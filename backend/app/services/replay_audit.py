"""
Audit logging for DLQ replay operations.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

REPLAY_AUDIT_COLLECTION = "dlq_replay_audit"


class ReplayAuditError(RuntimeError):
    """Raised when replay audit persistence fails."""


class MongoReplayAuditService:
    """
    Persists replay attempt audit entries in MongoDB.
    """

    def __init__(self) -> None:
        self._mongo_client: AsyncIOMotorClient | None = None
        self._mongo_db: AsyncIOMotorDatabase | None = None
        self._index_ready = False
        self._lock = asyncio.Lock()

    async def record_attempt(
        self,
        *,
        outcome: str,
        message_id: str | None = None,
        event_id: str | None = None,
        routing_key: str | None = None,
        error: str | None = None,
    ) -> None:
        await self._ensure_connected()
        if self._mongo_db is None:
            raise ReplayAuditError("MongoDB is not initialized for replay audit")

        attempted_at = datetime.now(timezone.utc)
        document = {
            "audit_id": str(uuid4()),
            "outcome": outcome,
            "message_id": message_id,
            "event_id": event_id,
            "routing_key": routing_key,
            "error": error,
            "attempted_at": attempted_at,
        }
        try:
            await self._mongo_db[REPLAY_AUDIT_COLLECTION].insert_one(document)
        except Exception as exc:  # pragma: no cover - exercised in integration
            raise ReplayAuditError(str(exc)) from exc

    async def _ensure_connected(self) -> None:
        if self._mongo_db is not None and self._index_ready:
            return

        async with self._lock:
            if self._mongo_db is None:
                self._mongo_client = AsyncIOMotorClient(settings.mongo_url)
                self._mongo_db = self._mongo_client[settings.mongo_database]

            if not self._index_ready:
                try:
                    await self._mongo_db[REPLAY_AUDIT_COLLECTION].create_index(
                        [("attempted_at", -1)],
                        name="attempted_at_desc",
                    )
                    self._index_ready = True
                except Exception as exc:  # pragma: no cover - exercised in integration
                    raise ReplayAuditError(str(exc)) from exc

    async def close(self) -> None:
        if self._mongo_client is not None:
            self._mongo_client.close()
        self._mongo_client = None
        self._mongo_db = None
        self._index_ready = False


replay_audit_service = MongoReplayAuditService()


def get_replay_audit_service() -> MongoReplayAuditService:
    return replay_audit_service
