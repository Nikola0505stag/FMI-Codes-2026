from functools import lru_cache
from pydantic import BaseModel
import os


class Settings(BaseModel):
    app_name: str = os.getenv("APP_NAME", "AI Voice Detector API")
    app_version: str = os.getenv("APP_VERSION", "1.0.0")
    max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "20"))
    allowed_extensions: tuple[str, ...] = tuple(
        ext.strip().lower()
        for ext in os.getenv("ALLOWED_EXTENSIONS", ".wav").split(",")
        if ext.strip()
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
