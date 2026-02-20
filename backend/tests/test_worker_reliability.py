import pytest

from app.core.config import settings
from app.worker import EventWorker


class FakeMessage:
    def __init__(self, headers: dict | None = None, message_id: str = "msg-1") -> None:
        self.headers = headers or {}
        self.message_id = message_id


def test_get_retry_count_reads_compute_queue_x_death_count() -> None:
    worker = EventWorker()
    message = FakeMessage(
        headers={
            "x-death": [
                {"queue": settings.rabbitmq_compute_queue, "count": 2},
            ]
        }
    )

    assert worker._get_retry_count(message) == 2


def test_get_retry_count_ignores_other_queues() -> None:
    worker = EventWorker()
    message = FakeMessage(
        headers={
            "x-death": [
                {"queue": "other.queue", "count": 5},
            ]
        }
    )

    assert worker._get_retry_count(message) == 0


@pytest.mark.asyncio
async def test_process_message_moves_to_dlq_when_retry_limit_reached(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = EventWorker()
    message = FakeMessage(
        headers={
            "x-death": [
                {
                    "queue": settings.rabbitmq_compute_queue,
                    "count": settings.worker_max_retry_attempts,
                }
            ]
        }
    )
    captured: dict[str, str] = {}

    async def fake_move_to_dlq_or_retry(message_arg: FakeMessage, reason: str) -> None:
        captured["message_id"] = message_arg.message_id
        captured["reason"] = reason

    monkeypatch.setattr(worker, "_move_to_dlq_or_retry", fake_move_to_dlq_or_retry)

    def fail_decode(_: FakeMessage) -> None:
        raise AssertionError("_decode_message should not be called for retry-exhausted messages")

    monkeypatch.setattr(worker, "_decode_message", fail_decode)

    await worker._process_message(message)  # type: ignore[arg-type]

    assert captured["message_id"] == "msg-1"
    assert "retry_limit_exceeded" in captured["reason"]


@pytest.mark.asyncio
async def test_process_message_moves_invalid_payload_to_dlq(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = EventWorker()
    message = FakeMessage(headers={})
    captured: dict[str, str] = {}

    def fail_decode(_: FakeMessage) -> None:
        raise ValueError("Invalid JSON message body")

    async def fake_move_to_dlq_or_retry(message_arg: FakeMessage, reason: str) -> None:
        captured["message_id"] = message_arg.message_id
        captured["reason"] = reason

    monkeypatch.setattr(worker, "_decode_message", fail_decode)
    monkeypatch.setattr(worker, "_move_to_dlq_or_retry", fake_move_to_dlq_or_retry)

    await worker._process_message(message)  # type: ignore[arg-type]

    assert captured["message_id"] == "msg-1"
    assert captured["reason"] == "Invalid JSON message body"
