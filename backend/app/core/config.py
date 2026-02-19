"""
Application configuration using Pydantic settings.
"""

from urllib.parse import quote

from sqlalchemy.engine import URL
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Application
    app_name: str = "Role Manager API"
    app_version: str = "0.1.0"
    debug: bool = True

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS - allowed origins for React frontend
    cors_origins: list[str] = ["http://localhost:3000"]

    # Event contracts
    default_event_producer: str = "api"

    # RabbitMQ
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "guest"
    rabbitmq_password: str = "guest"
    rabbitmq_vhost: str = "/"
    rabbitmq_exchange: str = "role_manager.events.topic"
    rabbitmq_compute_queue: str = "role_manager.assignments.compute"
    rabbitmq_compute_binding_key: str = "#"
    rabbitmq_dlq_queue: str = "role_manager.assignments.dlq"
    rabbitmq_dlq_routing_key: str = "events.dlq"
    rabbitmq_connect_timeout_seconds: int = 5

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    processed_event_ttl_seconds: int = 604800  # 7 days

    # MongoDB
    mongo_url: str = "mongodb://localhost:27017"
    mongo_database: str = "role_manager"

    # Worker
    worker_prefetch_count: int = 10

    # Database
    database_host: str = "localhost"
    database_port: int = 5432
    database_user: str = "postgres"
    database_password: str = ""
    database_name: str = "role_manager_dev"

    @property
    def rabbitmq_url(self) -> str:
        """
        Build RabbitMQ URL for aio-pika.
        Example: amqp://guest:guest@localhost:5672/%2F
        """
        username = quote(self.rabbitmq_user, safe="")
        password = quote(self.rabbitmq_password, safe="")
        # RabbitMQ requires the vhost segment URL-encoded.
        vhost_clean = self.rabbitmq_vhost.lstrip("/") or "/"
        vhost_encoded = quote(vhost_clean, safe="")
        return (
            f"amqp://{username}:{password}"
            f"@{self.rabbitmq_host}:{self.rabbitmq_port}/{vhost_encoded}"
        )

    @property
    def redis_url(self) -> str:
        """
        Build Redis URL for redis-py asyncio.
        """
        if self.redis_password:
            password = quote(self.redis_password, safe="")
            auth = f":{password}@"
        else:
            auth = ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

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

# Global settings instance
settings = Settings()
