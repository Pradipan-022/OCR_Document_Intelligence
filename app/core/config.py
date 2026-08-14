from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "OCR Document Intelligence Platform"

    # Pillar 1 constraints
    ALLOWED_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".pdf"}
    MAX_FILE_SIZE_MB: int = 10
    MAX_BATCH_SIZE: int = 10  # Maximum documents per batch upload

    # PDF rendering quality (DPI)
    PDF_RENDER_DPI: int = 200

    # Storage directory setup
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "storage" / "uploads"

    class Config:
        env_file = ".env"


settings = Settings()
# Ensure uploads directory exists on startup
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)