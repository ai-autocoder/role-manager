"""
Event contracts for ingestion and worker processing.
"""

from datetime import datetime, timezone
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
