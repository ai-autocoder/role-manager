"""
FastAPI application entry point.
"""

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi import Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import check_database_connection
from app.schemas.events import (
    EventIngestionRequest,
    EventIngestionResponse,
    build_event_envelope,
)
from app.services.messaging import EventPublishError, RabbitMQPublisher, get_event_publisher

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
