"""
Tests for the assignment finalization endpoint.
"""

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.events import EventEnvelope
from app.services.assignments import HistoryCheckError, get_history_check_service
from app.services.messaging import EventPublishError, get_event_publisher


class FakePublisher:
    def __init__(self) -> None:
        self.published_events: list[EventEnvelope] = []
        self.routing_key = "assignment.history.finalized"

    async def publish(self, event: EventEnvelope) -> str:
        self.published_events.append(event)
        return self.routing_key


class FailingPublisher:
    async def publish(self, event: EventEnvelope) -> str:
        raise EventPublishError("rabbitmq unavailable")


class FakeHistoryCheckService:
    def __init__(self, is_finalized: bool = False, fail: bool = False) -> None:
        self._is_finalized = is_finalized
        self._fail = fail

    async def is_week_finalized(self, team_id: str, week_start: str) -> bool:
        if self._fail:
            raise HistoryCheckError("mongo unavailable")
        return self._is_finalized


def test_finalize_assignments_success() -> None:
    fake_publisher = FakePublisher()
    app.dependency_overrides[get_event_publisher] = lambda: fake_publisher
    app.dependency_overrides[get_history_check_service] = lambda: FakeHistoryCheckService(
        is_finalized=False
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/teams/team_123/assignments/finalize",
                json={
                    "week_start": "2026-02-23",
                    "assignments": [
                        {"role_code": "role_1", "user_id": "user_1", "source": "auto"}
                    ],
                    "finalized_by": "admin",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "accepted"
    assert body["team_id"] == "team_123"
    assert body["week_start"] == "2026-02-23"
    assert "event_id" in body
    assert len(fake_publisher.published_events) == 1
    
    event = fake_publisher.published_events[0]
    assert event.team_id == "team_123"
    assert event.event_type == "assignment.history.finalized"
    assert event.payload["week_start"] == "2026-02-23"


def test_finalize_assignments_conflict_when_already_finalized() -> None:
    fake_publisher = FakePublisher()
    app.dependency_overrides[get_event_publisher] = lambda: fake_publisher
    app.dependency_overrides[get_history_check_service] = lambda: FakeHistoryCheckService(
        is_finalized=True
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/teams/team_123/assignments/finalize",
                json={
                    "week_start": "2026-02-23",
                    "assignments": [
                        {"role_code": "role_1", "user_id": "user_1", "source": "auto"}
                    ],
                    "finalized_by": "admin",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    assert "already finalized" in response.json()["detail"]
    assert len(fake_publisher.published_events) == 0


def test_finalize_assignments_returns_503_when_history_check_fails() -> None:
    app.dependency_overrides[get_history_check_service] = lambda: FakeHistoryCheckService(
        fail=True
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/teams/team_123/assignments/finalize",
                json={
                    "week_start": "2026-02-23",
                    "assignments": [
                        {"role_code": "role_1", "user_id": "user_1", "source": "auto"}
                    ],
                    "finalized_by": "admin",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert "Unable to check assignment history" in response.json()["detail"]


def test_finalize_assignments_returns_503_when_publish_fails() -> None:
    app.dependency_overrides[get_event_publisher] = lambda: FailingPublisher()
    app.dependency_overrides[get_history_check_service] = lambda: FakeHistoryCheckService(
        is_finalized=False
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/teams/team_123/assignments/finalize",
                json={
                    "week_start": "2026-02-23",
                    "assignments": [
                        {"role_code": "role_1", "user_id": "user_1", "source": "auto"}
                    ],
                    "finalized_by": "admin",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert "Unable to publish finalization event" in response.json()["detail"]
