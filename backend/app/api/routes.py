from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import get_settings
from app.schemas.prediction import PredictionResponse
from app.services.inference import run_inference

router = APIRouter()
settings = get_settings()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.post("/predict", response_model=PredictionResponse)
async def predict_voice(file: UploadFile = File(...)) -> PredictionResponse:
    filename = (file.filename or "").lower()
    extension_allowed = any(filename.endswith(ext) for ext in settings.allowed_extensions)

    if not extension_allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Only {', '.join(settings.allowed_extensions)} files are allowed.",
        )

    wav_bytes = await file.read()
    max_bytes = settings.max_file_size_mb * 1024 * 1024

    if len(wav_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size is {settings.max_file_size_mb} MB.",
        )

    # Basic signature check for RIFF/WAVE files.
    if not (wav_bytes.startswith(b"RIFF") and wav_bytes[8:12] == b"WAVE"):
        raise HTTPException(status_code=400, detail="Invalid WAV file format.")

    output = run_inference(wav_bytes)
    return PredictionResponse(**output)
