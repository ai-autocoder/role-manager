from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.events import DLQReplayResponse, EventEnvelope
from app.services.dlq_replay import DLQReplayError, get_dlq_replay_service
from app.services.messaging import EventPublishError, get_event_publisher
from app.services.replay_audit import ReplayAuditError, get_replay_audit_service


class FakePublisher:
    def __init__(self) -> None:
        self.published_events: list[EventEnvelope] = []
        self.routing_key = "availability.updated"

    async def publish(self, event: EventEnvelope) -> str:
        self.published_events.append(event)
        return self.routing_key


class FailingPublisher:
    async def publish(self, event: EventEnvelope) -> str:
        raise EventPublishError("rabbitmq unavailable")


class FakeDLQReplayService:
    def __init__(self, response: DLQReplayResponse) -> None:
        self._response = response

    async def replay_next(self) -> DLQReplayResponse:
        return self._response


class FailingDLQReplayService:
    async def replay_next(self) -> DLQReplayResponse:
        raise DLQReplayError("rabbitmq unavailable")


class FakeReplayAuditService:
    def __init__(self) -> None:
        self.records: list[dict[str, str | None]] = []

    async def record_attempt(
        self,
        *,
        outcome: str,
        message_id: str | None = None,
        event_id: str | None = None,
        routing_key: str | None = None,
        error: str | None = None,
    ) -> None:
        self.records.append(
            {
                "outcome": outcome,
                "message_id": message_id,
                "event_id": event_id,
                "routing_key": routing_key,
                "error": error,
            }
        )


class FailingReplayAuditService:
    async def record_attempt(
        self,
        *,
        outcome: str,
        message_id: str | None = None,
        event_id: str | None = None,
        routing_key: str | None = None,
        error: str | None = None,
    ) -> None:
        raise ReplayAuditError("mongo unavailable")


def test_post_events_returns_accepted_and_publishes_event() -> None:
    fake_publisher = FakePublisher()
    app.dependency_overrides[get_event_publisher] = lambda: fake_publisher

    try:
        with TestClient(app) as client:
            response = client.post(
                "/events",
                json={
                    "event_type": "availability.updated",
                    "team_id": "team_123",
                    "payload": {
                        "user_id": "user_456",
                        "week_start": "2026-02-23",
                        "availability": [{"day": "mon", "status": "unavailable"}],
                    },
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "accepted"
    assert body["routing_key"] == "availability.updated"
    assert body["event_id"]
    assert body["correlation_id"]
    assert len(fake_publisher.published_events) == 1
    assert fake_publisher.published_events[0].team_id == "team_123"


def test_post_events_returns_503_when_publisher_fails() -> None:
    app.dependency_overrides[get_event_publisher] = lambda: FailingPublisher()

    try:
        with TestClient(app) as client:
            response = client.post(
                "/events",
                json={
                    "event_type": "availability.updated",
                    "team_id": "team_123",
                    "payload": {},
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert "Unable to publish event" in response.json()["detail"]


def test_post_events_dlq_replay_returns_replayed_result() -> None:
    fake_audit_service = FakeReplayAuditService()
    app.dependency_overrides[get_dlq_replay_service] = lambda: FakeDLQReplayService(
        DLQReplayResponse(
            status="replayed",
            message_id="msg-1",
            event_id="evt-1",
            routing_key="availability.updated",
            replayed_at=datetime.now(timezone.utc),
        )
    )
    app.dependency_overrides[get_replay_audit_service] = lambda: fake_audit_service

    try:
        with TestClient(app) as client:
            response = client.post("/events/dlq/replay")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "replayed"
    assert body["message_id"] == "msg-1"
    assert body["event_id"] == "evt-1"
    assert body["routing_key"] == "availability.updated"
    assert body["replayed_at"] is not None
    assert fake_audit_service.records == [
        {
            "outcome": "replayed",
            "message_id": "msg-1",
            "event_id": "evt-1",
            "routing_key": "availability.updated",
            "error": None,
        }
    ]


def test_post_events_dlq_replay_returns_empty_result() -> None:
    fake_audit_service = FakeReplayAuditService()
    app.dependency_overrides[get_dlq_replay_service] = lambda: FakeDLQReplayService(
        DLQReplayResponse(status="empty")
    )
    app.dependency_overrides[get_replay_audit_service] = lambda: fake_audit_service

    try:
        with TestClient(app) as client:
            response = client.post("/events/dlq/replay")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "empty"
    assert body["message_id"] is None
    assert fake_audit_service.records == [
        {
            "outcome": "empty",
            "message_id": None,
            "event_id": None,
            "routing_key": None,
            "error": None,
        }
    ]


def test_post_events_dlq_replay_returns_503_when_replay_fails() -> None:
    fake_audit_service = FakeReplayAuditService()
    app.dependency_overrides[get_dlq_replay_service] = lambda: FailingDLQReplayService()
    app.dependency_overrides[get_replay_audit_service] = lambda: fake_audit_service

    try:
        with TestClient(app) as client:
            response = client.post("/events/dlq/replay")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert "Unable to replay DLQ message" in response.json()["detail"]
    assert fake_audit_service.records == [
        {
            "outcome": "failed",
            "message_id": None,
            "event_id": None,
            "routing_key": None,
            "error": "rabbitmq unavailable",
        }
    ]


def test_post_events_dlq_replay_succeeds_when_audit_write_fails() -> None:
    app.dependency_overrides[get_dlq_replay_service] = lambda: FakeDLQReplayService(
        DLQReplayResponse(
            status="replayed",
            message_id="msg-1",
            event_id="evt-1",
            routing_key="availability.updated",
            replayed_at=datetime.now(timezone.utc),
        )
    )
    app.dependency_overrides[get_replay_audit_service] = lambda: FailingReplayAuditService()

    try:
        with TestClient(app) as client:
            response = client.post("/events/dlq/replay")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "replayed"
