"""
RabbitMQ worker runtime for processing scheduling events.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, IncomingMessage, Message
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pydantic import ValidationError
from redis import asyncio as redis_asyncio

from app.core.config import settings
from app.schemas.events import AssignmentRecommendationsRequestedPayload, EventEnvelope

LOGGER = logging.getLogger("role_manager.worker")
DLX_ARGUMENT_KEY = "x-dead-letter-exchange"
TTL_ARGUMENT_KEY = "x-message-ttl"
X_DEATH_HEADER_KEY = "x-death"
X_DEATH_COUNT_KEY = "count"
X_DEATH_QUEUE_KEY = "queue"
DLQ_REASON_HEADER_KEY = "dlq_reason"
FAILED_AT_HEADER_KEY = "failed_at"
ORIGINAL_ROUTING_KEY_HEADER_KEY = "original_routing_key"
ASSIGNMENT_RECOMMENDATIONS_EVENT_TYPE = "assignment.recommendations.requested"


class EventWorker:
    """
    Consumes scheduling events and writes durable records to MongoDB.
    """

    def __init__(self) -> None:
        self._rabbit_connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._rabbit_channel: aio_pika.abc.AbstractRobustChannel | None = None
        self._exchange: aio_pika.abc.AbstractExchange | None = None
        self._retry_exchange: aio_pika.abc.AbstractExchange | None = None
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
        self._retry_exchange = await self._rabbit_channel.declare_exchange(
            settings.rabbitmq_retry_exchange,
            ExchangeType.TOPIC,
            durable=True,
        )

        await self._rabbit_channel.declare_queue(
            settings.rabbitmq_dlq_queue,
            durable=True,
        )
        dlq = await self._rabbit_channel.get_queue(settings.rabbitmq_dlq_queue)
        await dlq.bind(self._exchange, routing_key=settings.rabbitmq_dlq_routing_key)

        retry_queue = await self._rabbit_channel.declare_queue(
            settings.rabbitmq_retry_queue,
            durable=True,
            arguments={
                TTL_ARGUMENT_KEY: settings.rabbitmq_retry_delay_ms,
                DLX_ARGUMENT_KEY: settings.rabbitmq_exchange,
            },
        )
        await retry_queue.bind(self._retry_exchange, routing_key=settings.rabbitmq_retry_binding_key)

        self._compute_queue = await self._rabbit_channel.declare_queue(
            settings.rabbitmq_compute_queue,
            durable=True,
            arguments={
                DLX_ARGUMENT_KEY: settings.rabbitmq_retry_exchange,
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
        await self._mongo_db.assignment_recommendations.create_index(
            [("team_id", 1), ("week_start", 1), ("role_code", 1)],
            unique=True,
            name="assignment_recommendations_team_week_role_unique",
        )

    async def _consume_loop(self) -> None:
        if self._compute_queue is None:
            raise RuntimeError("RabbitMQ compute queue is not initialized")

        await self._compute_queue.consume(self._process_message, no_ack=False)
        LOGGER.info("Worker is consuming queue '%s'", settings.rabbitmq_compute_queue)
        await self._stop_event.wait()

    async def _process_message(self, message: IncomingMessage) -> None:
        retry_count = self._get_retry_count(message)
        if retry_count >= settings.worker_max_retry_attempts:
            await self._move_to_dlq_or_retry(
                message,
                (
                    f"retry_limit_exceeded: "
                    f"retry_count={retry_count} max={settings.worker_max_retry_attempts}"
                ),
            )
            LOGGER.warning(
                "Moved message_id=%s to DLQ after retry limit",
                message.message_id,
            )
            return

        try:
            event = self._decode_message(message)
        except ValueError as exc:
            await self._move_to_dlq_or_retry(message, str(exc))
            LOGGER.warning(
                "Moved invalid message_id=%s to DLQ: %s",
                message.message_id,
                exc,
            )
            return

        try:
            if await self._already_processed(event.event_id):
                LOGGER.info("Skipping duplicate event_id=%s", event.event_id)
                await message.ack()
                return

            processed_at = datetime.now(timezone.utc)
            await self._persist_event_log(event, message, processed_at)
            await self._apply_projection(event, processed_at)
            await self._mark_processed(event.event_id)
            await message.ack()
            LOGGER.info(
                "Processed event_id=%s event_type=%s team_id=%s",
                event.event_id,
                event.event_type,
                event.team_id,
            )
        except Exception:
            LOGGER.exception(
                "Processing failed for message_id=%s event_id=%s, routing to retry",
                message.message_id,
                event.event_id,
            )
            await message.reject(requeue=False)

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

        if event.event_type == "availability.updated":
            await self._apply_availability_projection(event, processed_at)
            return

        if event.event_type == ASSIGNMENT_RECOMMENDATIONS_EVENT_TYPE:
            await self._apply_assignment_recommendations(event, processed_at)
            return

    async def _apply_availability_projection(
        self,
        event: EventEnvelope,
        processed_at: datetime,
    ) -> None:
        if self._mongo_db is None:
            raise RuntimeError("MongoDB is not initialized")

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

    async def _apply_assignment_recommendations(
        self,
        event: EventEnvelope,
        processed_at: datetime,
    ) -> None:
        if self._mongo_db is None:
            raise RuntimeError("MongoDB is not initialized")

        payload = AssignmentRecommendationsRequestedPayload.model_validate(event.payload)
        recommendations = self._build_assignment_recommendations(
            event.team_id,
            payload,
            event.event_id,
            processed_at,
        )

        for recommendation in recommendations:
            await self._mongo_db.assignment_recommendations.update_one(
                {
                    "team_id": recommendation["team_id"],
                    "week_start": recommendation["week_start"],
                    "role_code": recommendation["role_code"],
                },
                {"$set": recommendation},
                upsert=True,
            )

    def _build_assignment_recommendations(
        self,
        team_id: str,
        payload: AssignmentRecommendationsRequestedPayload,
        event_id: str,
        generated_at: datetime,
    ) -> list[dict[str, Any]]:
        recommendations: list[dict[str, Any]] = []

        for role in payload.roles:
            scored_candidates = [
                {
                    "user_id": candidate.user_id,
                    "score": (candidate.last_done * candidate.motivation_factor)
                    + candidate.experience_factor,
                    "score_breakdown": {
                        "last_done": candidate.last_done,
                        "motivation_factor": candidate.motivation_factor,
                        "experience_factor": candidate.experience_factor,
                    },
                }
                for candidate in role.candidates
            ]
            scored_candidates.sort(
                key=lambda candidate: (
                    -candidate["score"],
                    -candidate["score_breakdown"]["last_done"],
                    -candidate["score_breakdown"]["motivation_factor"],
                    -candidate["score_breakdown"]["experience_factor"],
                    candidate["user_id"],
                )
            )

            selected_candidate = scored_candidates[0]
            recommendations.append(
                {
                    "team_id": team_id,
                    "week_start": payload.week_start.isoformat(),
                    "role_code": role.role_code,
                    "recommended_user_id": selected_candidate["user_id"],
                    "score": selected_candidate["score"],
                    "score_breakdown": selected_candidate["score_breakdown"],
                    "event_ids": [event_id],
                    "generated_at": generated_at,
                    "explanation": (
                        "Highest fair score among submitted candidates. "
                        "Ties resolve deterministically by score inputs and user_id."
                    ),
                }
            )

        return recommendations

    def _get_retry_count(self, message: IncomingMessage) -> int:
        headers = message.headers or {}
        x_death = headers.get(X_DEATH_HEADER_KEY)
        if not isinstance(x_death, list):
            return 0

        for death_entry in x_death:
            if not isinstance(death_entry, Mapping):
                continue
            if death_entry.get(X_DEATH_QUEUE_KEY) != settings.rabbitmq_compute_queue:
                continue

            count = death_entry.get(X_DEATH_COUNT_KEY, 0)
            try:
                return int(count)
            except (TypeError, ValueError):
                return 0

        return 0

    async def _move_to_dlq_or_retry(self, message: IncomingMessage, reason: str) -> None:
        try:
            await self._publish_to_dlq(message, reason)
            await message.ack()
        except Exception:
            LOGGER.exception(
                "Failed to move message_id=%s to DLQ, routing to retry",
                message.message_id,
            )
            await message.reject(requeue=False)

    async def _publish_to_dlq(self, message: IncomingMessage, reason: str) -> None:
        if self._exchange is None:
            raise RuntimeError("RabbitMQ exchange is not initialized")

        headers = dict(message.headers or {})
        headers[DLQ_REASON_HEADER_KEY] = reason
        headers[FAILED_AT_HEADER_KEY] = datetime.now(timezone.utc).isoformat()
        headers[ORIGINAL_ROUTING_KEY_HEADER_KEY] = message.routing_key

        dlq_message = Message(
            body=message.body,
            content_type=message.content_type or "application/json",
            content_encoding=message.content_encoding,
            delivery_mode=DeliveryMode.PERSISTENT,
            message_id=message.message_id,
            correlation_id=message.correlation_id,
            timestamp=datetime.now(timezone.utc),
            type=message.type,
            app_id=message.app_id,
            headers=headers,
        )
        await self._exchange.publish(dlq_message, routing_key=settings.rabbitmq_dlq_routing_key)

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
