from functools import lru_cache
from pydantic import BaseModel
import os


class Settings(BaseModel):
    app_name: str = os.getenv("APP_NAME", "AI Voice Detector API")
    app_version: str = os.getenv("APP_VERSION", "1.0.0")
    max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "20"))
    allowed_extensions: tuple[str, ...] = tuple(
        ext.strip().lower()
        for ext in os.getenv("ALLOWED_EXTENSIONS", ".wav,.m4a").split(",")
        if ext.strip()
    )
    model_dir: str = os.getenv("MODEL_DIR", "")
    model_zip_path: str = os.getenv("MODEL_ZIP_PATH", "")
    model_release_url: str = os.getenv(
        "MODEL_RELEASE_URL",
        "https://github.com/Nikola0505stag/FMI-Code-2026/releases/download/v1.0/final_model.zip",
    )
    model_target_sr: int = int(os.getenv("MODEL_TARGET_SR", "16000"))
    model_target_duration_sec: float = float(os.getenv("MODEL_TARGET_DURATION_SEC", "3.0"))
    model_device: str = os.getenv("MODEL_DEVICE", "cpu")
    cors_allow_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
        if origin.strip()
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
