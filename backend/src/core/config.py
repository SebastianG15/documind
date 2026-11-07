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

    # Controles de seguridad y limites de cuota de ingesta
    MAX_FILE_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB por archivo
    MAX_DOSSIER_SIZE_BYTES: int = 75 * 1024 * 1024  # 75 MB por expediente completo
    MAX_FILES_PER_DOSSIER: int = 10  # Maximo de comprobantes por expediente

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
