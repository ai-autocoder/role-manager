"""
FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import check_database_connection

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
