"""
FastAPI application entry point.
"""

from datetime import datetime, timezone
import logging

from fastapi import FastAPI
from fastapi import Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import check_database_connection
from app.schemas.events import (
    DLQReplayResponse,
    EventIngestionRequest,
    EventIngestionResponse,
    build_event_envelope,
)
from app.services.dlq_replay import (
    DLQReplayError,
    RabbitMQDLQReplayService,
    get_dlq_replay_service,
)
from app.services.messaging import EventPublishError, RabbitMQPublisher, get_event_publisher
from app.services.replay_audit import (
    MongoReplayAuditService,
    ReplayAuditError,
    get_replay_audit_service,
)

LOGGER = logging.getLogger("role_manager.api")

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API for Role Manager - team role assignment application",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    Returns the current status of the API and database connection.
    """
    db_status = await check_database_connection()

    # Overall status is "ok" only if database is connected
    overall_status = "ok" if db_status["status"] == "connected" else "degraded"

    return {
        "status": overall_status,
        "app_name": settings.app_name,
        "version": settings.app_version,
        "database": db_status,
    }


@app.get("/")
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }


@app.post(
    "/events",
    response_model=EventIngestionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_event(
    event_request: EventIngestionRequest,
    event_publisher: RabbitMQPublisher = Depends(get_event_publisher),
):
    """
    Ingest a scheduling event and publish it to RabbitMQ.
    """
    envelope = build_event_envelope(
        event_request,
        default_producer=settings.default_event_producer,
    )

    try:
        routing_key = await event_publisher.publish(envelope)
    except EventPublishError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to publish event: {exc}",
        ) from exc

    return EventIngestionResponse(
        event_id=envelope.event_id,
        correlation_id=envelope.correlation_id,
        schema_version=envelope.schema_version,
        routing_key=routing_key,
        accepted_at=datetime.now(timezone.utc),
    )


@app.post(
    "/events/dlq/replay",
    response_model=DLQReplayResponse,
    status_code=status.HTTP_200_OK,
)
async def replay_next_dlq_event(
    replay_service: RabbitMQDLQReplayService = Depends(get_dlq_replay_service),
    audit_service: MongoReplayAuditService = Depends(get_replay_audit_service),
):
    """
    Replay one message from DLQ back to the main event exchange.
    """
    try:
        replay_response = await replay_service.replay_next()
        await _record_replay_audit(
            audit_service,
            outcome=replay_response.status,
            message_id=replay_response.message_id,
            event_id=replay_response.event_id,
            routing_key=replay_response.routing_key,
        )
        return replay_response
    except DLQReplayError as exc:
        await _record_replay_audit(
            audit_service,
            outcome="failed",
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to replay DLQ message: {exc}",
        ) from exc


async def _record_replay_audit(
    audit_service: MongoReplayAuditService,
    *,
    outcome: str,
    message_id: str | None = None,
    event_id: str | None = None,
    routing_key: str | None = None,
    error: str | None = None,
) -> None:
    try:
        await audit_service.record_attempt(
            outcome=outcome,
            message_id=message_id,
            event_id=event_id,
            routing_key=routing_key,
            error=error,
        )
    except ReplayAuditError as audit_exc:
        LOGGER.warning("Replay audit write failed: %s", audit_exc)
