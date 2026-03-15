import io
import wave
from pathlib import Path
from uuid import uuid4

import matplotlib
import numpy as np
from scipy import signal
from scipy.fftpack import dct
from fastapi import HTTPException

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from app.ml.mla import mla


ARTIFACTS_ROOT = Path(__file__).resolve().parents[1] / "artifacts"


def _decode_wav_to_mono_float(wav_bytes: bytes) -> tuple[np.ndarray, int]:
    try:
        with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
            sample_rate = wav_file.getframerate()
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            frame_count = wav_file.getnframes()
            raw = wav_file.readframes(frame_count)
    except wave.Error as exc:
        raise HTTPException(status_code=400, detail="Invalid WAV content.") from exc

    if sample_rate <= 0 or channels <= 0 or sample_width <= 0:
        raise HTTPException(status_code=400, detail="Invalid WAV metadata.")

    if sample_width == 1:
        samples = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
        samples = (samples - 128.0) / 128.0
    elif sample_width == 2:
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sample_width == 3:
        raw_u8 = np.frombuffer(raw, dtype=np.uint8)
        usable = (raw_u8.size // 3) * 3
        raw_u8 = raw_u8[:usable].reshape(-1, 3)

        # Convert little-endian 24-bit PCM to signed int32, then normalize.
        int_samples = (
            raw_u8[:, 0].astype(np.int32)
            | (raw_u8[:, 1].astype(np.int32) << 8)
            | (raw_u8[:, 2].astype(np.int32) << 16)
        )
        sign_mask = 1 << 23
        int_samples = (int_samples ^ sign_mask) - sign_mask
        samples = int_samples.astype(np.float32) / 8388608.0
    elif sample_width == 4:
        samples = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        raise HTTPException(status_code=400, detail="Only 8/16/24/32-bit WAV is supported.")

    if samples.size == 0:
        raise HTTPException(status_code=400, detail="Uploaded WAV has no audio samples.")

    if channels > 1:
        usable = samples.size - (samples.size % channels)
        samples = samples[:usable].reshape(-1, channels).mean(axis=1)

    return samples, sample_rate


def _hz_to_mel(freq_hz: float) -> float:
    return 2595.0 * np.log10(1.0 + (freq_hz / 700.0))


def _mel_to_hz(mel: np.ndarray) -> np.ndarray:
    return 700.0 * (10 ** (mel / 2595.0) - 1.0)


def _create_mel_filterbank(
    sample_rate: int,
    n_fft: int,
    n_mels: int = 64,
    fmin: float = 0.0,
    fmax: float | None = None,
) -> np.ndarray:
    if fmax is None:
        fmax = sample_rate / 2.0

    fft_freqs = np.linspace(0.0, sample_rate / 2.0, (n_fft // 2) + 1)
    mel_points = np.linspace(_hz_to_mel(fmin), _hz_to_mel(fmax), n_mels + 2)
    hz_points = _mel_to_hz(mel_points)
    bins = np.searchsorted(fft_freqs, hz_points)
    bins = np.clip(bins, 0, len(fft_freqs) - 1)

    filters = np.zeros((n_mels, len(fft_freqs)), dtype=np.float32)
    for i in range(1, n_mels + 1):
        left = bins[i - 1]
        center = bins[i]
        right = bins[i + 1]

        if center <= left:
            center = min(left + 1, len(fft_freqs) - 1)
        if right <= center:
            right = min(center + 1, len(fft_freqs) - 1)

        for j in range(left, center):
            filters[i - 1, j] = (j - left) / max(1, center - left)
        for j in range(center, right):
            filters[i - 1, j] = (right - j) / max(1, right - center)

    return filters


def _extract_suspicious_windows(
    samples: np.ndarray,
    sample_rate: int,
    max_parts: int = 3,
) -> list[tuple[float, float, float]]:
    if sample_rate <= 0 or samples.size == 0:
        return []

    window_size = max(1, int(sample_rate * 0.75))
    windows: list[tuple[float, float, float]] = []

    for start in range(0, samples.size, window_size):
        end = min(start + window_size, samples.size)
        segment = samples[start:end]
        if segment.size == 0:
            continue

        rms = float(np.sqrt(np.mean(np.square(segment), dtype=np.float64)))
        start_sec = start / sample_rate
        end_sec = end / sample_rate
        windows.append((start_sec, end_sec, rms))

    if not windows:
        return []

    max_rms = max(window[2] for window in windows) or 1.0
    top_windows = sorted(windows, key=lambda item: item[2], reverse=True)[:max_parts]
    top_windows.sort(key=lambda item: item[0])

    return [
        (start_sec, end_sec, round(min(1.0, rms / max_rms), 2))
        for start_sec, end_sec, rms in top_windows
    ]


def _compute_mel_and_mfcc(segment: np.ndarray, sample_rate: int) -> tuple[np.ndarray, np.ndarray]:
    n_fft = 1024
    hop_length = 256
    n_mels = 64
    n_mfcc = 20

    if segment.size < n_fft:
        segment = np.pad(segment, (0, n_fft - segment.size), mode="constant")

    _, _, stft = signal.stft(
        segment,
        fs=sample_rate,
        nperseg=n_fft,
        noverlap=n_fft - hop_length,
        nfft=n_fft,
        boundary="zeros",
        padded=True,
    )

    power = np.abs(stft) ** 2
    if power.size == 0:
        power = np.zeros(((n_fft // 2) + 1, 1), dtype=np.float32)

    mel_filters = _create_mel_filterbank(sample_rate, n_fft, n_mels=n_mels)
    mel_power = mel_filters @ power
    mel_power = np.maximum(mel_power, 1e-10)

    mel_db = 10.0 * np.log10(mel_power)
    mfcc = dct(np.log(mel_power), type=2, axis=0, norm="ortho")[:n_mfcc, :]

    return mel_db, mfcc


def _save_feature_plot(
    data: np.ndarray,
    file_path: Path,
    title: str,
    ylabel: str,
    cmap: str,
    duration_sec: float,
) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=120)
    im = ax.imshow(
        data,
        origin="lower",
        aspect="auto",
        interpolation="nearest",
        extent=[0.0, max(duration_sec, 0.001), 0, data.shape[0]],
        cmap=cmap,
    )
    ax.set_title(title)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel(ylabel)
    fig.colorbar(im, ax=ax, pad=0.015)
    fig.tight_layout()
    fig.savefig(file_path, format="png")
    plt.close(fig)


def _build_suspicious_parts(
    samples: np.ndarray,
    sample_rate: int,
    analysis_id: str,
) -> list[dict]:
    windows = _extract_suspicious_windows(samples, sample_rate)
    if not windows:
        return []

    analysis_dir = ARTIFACTS_ROOT / analysis_id
    analysis_dir.mkdir(parents=True, exist_ok=True)

    parts: list[dict] = []
    for index, (start_sec, end_sec, score) in enumerate(windows):
        mel_name = f"part-{index}-mel.png"
        mfcc_name = f"part-{index}-mfcc.png"
        mel_path = analysis_dir / mel_name
        mfcc_path = analysis_dir / mfcc_name

        start_sample = int(start_sec * sample_rate)
        end_sample = max(start_sample + 1, int(end_sec * sample_rate))
        segment = samples[start_sample:end_sample]
        if segment.size == 0:
            continue

        mel_db, mfcc = _compute_mel_and_mfcc(segment, sample_rate)
        segment_duration = segment.size / sample_rate

        _save_feature_plot(
            mel_db,
            mel_path,
            title=f"Mel Spectrogram ({start_sec:.2f}s - {end_sec:.2f}s)",
            ylabel="Mel bins",
            cmap="magma",
            duration_sec=segment_duration,
        )
        _save_feature_plot(
            mfcc,
            mfcc_path,
            title=f"MFCC ({start_sec:.2f}s - {end_sec:.2f}s)",
            ylabel="MFCC coeff",
            cmap="viridis",
            duration_sec=segment_duration,
        )

        parts.append(
            {
                "start_sec": round(start_sec, 3),
                "end_sec": round(end_sec, 3),
                "score": score,
                "mel_image_url": f"/artifacts/{analysis_id}/{mel_name}",
                "mfcc_image_url": f"/artifacts/{analysis_id}/{mfcc_name}",
            }
        )

    return parts


def run_inference(wav_bytes: bytes) -> dict:
    if not wav_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        result = mla.predict(wav_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"Model is not ready: {exc}") from exc
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

    analysis_id = uuid4().hex[:12]
    samples, sample_rate = _decode_wav_to_mono_float(wav_bytes)
    suspicious_parts = _build_suspicious_parts(samples, sample_rate, analysis_id) if status == "ai" else []

    return {
        "status": status,
        "accuracy": accuracy,
        "analysis_id": analysis_id,
        "suspicious_parts": suspicious_parts,
    }
