import asyncio
import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

LOGGER = logging.getLogger("role_manager.services.teams")

class TeamServiceError(RuntimeError):
    """Raised when fetching team data fails."""

class TeamNotFoundError(TeamServiceError):
    """Raised when a team is not found."""

class MongoTeamService:
    def __init__(self) -> None:
        self._mongo_client: AsyncIOMotorClient | None = None
        self._mongo_db: AsyncIOMotorDatabase | None = None
        self._lock = asyncio.Lock()

    async def get_team(self, team_id: str) -> Optional[dict]:
        await self._ensure_connected()
        if self._mongo_db is None:
            raise TeamServiceError("MongoDB is not initialized for team fetch")

        try:
            team_doc = await self._mongo_db.teams.find_one({"team_id": team_id})
            return team_doc
        except Exception as exc:
            LOGGER.error("Failed to fetch team %s: %s", team_id, exc)
            raise TeamServiceError(str(exc)) from exc

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

team_service = MongoTeamService()

def get_team_service() -> MongoTeamService:
    return team_service
