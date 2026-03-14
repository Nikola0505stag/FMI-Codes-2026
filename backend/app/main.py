from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name, version=settings.app_version)

allow_all_origins = "*" in settings.cors_allow_origins
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"] if allow_all_origins else list(settings.cors_allow_origins),
	allow_credentials=not allow_all_origins,
	allow_methods=["*"],
	allow_headers=["*"],
)

artifacts_dir = Path(__file__).resolve().parent / "artifacts"
artifacts_dir.mkdir(parents=True, exist_ok=True)
app.mount("/artifacts", StaticFiles(directory=artifacts_dir), name="artifacts")

app.include_router(router)
