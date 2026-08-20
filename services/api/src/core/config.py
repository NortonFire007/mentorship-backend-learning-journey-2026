import os
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "Mentorship Backend")
    API_V1_STR: str = os.getenv("API_V1_STR", "/api/v1")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    # Database
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "mentorship_db")

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # RabbitMQ
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

    # Taskiq Configurations
    TASKIQ_DASHBOARD_TOKEN: str = os.getenv("TASKIQ_DASHBOARD_TOKEN", "supersecret")
    TASKIQ_DASHBOARD_PATH: str = os.getenv("TASKIQ_DASHBOARD_PATH", "/admin")
    TASKIQ_DASHBOARD_URL: str = os.getenv("TASKIQ_DASHBOARD_URL", "http://localhost:8000/admin/")
    TASKIQ_DASHBOARD_DB_DSN: str = os.getenv(
        "TASKIQ_DASHBOARD_DB_DSN",
        "sqlite+aiosqlite:///taskiq_dashboard.db" if os.name == "nt" else "sqlite+aiosqlite:////tmp/taskiq_dashboard.db"
    )
    TASKIQ_WORKER_RELOAD: bool = os.getenv("TASKIQ_WORKER_RELOAD", "True").lower() == "true"

    # JWT Settings
    JWT_SECRET_KEY: str
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_BOT_USERNAME: str
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

    # MCP Admin Settings
    MCP_API_KEY: str

    # First Superuser Settings
    FIRST_SUPERUSER_EMAIL: str = os.getenv("FIRST_SUPERUSER_EMAIL", "admin@example.com")
    FIRST_SUPERUSER_PASSWORD: str = os.getenv("FIRST_SUPERUSER_PASSWORD", "adminpassword")

    # Auth Redis
    REDIS_AUTH_URL: str = os.getenv("REDIS_AUTH_URL", "redis://localhost:6379/1")

    # Rate Limiting & Grace Period
    MAX_LOGIN_ATTEMPTS: int = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
    LOGIN_LOCKOUT_MINUTES: int = int(os.getenv("LOGIN_LOCKOUT_MINUTES", "15"))
    REFRESH_GRACE_PERIOD_SECONDS: int = int(os.getenv("REFRESH_GRACE_PERIOD_SECONDS", "30"))

    # CORS
    CORS_ALLOWED_ORIGINS: list[str] | str = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Apify Settings
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")
    APIFY_API_TOKEN: str | None = os.getenv("APIFY_API_TOKEN", None)
    APIFY_WEBHOOK_SECRET: str | None = os.getenv("APIFY_WEBHOOK_SECRET", None)
    APIFY_ACTOR_ID: str = os.getenv("APIFY_ACTOR_ID", "automation-lab~airbnb-listing")
    APIFY_MAX_LISTINGS: int = int(os.getenv("APIFY_MAX_LISTINGS", "50"))
    APIFY_POLL_INTERVAL_MINUTES: int = int(os.getenv("APIFY_POLL_INTERVAL_MINUTES", "360"))
    APIFY_POLL_BATCH_SIZE: int = int(os.getenv("APIFY_POLL_BATCH_SIZE", "50"))
    APIFY_SUBSCRIPTION_RECHECK_HOURS: int = int(os.getenv("APIFY_SUBSCRIPTION_RECHECK_HOURS", "24"))

    @field_validator("CORS_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v



    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
