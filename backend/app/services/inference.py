from fastapi import HTTPException

from app.ml.mla import mla


def run_inference(wav_bytes: bytes) -> dict:
    if not wav_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        result = mla.predict(wav_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Model inference failed.") from exc

    if "status" not in result or "accuracy" not in result:
        raise HTTPException(
            status_code=500,
            detail="Model output must include 'status' and 'accuracy'.",
        )

    status = str(result["status"]).lower().strip()
    accuracy = float(result["accuracy"])

    if status not in {"ai", "real"}:
        raise HTTPException(status_code=500, detail="Model status must be 'ai' or 'real'.")

    if accuracy < 0.0 or accuracy > 1.0:
        raise HTTPException(status_code=500, detail="Model accuracy must be in [0, 1].")

    return {
        "status": status,
        "accuracy": accuracy,
    }
