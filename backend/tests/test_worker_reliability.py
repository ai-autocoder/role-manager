from datetime import datetime, timezone

import pytest

from app.core.config import settings
from app.schemas.events import AssignmentRecommendationsRequestedPayload, EventEnvelope
from app.worker import EventWorker


class FakeMessage:
    def __init__(self, headers: dict | None = None, message_id: str = "msg-1") -> None:
        self.headers = headers or {}
        self.message_id = message_id


class FakeCollection:
    def __init__(self) -> None:
        self.create_index_calls: list[dict[str, object]] = []
        self.update_calls: list[dict[str, object]] = []

    async def create_index(self, keys: object, **kwargs: object) -> None:
        self.create_index_calls.append({"keys": keys, "kwargs": kwargs})

    async def update_one(self, filter_doc: dict, update_doc: dict, upsert: bool = False) -> None:
        self.update_calls.append(
            {
                "filter": filter_doc,
                "update": update_doc,
                "upsert": upsert,
            }
        )


class FakeMongoDatabase:
    def __init__(self) -> None:
        self.event_log = FakeCollection()
        self.availability = FakeCollection()
        self.assignment_recommendations = FakeCollection()


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


def test_build_assignment_recommendations_prefers_highest_score_and_is_deterministic() -> None:
    worker = EventWorker()
    payload = AssignmentRecommendationsRequestedPayload.model_validate(
        {
            "week_start": "2026-02-23",
            "roles": [
                {
                    "role_code": "role_1",
                    "candidates": [
                        {
                            "user_id": "user-b",
                            "last_done": 3,
                            "motivation_factor": 1.5,
                            "experience_factor": 1.0,
                        },
                        {
                            "user_id": "user-a",
                            "last_done": 5,
                            "motivation_factor": 1.0,
                            "experience_factor": 1.0,
                        },
                    ],
                },
                {
                    "role_code": "role_2",
                    "candidates": [
                        {
                            "user_id": "user-z",
                            "last_done": 4,
                            "motivation_factor": 1.0,
                            "experience_factor": 1.0,
                        },
                        {
                            "user_id": "user-a",
                            "last_done": 4,
                            "motivation_factor": 1.0,
                            "experience_factor": 1.0,
                        },
                    ],
                },
            ],
        }
    )
    processed_at = datetime(2026, 2, 18, 10, 46, 22, tzinfo=timezone.utc)

    recommendations = worker._build_assignment_recommendations(
        "team_123",
        payload,
        "evt-123",
        processed_at,
    )

    assert recommendations == [
        {
            "team_id": "team_123",
            "week_start": "2026-02-23",
            "role_code": "role_1",
            "recommended_user_id": "user-a",
            "score": 6.0,
            "score_breakdown": {
                "last_done": 5,
                "motivation_factor": 1.0,
                "experience_factor": 1.0,
            },
            "event_ids": ["evt-123"],
            "generated_at": processed_at,
            "explanation": (
                "Highest fair score among submitted candidates. "
                "Ties resolve deterministically by score inputs and user_id."
            ),
        },
        {
            "team_id": "team_123",
            "week_start": "2026-02-23",
            "role_code": "role_2",
            "recommended_user_id": "user-a",
            "score": 5.0,
            "score_breakdown": {
                "last_done": 4,
                "motivation_factor": 1.0,
                "experience_factor": 1.0,
            },
            "event_ids": ["evt-123"],
            "generated_at": processed_at,
            "explanation": (
                "Highest fair score among submitted candidates. "
                "Ties resolve deterministically by score inputs and user_id."
            ),
        },
    ]


@pytest.mark.asyncio
async def test_apply_projection_persists_assignment_recommendations() -> None:
    worker = EventWorker()
    fake_db = FakeMongoDatabase()
    worker._mongo_db = fake_db  # type: ignore[assignment]
    processed_at = datetime(2026, 2, 18, 10, 46, 22, tzinfo=timezone.utc)
    event = EventEnvelope(
        schema_version=1,
        event_id="evt-123",
        event_type="assignment.recommendations.requested",
        occurred_at=processed_at,
        producer="api",
        correlation_id="corr-123",
        team_id="team_123",
        payload={
            "week_start": "2026-02-23",
            "roles": [
                {
                    "role_code": "role_1",
                    "candidates": [
                        {
                            "user_id": "user-a",
                            "last_done": 5,
                            "motivation_factor": 1.0,
                            "experience_factor": 1.0,
                        },
                        {
                            "user_id": "user-b",
                            "last_done": 1,
                            "motivation_factor": 1.0,
                            "experience_factor": 1.0,
                        },
                    ],
                }
            ],
        },
    )

    await worker._apply_projection(event, processed_at)

    assert fake_db.assignment_recommendations.update_calls == [
        {
            "filter": {
                "team_id": "team_123",
                "week_start": "2026-02-23",
                "role_code": "role_1",
            },
            "update": {
                "$set": {
                    "team_id": "team_123",
                    "week_start": "2026-02-23",
                    "role_code": "role_1",
                    "recommended_user_id": "user-a",
                    "score": 6.0,
                    "score_breakdown": {
                        "last_done": 5,
                        "motivation_factor": 1.0,
                        "experience_factor": 1.0,
                    },
                    "event_ids": ["evt-123"],
                    "generated_at": processed_at,
                    "explanation": (
                        "Highest fair score among submitted candidates. "
                        "Ties resolve deterministically by score inputs and user_id."
                    ),
                }
            },
            "upsert": True,
        }
    ]
