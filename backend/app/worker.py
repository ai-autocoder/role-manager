"""
RabbitMQ worker runtime for processing scheduling events.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

import aio_pika
from aio_pika import ExchangeType, IncomingMessage
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pydantic import ValidationError
from redis import asyncio as redis_asyncio

from app.core.config import settings
from app.schemas.events import EventEnvelope

LOGGER = logging.getLogger("role_manager.worker")
DLQ_ARGUMENT_KEY = "x-dead-letter-routing-key"
DLX_ARGUMENT_KEY = "x-dead-letter-exchange"


class EventWorker:
    """
    Consumes scheduling events and writes durable records to MongoDB.
    """

    def __init__(self) -> None:
        self._rabbit_connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._rabbit_channel: aio_pika.abc.AbstractRobustChannel | None = None
        self._exchange: aio_pika.abc.AbstractExchange | None = None
        self._compute_queue: aio_pika.abc.AbstractQueue | None = None
        self._redis: redis_asyncio.Redis | None = None
        self._mongo_client: AsyncIOMotorClient | None = None
        self._mongo_db: AsyncIOMotorDatabase | None = None
        self._stop_event = asyncio.Event()

    async def run(self) -> None:
        await self._connect_dependencies()
        await self._consume_loop()

    async def _connect_dependencies(self) -> None:
        self._redis = redis_asyncio.from_url(settings.redis_url, decode_responses=True)
        self._mongo_client = AsyncIOMotorClient(settings.mongo_url)
        self._mongo_db = self._mongo_client[settings.mongo_database]
        await self._ensure_indexes()

        self._rabbit_connection = await aio_pika.connect_robust(
            settings.rabbitmq_url,
            timeout=settings.rabbitmq_connect_timeout_seconds,
        )
        self._rabbit_channel = await self._rabbit_connection.channel()
        await self._rabbit_channel.set_qos(prefetch_count=settings.worker_prefetch_count)
        self._exchange = await self._rabbit_channel.declare_exchange(
            settings.rabbitmq_exchange,
            ExchangeType.TOPIC,
            durable=True,
        )

        await self._rabbit_channel.declare_queue(
            settings.rabbitmq_dlq_queue,
            durable=True,
        )
        dlq = await self._rabbit_channel.get_queue(settings.rabbitmq_dlq_queue)
        await dlq.bind(self._exchange, routing_key=settings.rabbitmq_dlq_routing_key)

        self._compute_queue = await self._rabbit_channel.declare_queue(
            settings.rabbitmq_compute_queue,
            durable=True,
            arguments={
                DLX_ARGUMENT_KEY: settings.rabbitmq_exchange,
                DLQ_ARGUMENT_KEY: settings.rabbitmq_dlq_routing_key,
            },
        )
        await self._compute_queue.bind(
            self._exchange,
            routing_key=settings.rabbitmq_compute_binding_key,
        )

    async def _ensure_indexes(self) -> None:
        if self._mongo_db is None:
            raise RuntimeError("MongoDB is not initialized")

        await self._mongo_db.event_log.create_index("event_id", unique=True, name="event_id_unique")
        await self._mongo_db.availability.create_index(
            [("team_id", 1), ("user_id", 1), ("week_start", 1)],
            unique=True,
            name="availability_team_user_week_unique",
        )

    async def _consume_loop(self) -> None:
        if self._compute_queue is None:
            raise RuntimeError("RabbitMQ compute queue is not initialized")

        await self._compute_queue.consume(self._process_message, no_ack=False)
        LOGGER.info("Worker is consuming queue '%s'", settings.rabbitmq_compute_queue)
        await self._stop_event.wait()

    async def _process_message(self, message: IncomingMessage) -> None:
        async with message.process(requeue=False):
            event = self._decode_message(message)

            if await self._already_processed(event.event_id):
                LOGGER.info("Skipping duplicate event_id=%s", event.event_id)
                return

            processed_at = datetime.now(timezone.utc)
            await self._persist_event_log(event, message, processed_at)
            await self._apply_projection(event, processed_at)
            await self._mark_processed(event.event_id)
            LOGGER.info(
                "Processed event_id=%s event_type=%s team_id=%s",
                event.event_id,
                event.event_type,
                event.team_id,
            )

    def _decode_message(self, message: IncomingMessage) -> EventEnvelope:
        try:
            payload: dict[str, Any] = json.loads(message.body.decode("utf-8"))
            return EventEnvelope.model_validate(payload)
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON message body") from exc
        except ValidationError as exc:
            raise ValueError(f"Invalid event envelope: {exc}") from exc

    async def _already_processed(self, event_id: str) -> bool:
        if self._redis is None:
            raise RuntimeError("Redis is not initialized")
        key = f"event:processed:{event_id}"
        return bool(await self._redis.exists(key))

    async def _mark_processed(self, event_id: str) -> None:
        if self._redis is None:
            raise RuntimeError("Redis is not initialized")
        key = f"event:processed:{event_id}"
        await self._redis.set(key, "1", ex=settings.processed_event_ttl_seconds)

    async def _persist_event_log(
        self,
        event: EventEnvelope,
        message: IncomingMessage,
        processed_at: datetime,
    ) -> None:
        if self._mongo_db is None:
            raise RuntimeError("MongoDB is not initialized")

        event_document = event.model_dump(mode="json")
        event_document["processed_at"] = processed_at
        event_document["routing_key"] = message.routing_key
        event_document["delivery_tag"] = message.delivery_tag

        await self._mongo_db.event_log.update_one(
            {"event_id": event.event_id},
            {"$setOnInsert": event_document},
            upsert=True,
        )

    async def _apply_projection(self, event: EventEnvelope, processed_at: datetime) -> None:
        """
        Build early read-model projections for known event types.
        """
        if self._mongo_db is None:
            raise RuntimeError("MongoDB is not initialized")

        if event.event_type != "availability.updated":
            return

        user_id = event.payload.get("user_id")
        week_start = event.payload.get("week_start")
        availability = event.payload.get("availability")

        if not user_id or not week_start or not isinstance(availability, list):
            LOGGER.warning(
                "Skipping availability projection for event_id=%s due to incomplete payload",
                event.event_id,
            )
            return

        projection = {
            "team_id": event.team_id,
            "user_id": user_id,
            "week_start": week_start,
            "availability": availability,
            "reason": event.payload.get("reason"),
            "source_event_id": event.event_id,
            "updated_at": processed_at,
        }

        await self._mongo_db.availability.update_one(
            {
                "team_id": event.team_id,
                "user_id": user_id,
                "week_start": week_start,
            },
            {"$set": projection},
            upsert=True,
        )

    async def shutdown(self) -> None:
        self._stop_event.set()

        if self._redis is not None:
            await self._redis.close()

        if self._rabbit_channel is not None and not self._rabbit_channel.is_closed:
            await self._rabbit_channel.close()

        if self._rabbit_connection is not None and not self._rabbit_connection.is_closed:
            await self._rabbit_connection.close()

        if self._mongo_client is not None:
            self._mongo_client.close()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    worker = EventWorker()
    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        LOGGER.info("Worker shutdown requested")
    finally:
        try:
            asyncio.run(worker.shutdown())
        except RuntimeError:
            # Event loop already closed.
            pass


if __name__ == "__main__":
    main()
