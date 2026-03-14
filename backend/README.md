# AI Voice Detector Backend

FastAPI API for voice classification (`.wav` in, JSON out).

## Run (PowerShell)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Docs: `http://127.0.0.1:8000/docs`

## Endpoints

- `GET /health` -> `{"status": "ok"}`
- `POST /predict` -> multipart form-data field `file` (`.wav` only)

## Test `/predict`

```powershell
curl.exe -X POST "http://127.0.0.1:8000/predict" `
  -H "accept: application/json" `
  -F "file=@C:\path\to\sample.wav;type=audio/wav"
```

## Response Format

```json
{
  "status": "ai",
  "accuracy": 0.91,
  "analysis_id": "a1b2c3d4e5f6",
  "suspicious_parts": [
    {
      "start_sec": 2.25,
      "end_sec": 3.0,
      "score": 0.88,
      "mel_image_url": "/artifacts/a1b2c3d4e5f6/part-0-mel.png",
      "mfcc_image_url": "/artifacts/a1b2c3d4e5f6/part-0-mfcc.png"
    }
  ]
}
```

Notes:

- `suspicious_parts` is empty when `status` is `real`.
- The `/artifacts/...` URLs are static files served by FastAPI.
- Artifact images are real feature visualizations generated from audio windows (not placeholders).

## Model Contract

`app/ml/mla.py` -> `MLA.predict(wav_bytes: bytes) -> dict`

```python
{"status": "ai" | "real", "accuracy": 0.0..1.0}
```

`app/services/inference.py` enriches this model output with:

- `analysis_id`
- `suspicious_parts[]`
  - `start_sec`, `end_sec`, `score`
  - `mel_image_url`, `mfcc_image_url`

Static files are exposed at `/artifacts/<analysis_id>/...`.

## Common Errors

- `400`: invalid file or not real WAV
- `413`: file too large
- `500`: model inference failure
