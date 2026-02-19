from fastapi.testclient import TestClient

from app.main import app
from app.schemas.events import EventEnvelope
from app.services.messaging import EventPublishError, get_event_publisher


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
