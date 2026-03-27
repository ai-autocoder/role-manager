"""
Tests for the team CRUD API endpoints.
"""

from fastapi.testclient import TestClient

from app.main import app
from app.services.teams import TeamServiceError, get_team_service


class FakeTeamService:
    def __init__(self, mock_team: dict = None, mock_error: bool = False):
        self._mock_team = mock_team
        self._mock_error = mock_error

    async def get_team(self, team_id: str):
        if self._mock_error:
            raise TeamServiceError("database unavailable")
        if self._mock_team and self._mock_team.get("team_id") == team_id:
            return self._mock_team
        return None

    async def create_team(self, name: str, roles: list, users: list):
        if self._mock_error:
            raise TeamServiceError("database unavailable")
        return {
            "team_id": "team_generated_abc",
            "name": name,
            "roles": roles,
            "users": users,
        }


# --- GET /teams/{team_id} tests ---

def test_get_team_success() -> None:
    mock_team_data = {
        "team_id": "team_123",
        "name": "Platform Team",
        "roles": [{"code": "role_1", "name": "Role 1", "enabled": True}],
        "users": [{
            "user_id": "user_456",
            "name": "Alex",
            "qualifications": [{"role_code": "role_1", "motivation_factor": 1.0}]
        }]
    }

    app.dependency_overrides[get_team_service] = lambda: FakeTeamService(mock_team=mock_team_data)

    try:
        with TestClient(app) as client:
            response = client.get("/teams/team_123")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["team_id"] == "team_123"
    assert body["name"] == "Platform Team"
    assert len(body["roles"]) == 1
    assert body["roles"][0]["code"] == "role_1"
    assert len(body["users"]) == 1
    assert body["users"][0]["user_id"] == "user_456"


def test_get_team_not_found() -> None:
    app.dependency_overrides[get_team_service] = lambda: FakeTeamService(mock_team=None)

    try:
        with TestClient(app) as client:
            response = client.get("/teams/nonexistent_team")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_team_returns_500_on_service_error() -> None:
    app.dependency_overrides[get_team_service] = lambda: FakeTeamService(mock_error=True)

    try:
        with TestClient(app) as client:
            response = client.get("/teams/team_123")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert "database unavailable" in response.json()["detail"]


# --- POST /teams tests ---

def test_create_team_success() -> None:
    app.dependency_overrides[get_team_service] = lambda: FakeTeamService()

    try:
        with TestClient(app) as client:
            response = client.post("/teams", json={
                "name": "New Team",
                "roles": [{"code": "role_a", "name": "Role A", "enabled": True}],
                "users": [],
            })
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "New Team"
    assert body["team_id"] == "team_generated_abc"
    assert len(body["roles"]) == 1
    assert body["roles"][0]["code"] == "role_a"


def test_create_team_minimal_payload() -> None:
    """Only name is required; roles and users default to empty lists."""
    app.dependency_overrides[get_team_service] = lambda: FakeTeamService()

    try:
        with TestClient(app) as client:
            response = client.post("/teams", json={"name": "Minimal Team"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Minimal Team"
    assert body["roles"] == []
    assert body["users"] == []


def test_create_team_missing_name_returns_422() -> None:
    app.dependency_overrides[get_team_service] = lambda: FakeTeamService()

    try:
        with TestClient(app) as client:
            response = client.post("/teams", json={"roles": []})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_create_team_returns_500_on_service_error() -> None:
    app.dependency_overrides[get_team_service] = lambda: FakeTeamService(mock_error=True)

    try:
        with TestClient(app) as client:
            response = client.post("/teams", json={"name": "Broken Team"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert "database unavailable" in response.json()["detail"]
