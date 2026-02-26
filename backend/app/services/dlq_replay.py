"""
RabbitMQ DLQ replay service for operational recovery.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message

from app.core.config import settings
from app.schemas.events import DLQReplayResponse, EventEnvelope

DLX_ARGUMENT_KEY = "x-dead-letter-exchange"
TTL_ARGUMENT_KEY = "x-message-ttl"
X_DEATH_HEADER_KEY = "x-death"
DLQ_REASON_HEADER_KEY = "dlq_reason"
FAILED_AT_HEADER_KEY = "failed_at"


class DLQReplayError(RuntimeError):
    """Raised when a DLQ message cannot be replayed."""


class RabbitMQDLQReplayService:
    """
    Replays one message at a time from DLQ back to the primary event exchange.
    """

    def __init__(self) -> None:
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._channel: aio_pika.abc.AbstractRobustChannel | None = None
        self._exchange: aio_pika.abc.AbstractExchange | None = None
        self._dlq_queue: aio_pika.abc.AbstractQueue | None = None
        self._lock = asyncio.Lock()

    async def replay_next(self) -> DLQReplayResponse:
        await self._ensure_connected()
        if self._exchange is None or self._dlq_queue is None:
            raise DLQReplayError("RabbitMQ topology is not initialized")

        dlq_message = await self._dlq_queue.get(no_ack=False, fail=False)
        if dlq_message is None:
            return DLQReplayResponse(status="empty")

        try:
            envelope = EventEnvelope.model_validate_json(dlq_message.body)
            routing_key = self._resolve_replay_routing_key(dlq_message.headers, envelope)

            replay_message = Message(
                body=dlq_message.body,
                content_type=dlq_message.content_type or "application/json",
                content_encoding=dlq_message.content_encoding,
                delivery_mode=DeliveryMode.PERSISTENT,
                message_id=dlq_message.message_id or envelope.event_id,
                correlation_id=dlq_message.correlation_id or envelope.correlation_id,
                timestamp=datetime.now(timezone.utc),
                type=dlq_message.type,
                app_id=dlq_message.app_id,
                headers=self._clean_replay_headers(dlq_message.headers),
            )

            await self._exchange.publish(replay_message, routing_key=routing_key, mandatory=True)
            await dlq_message.ack()

            return DLQReplayResponse(
                status="replayed",
                message_id=replay_message.message_id,
                event_id=envelope.event_id,
                routing_key=routing_key,
                replayed_at=datetime.now(timezone.utc),
            )
        except Exception as exc:
            await dlq_message.reject(requeue=True)
            raise DLQReplayError(str(exc)) from exc

    async def _ensure_connected(self) -> None:
        if self._exchange is not None and self._dlq_queue is not None:
            return

        async with self._lock:
            if self._exchange is not None and self._dlq_queue is not None:
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

                await self._channel.declare_exchange(
                    settings.rabbitmq_retry_exchange,
                    ExchangeType.TOPIC,
                    durable=True,
                )
                await self._channel.declare_queue(
                    settings.rabbitmq_retry_queue,
                    durable=True,
                    arguments={
                        TTL_ARGUMENT_KEY: settings.rabbitmq_retry_delay_ms,
                        DLX_ARGUMENT_KEY: settings.rabbitmq_exchange,
                    },
                )
                self._dlq_queue = await self._channel.declare_queue(
                    settings.rabbitmq_dlq_queue,
                    durable=True,
                )
            except Exception as exc:
                await self.close()
                raise DLQReplayError(f"Failed to connect to RabbitMQ: {exc}") from exc

    def _resolve_replay_routing_key(
        self,
        headers: dict[str, Any] | None,
        envelope: EventEnvelope,
    ) -> str:
        if not headers:
            return envelope.event_type

        original_routing_key = headers.get("original_routing_key")
        if isinstance(original_routing_key, str) and original_routing_key:
            return original_routing_key
        return envelope.event_type

    def _clean_replay_headers(self, headers: dict[str, Any] | None) -> dict[str, Any]:
        sanitized = dict(headers or {})
        sanitized.pop(X_DEATH_HEADER_KEY, None)
        sanitized.pop(DLQ_REASON_HEADER_KEY, None)
        sanitized.pop(FAILED_AT_HEADER_KEY, None)
        return sanitized

    async def close(self) -> None:
        if self._channel is not None and not self._channel.is_closed:
            await self._channel.close()

        if self._connection is not None and not self._connection.is_closed:
            await self._connection.close()

        self._channel = None
        self._connection = None
        self._exchange = None
        self._dlq_queue = None


dlq_replay_service = RabbitMQDLQReplayService()


def get_dlq_replay_service() -> RabbitMQDLQReplayService:
    return dlq_replay_service
