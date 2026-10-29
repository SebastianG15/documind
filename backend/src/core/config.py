from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "DocuMind Financial AI"
    API_V1_STR: str = "/api/v1"

    POSTGRES_USER: str = "documind_user"
    POSTGRES_PASSWORD: str = "documind_pass"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "documind_db"
    DATABASE_URL: str = "postgresql://documind_user:documind_pass@localhost:5432/documind_db"

    UPLOAD_DIR: Path = Path("uploads")
    PROCESSED_DIR: Path = Path("uploads/processed")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
