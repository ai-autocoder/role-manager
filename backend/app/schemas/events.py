"""
Event contracts for ingestion and worker processing.
"""

from datetime import date, datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

SUPPORTED_SCHEMA_VERSIONS = {1}


class EventIngestionRequest(BaseModel):
    """
    Request payload for POST /events.
    Metadata fields are optional at ingress and are auto-filled when missing.
    """

    schema_version: int = Field(default=1)
    event_id: str | None = Field(default=None, min_length=1, max_length=128)
    event_type: str = Field(min_length=3, max_length=128)
    occurred_at: datetime | None = None
    producer: str | None = Field(default=None, min_length=1, max_length=64)
    correlation_id: str | None = Field(default=None, min_length=1, max_length=128)
    team_id: str = Field(min_length=1, max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: int) -> int:
        if value not in SUPPORTED_SCHEMA_VERSIONS:
            supported = ", ".join(str(v) for v in sorted(SUPPORTED_SCHEMA_VERSIONS))
            raise ValueError(f"Unsupported schema_version '{value}'. Supported: {supported}")
        return value

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str) -> str:
        # Keep contract strict enough for routing without over-constraining names.
        if "." not in value:
            raise ValueError("event_type must use dot notation, e.g. 'availability.updated'")
        return value


class EventEnvelope(BaseModel):
    """
    Canonical event envelope sent to RabbitMQ and consumed by workers.
    """

    schema_version: int = Field(default=1)
    event_id: str = Field(min_length=1, max_length=128)
    event_type: str = Field(min_length=3, max_length=128)
    occurred_at: datetime
    producer: str = Field(min_length=1, max_length=64)
    correlation_id: str = Field(min_length=1, max_length=128)
    team_id: str = Field(min_length=1, max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: int) -> int:
        if value not in SUPPORTED_SCHEMA_VERSIONS:
            supported = ", ".join(str(v) for v in sorted(SUPPORTED_SCHEMA_VERSIONS))
            raise ValueError(f"Unsupported schema_version '{value}'. Supported: {supported}")
        return value

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str) -> str:
        if "." not in value:
            raise ValueError("event_type must use dot notation, e.g. 'availability.updated'")
        return value

    @field_validator("occurred_at")
    @classmethod
    def normalize_to_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class RecommendationCandidateInput(BaseModel):
    """
    Candidate score inputs for a single role recommendation.
    """

    user_id: str = Field(min_length=1, max_length=128)
    last_done: int = Field(ge=0)
    motivation_factor: float = Field(default=1.0, gt=0)
    experience_factor: float = Field(default=1.0)
    is_volunteer: bool = Field(default=False)


class RecommendationRoleInput(BaseModel):
    """
    Input candidates for one role in a recommendation request.
    """

    role_code: str = Field(min_length=1, max_length=128)
    candidates: list[RecommendationCandidateInput] = Field(min_length=1)

    @field_validator("candidates")
    @classmethod
    def validate_unique_candidate_users(
        cls,
        value: list[RecommendationCandidateInput],
    ) -> list[RecommendationCandidateInput]:
        user_ids = [candidate.user_id for candidate in value]
        if len(user_ids) != len(set(user_ids)):
            raise ValueError("Each role must contain unique candidate user_id values")
        return value


class AssignmentRecommendationsRequestedPayload(BaseModel):
    """
    Worker input contract for generating recommendation documents.
    """

    week_start: date
    roles: list[RecommendationRoleInput] = Field(min_length=1)

    @field_validator("roles")
    @classmethod
    def validate_unique_role_codes(
        cls,
        value: list[RecommendationRoleInput],
    ) -> list[RecommendationRoleInput]:
        role_codes = [role.role_code for role in value]
        if len(role_codes) != len(set(role_codes)):
            raise ValueError("Recommendation request payload must contain unique role_code values")
        return value


class AssignmentInput(BaseModel):
    """
    Input for a single role assignment within a finalized week.
    """

    role_code: str = Field(min_length=1, max_length=128)
    user_id: str = Field(min_length=1, max_length=128)
    source: Literal["auto", "manual_override"]


class AssignmentHistoryFinalizedPayload(BaseModel):
    """
    Worker input contract for persisting a weekly assignment history entry.
    """

    week_start: date
    assignments: list[AssignmentInput]
    finalized_by: str = Field(min_length=1, max_length=128)

    @field_validator("assignments")
    @classmethod
    def validate_unique_role_codes(cls, value: list[AssignmentInput]) -> list[AssignmentInput]:
        role_codes = [assignment.role_code for assignment in value]
        if len(role_codes) != len(set(role_codes)):
            raise ValueError("History finalization payload must contain unique role_code values")
        return value


class EventIngestionResponse(BaseModel):
    """
    Response body for accepted events.
    """

    status: Literal["accepted"] = "accepted"
    event_id: str
    correlation_id: str
    schema_version: int
    routing_key: str
    accepted_at: datetime


class DLQReplayResponse(BaseModel):
    """
    Response body for dead-letter queue replay attempts.
    """

    status: Literal["replayed", "empty"]
    message_id: str | None = None
    event_id: str | None = None
    routing_key: str | None = None
    replayed_at: datetime | None = None


def build_event_envelope(
    request: EventIngestionRequest,
    *,
    default_producer: str = "api",
) -> EventEnvelope:
    """
    Enriches ingress payload with required metadata to produce a canonical envelope.
    """

    now_utc = datetime.now(timezone.utc)
    occurred_at = request.occurred_at or now_utc

    return EventEnvelope(
        schema_version=request.schema_version,
        event_id=request.event_id or str(uuid4()),
        event_type=request.event_type,
        occurred_at=occurred_at,
        producer=request.producer or default_producer or "api",
        correlation_id=request.correlation_id or str(uuid4()),
        team_id=request.team_id,
        payload=request.payload,
    )
