"""
Assignment finalization and history checking operations.
"""

from __future__ import annotations

import asyncio

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings


class HistoryCheckError(RuntimeError):
    """Raised when checking history persistence fails."""


class MongoHistoryCheckService:
    """
    Checks if assignment history already exists in MongoDB to prevent duplicate finalizations.
    """

    def __init__(self) -> None:
        self._mongo_client: AsyncIOMotorClient | None = None
        self._mongo_db: AsyncIOMotorDatabase | None = None
        self._lock = asyncio.Lock()

    async def is_week_finalized(self, team_id: str, week_start: str) -> bool:
        await self._ensure_connected()
        if self._mongo_db is None:
            raise HistoryCheckError("MongoDB is not initialized for history check")

        try:
            doc = await self._mongo_db.assignment_history.find_one(
                {
                    "team_id": team_id,
                    "week_start": week_start,
                }
            )
            return doc is not None
        except Exception as exc:
            raise HistoryCheckError(str(exc)) from exc

    async def _ensure_connected(self) -> None:
        if self._mongo_db is not None:
            return

        async with self._lock:
            if self._mongo_db is None:
                self._mongo_client = AsyncIOMotorClient(settings.mongo_url)
                self._mongo_db = self._mongo_client[settings.mongo_database]

    async def close(self) -> None:
        if self._mongo_client is not None:
            self._mongo_client.close()
        self._mongo_client = None
        self._mongo_db = None


history_check_service = MongoHistoryCheckService()


def get_history_check_service() -> MongoHistoryCheckService:
    return history_check_service
