# FastAPI Backend (AI vs Real Voice)

## Project structure

```text
backend/
  app/
    api/
      __init__.py
      routes.py
    core/
      config.py
    ml/
      __init__.py
      mla.py
    schemas/
      __init__.py
      prediction.py
    services/
      __init__.py
      inference.py
    __init__.py
    main.py
  .env.example
  requirements.txt
  README.md
```

## Run locally

```bash
cd backend
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Endpoints

- `GET /health`
- `POST /predict` (multipart form-data with field name `file` and `.wav` file)

## cURL test

```bash
curl -X POST "http://127.0.0.1:8000/predict" ^
  -H "accept: application/json" ^
  -H "Content-Type: multipart/form-data" ^
  -F "file=@sample.wav;type=audio/wav"
```

## Expected response

```json
{
  "status": "ai",
  "accuracy": 0.91
}
```

## Integrate your real model

Model is implemented in `app/ml/mla.py` and returns:

- `{"status": "ai" | "real", "accuracy": 0.0..1.0}`
