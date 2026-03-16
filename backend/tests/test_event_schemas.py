from pydantic import ValidationError

from app.schemas.events import (
    AssignmentHistoryFinalizedPayload,
    AssignmentRecommendationsRequestedPayload,
    EventIngestionRequest,
    build_event_envelope,
)


def test_build_event_envelope_enriches_missing_metadata() -> None:
    request = EventIngestionRequest(
        event_type="availability.updated",
        team_id="team_123",
        payload={"user_id": "user_1", "week_start": "2026-02-23", "availability": []},
    )

    envelope = build_event_envelope(request)

    assert envelope.schema_version == 1
    assert envelope.event_id
    assert envelope.correlation_id
    assert envelope.producer == "api"
    assert envelope.occurred_at.tzinfo is not None


def test_schema_version_validation_rejects_unsupported_versions() -> None:
    try:
        EventIngestionRequest(
            schema_version=99,
            event_type="availability.updated",
            team_id="team_123",
            payload={},
        )
    except ValidationError as exc:
        assert "Unsupported schema_version" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected ValidationError for unsupported schema_version")


def test_assignment_recommendations_payload_rejects_duplicate_role_codes() -> None:
    try:
        AssignmentRecommendationsRequestedPayload.model_validate(
            {
                "week_start": "2026-02-23",
                "roles": [
                    {
                        "role_code": "role_1",
                        "candidates": [{"user_id": "user_1", "last_done": 2}],
                    },
                    {
                        "role_code": "role_1",
                        "candidates": [{"user_id": "user_2", "last_done": 4}],
                    },
                ],
            }
        )
    except ValidationError as exc:
        assert "unique role_code" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected ValidationError for duplicate role_code values")


def test_assignment_history_finalized_payload_rejects_duplicate_role_codes() -> None:
    try:
        AssignmentHistoryFinalizedPayload.model_validate(
            {
                "week_start": "2026-02-23",
                "assignments": [
                    {"role_code": "role_1", "user_id": "user_1", "source": "auto"},
                    {"role_code": "role_1", "user_id": "user_2", "source": "manual_override"},
                ],
                "finalized_by": "admin",
            }
        )
    except ValidationError as exc:
        assert "unique role_code" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected ValidationError for duplicate role_code values")
