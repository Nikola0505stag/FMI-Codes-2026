import io
import shutil
import threading
import urllib.request
import wave
import zipfile
from pathlib import Path

import numpy as np
from scipy import signal

from app.core.config import get_settings


class MLA:
    model_name = "mla"

    def __init__(self) -> None:
        self.settings = get_settings()
        self._lock = threading.Lock()
        self._loaded = False
        self._processor = None
        self._model = None
        self._torch = None
        self._device = None
        self._ai_idx = 1

    def _decode_wav_to_mono(self, wav_bytes: bytes) -> tuple[np.ndarray, int]:
        try:
            with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
                sample_rate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                frame_count = wav_file.getnframes()
                raw = wav_file.readframes(frame_count)
        except wave.Error as exc:
            raise ValueError("Invalid WAV content.") from exc

        if sample_rate <= 0 or channels <= 0 or sample_width <= 0:
            raise ValueError("Invalid WAV metadata.")

        if sample_width == 1:
            samples = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
            samples = (samples - 128.0) / 128.0
        elif sample_width == 2:
            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        elif sample_width == 4:
            samples = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
        else:
            raise ValueError("Only 8/16/32-bit WAV is supported.")

        if samples.size == 0:
            raise ValueError("Uploaded WAV has no audio samples.")

        if channels > 1:
            usable = samples.size - (samples.size % channels)
            samples = samples[:usable].reshape(-1, channels).mean(axis=1)

        return samples, sample_rate

    def _preprocess(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        target_sr = self.settings.model_target_sr
        target_duration = self.settings.model_target_duration_sec
        target_len = int(target_sr * target_duration)

        if sample_rate != target_sr:
            audio = signal.resample_poly(audio, target_sr, sample_rate).astype(np.float32)

        if audio.shape[0] > target_len:
            audio = audio[:target_len]
        elif audio.shape[0] < target_len:
            audio = np.pad(audio, (0, target_len - audio.shape[0]), mode="constant")

        max_val = float(np.max(np.abs(audio))) if audio.size else 0.0
        if max_val > 0.0:
            audio = audio / max_val

        return audio.astype(np.float32)

    def _candidate_model_dirs(self) -> list[Path]:
        backend_root = Path(__file__).resolve().parents[2]
        candidates: list[Path] = []

        if self.settings.model_dir:
            candidates.append(Path(self.settings.model_dir))

        # Known local layouts used in this repository.
        candidates.append(backend_root / "model" / "trained_model")
        candidates.append(backend_root / "model" / "cache" / "release_model" / "kaggle" / "working" / "trained_model")
        candidates.append(backend_root / "trained_model")

        # Discover additional nested local model dirs under backend/model.
        model_root = backend_root / "model"
        if model_root.exists():
            discovered = sorted({p.parent for p in model_root.rglob("config.json")})
            candidates.extend(discovered)

        return candidates

    def _looks_like_hf_model_dir(self, model_dir: Path) -> bool:
        return (model_dir / "config.json").exists() and (
            (model_dir / "model.safetensors").exists() or (model_dir / "pytorch_model.bin").exists()
        )

    def _extract_model_zip(self, zip_path: Path) -> Path:
        cache_root = Path(__file__).resolve().parents[2] / "model" / "cache"
        cache_root.mkdir(parents=True, exist_ok=True)
        extract_dir = cache_root / zip_path.stem

        if extract_dir.exists() and self._looks_like_hf_model_dir(extract_dir):
            return extract_dir

        # If a previous extraction already contains a nested valid model dir,
        # reuse it instead of deleting and extracting every startup.
        if extract_dir.exists():
            for config_path in extract_dir.rglob("config.json"):
                candidate = config_path.parent
                if self._looks_like_hf_model_dir(candidate):
                    return candidate

        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        extract_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

        if self._looks_like_hf_model_dir(extract_dir):
            return extract_dir

        nested = [p for p in extract_dir.rglob("config.json") if p.parent.is_dir()]
        for config_path in nested:
            if self._looks_like_hf_model_dir(config_path.parent):
                return config_path.parent

        raise RuntimeError(f"Model zip '{zip_path}' does not contain a valid Hugging Face model directory.")

    def _resolve_model_dir(self) -> Path:
        for candidate in self._candidate_model_dirs():
            if self._looks_like_hf_model_dir(candidate):
                return candidate

        if self.settings.model_zip_path:
            zip_path = Path(self.settings.model_zip_path)
            if not zip_path.exists():
                raise RuntimeError(f"MODEL_ZIP_PATH does not exist: {zip_path}")
            return self._extract_model_zip(zip_path)

        if self.settings.model_release_url:
            cache_root = Path(__file__).resolve().parents[2] / "model" / "downloads"
            cache_root.mkdir(parents=True, exist_ok=True)
            zip_path = cache_root / "release_model.zip"
            if not zip_path.exists() or zip_path.stat().st_size == 0:
                urllib.request.urlretrieve(self.settings.model_release_url, zip_path)
            return self._extract_model_zip(zip_path)

        raise RuntimeError(
            "No model artifacts found. Set one of MODEL_DIR, MODEL_ZIP_PATH, or MODEL_RELEASE_URL."
        )

    def _resolve_ai_index(self, id2label: dict) -> int:
        ai_candidates = {"ai", "fake", "synthetic", "generated"}
        real_candidates = {"real", "human"}

        ai_idx = None
        real_idx = None
        for idx, label in id2label.items():
            label_text = str(label).lower()
            if any(token in label_text for token in ai_candidates):
                ai_idx = int(idx)
            if any(token in label_text for token in real_candidates):
                real_idx = int(idx)

        if ai_idx is not None:
            return ai_idx
        if real_idx is not None:
            return 1 - real_idx if real_idx in {0, 1} else 1
        return 1

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        with self._lock:
            if self._loaded:
                return

            try:
                import torch
                from transformers import Wav2Vec2ForSequenceClassification, Wav2Vec2Processor
            except ImportError as exc:
                raise RuntimeError(
                    "Missing model dependencies. Install 'torch' and 'transformers' in backend environment."
                ) from exc

            model_dir = self._resolve_model_dir()
            processor = Wav2Vec2Processor.from_pretrained(str(model_dir))
            model = Wav2Vec2ForSequenceClassification.from_pretrained(str(model_dir))

            requested_device = self.settings.model_device.lower().strip()
            if requested_device == "cuda" and not torch.cuda.is_available():
                requested_device = "cpu"

            device = torch.device(requested_device)
            model = model.to(device)
            model.eval()

            id2label = getattr(model.config, "id2label", None) or {0: "real", 1: "ai"}

            self._torch = torch
            self._processor = processor
            self._model = model
            self._device = device
            self._ai_idx = self._resolve_ai_index(id2label)
            self._loaded = True

    def predict(self, wav_bytes: bytes) -> dict:
        self._ensure_loaded()

        audio, sample_rate = self._decode_wav_to_mono(wav_bytes)
        audio = self._preprocess(audio, sample_rate)

        inputs = self._processor(
            audio,
            sampling_rate=self.settings.model_target_sr,
            return_tensors="pt",
            padding=True,
        )
        inputs = {k: v.to(self._device) for k, v in inputs.items()}

        with self._torch.no_grad():
            outputs = self._model(**inputs)

        probs = self._torch.softmax(outputs.logits, dim=-1)[0].detach().cpu().numpy()
        if probs.shape[0] <= self._ai_idx:
            raise RuntimeError("Model output does not contain expected AI class index.")

        ai_prob = float(probs[self._ai_idx])
        status = "ai" if ai_prob >= 0.5 else "real"
        accuracy = ai_prob if status == "ai" else (1.0 - ai_prob)

        return {"status": status, "accuracy": max(0.0, min(1.0, accuracy))}


mla = MLA()
