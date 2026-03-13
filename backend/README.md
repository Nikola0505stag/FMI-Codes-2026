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
  "accuracy": 0.91
}
```

## Model Contract

`app/ml/mla.py` -> `MLA.predict(wav_bytes: bytes) -> dict`

```python
{"status": "ai" | "real", "accuracy": 0.0..1.0}
```

## Common Errors

- `400`: invalid file or not real WAV
- `413`: file too large
- `500`: model inference failure
