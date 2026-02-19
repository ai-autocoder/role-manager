"""
RabbitMQ publishing and topology management for scheduling events.
"""

from __future__ import annotations

import asyncio
from typing import Final

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message

from app.core.config import settings
from app.schemas.events import EventEnvelope

DLQ_ARGUMENT_KEY: Final[str] = "x-dead-letter-routing-key"
DLX_ARGUMENT_KEY: Final[str] = "x-dead-letter-exchange"


class EventPublishError(RuntimeError):
    """Raised when a scheduling event cannot be published to RabbitMQ."""


class RabbitMQPublisher:
    """
    Publishes events to RabbitMQ and ensures queue topology exists.
    """

    def __init__(self) -> None:
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._channel: aio_pika.abc.AbstractRobustChannel | None = None
        self._exchange: aio_pika.abc.AbstractExchange | None = None
        self._lock = asyncio.Lock()

    async def publish(self, event: EventEnvelope) -> str:
        """
        Publish a canonical event envelope as a durable RabbitMQ message.
        Returns the routing key used for publishing.
        """
        await self._ensure_connected()

        if self._exchange is None:
            raise EventPublishError("RabbitMQ exchange is not initialized")

        routing_key = event.event_type
        message = Message(
            body=event.model_dump_json().encode("utf-8"),
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
            message_id=event.event_id,
            correlation_id=event.correlation_id,
            timestamp=event.occurred_at,
            headers={
                "schema_version": event.schema_version,
                "event_type": event.event_type,
                "team_id": event.team_id,
                "producer": event.producer,
            },
        )

        try:
            await self._exchange.publish(message, routing_key=routing_key, mandatory=True)
            return routing_key
        except Exception as exc:  # pragma: no cover - exercised in integration
            await self.close()
            raise EventPublishError(str(exc)) from exc

    async def _ensure_connected(self) -> None:
        if self._exchange is not None:
            return

        async with self._lock:
            if self._exchange is not None:
                return

            try:
                self._connection = await aio_pika.connect_robust(
                    settings.rabbitmq_url,
                    timeout=settings.rabbitmq_connect_timeout_seconds,
                )
                self._channel = await self._connection.channel()
                self._exchange = await self._channel.declare_exchange(
                    settings.rabbitmq_exchange,
                    ExchangeType.TOPIC,
                    durable=True,
                )
                await self._declare_topology()
            except Exception as exc:  # pragma: no cover - exercised in integration
                await self.close()
                raise EventPublishError(f"Failed to connect to RabbitMQ: {exc}") from exc

    async def _declare_topology(self) -> None:
        if self._channel is None or self._exchange is None:
            raise EventPublishError("RabbitMQ channel is not initialized")

        await self._channel.declare_queue(
            settings.rabbitmq_dlq_queue,
            durable=True,
        )
        dlq = await self._channel.get_queue(settings.rabbitmq_dlq_queue)
        await dlq.bind(self._exchange, routing_key=settings.rabbitmq_dlq_routing_key)

        queue = await self._channel.declare_queue(
            settings.rabbitmq_compute_queue,
            durable=True,
            arguments={
                DLX_ARGUMENT_KEY: settings.rabbitmq_exchange,
                DLQ_ARGUMENT_KEY: settings.rabbitmq_dlq_routing_key,
            },
        )
        await queue.bind(self._exchange, routing_key=settings.rabbitmq_compute_binding_key)

    async def close(self) -> None:
        if self._channel is not None and not self._channel.is_closed:
            await self._channel.close()

        if self._connection is not None and not self._connection.is_closed:
            await self._connection.close()

        self._channel = None
        self._connection = None
        self._exchange = None


publisher = RabbitMQPublisher()


def get_event_publisher() -> RabbitMQPublisher:
    return publisher
