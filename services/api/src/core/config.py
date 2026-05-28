import os
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

    # Taskiq Configurations
    TASKIQ_DASHBOARD_TOKEN: str = os.getenv("TASKIQ_DASHBOARD_TOKEN", "supersecret")
    TASKIQ_DASHBOARD_PATH: str = os.getenv("TASKIQ_DASHBOARD_PATH", "/admin")
    TASKIQ_DASHBOARD_URL: str = os.getenv("TASKIQ_DASHBOARD_URL", "http://localhost:8000/admin")
    TASKIQ_WORKER_RELOAD: bool = os.getenv("TASKIQ_WORKER_RELOAD", "True").lower() == "true"



    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
