"""
Application configuration using Pydantic settings.
"""

from sqlalchemy.engine import URL
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "Role Manager API"
    app_version: str = "0.1.0"
    debug: bool = True

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS - allowed origins for React frontend
    cors_origins: list[str] = ["http://localhost:3000"]

    # Database
    database_host: str = "localhost"
    database_port: int = 5432
    database_user: str = "postgres"
    database_password: str = ""
    database_name: str = "role_manager_dev"

    @property
    def database_url(self) -> str:
        """Construct async PostgreSQL URL for asyncpg."""
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.database_user,
            password=self.database_password,
            host=self.database_host,
            port=self.database_port,
            database=self.database_name,
        ).render_as_string(hide_password=False)

    @property
    def database_url_sync(self) -> str:
        """Construct sync PostgreSQL URL for psycopg2 (used by Alembic)."""
        return URL.create(
            drivername="postgresql+psycopg2",
            username=self.database_user,
            password=self.database_password,
            host=self.database_host,
            port=self.database_port,
            database=self.database_name,
        ).render_as_string(hide_password=False)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
