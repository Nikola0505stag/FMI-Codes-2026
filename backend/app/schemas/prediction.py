from pydantic import BaseModel, Field
from typing import List


class SuspiciousPart(BaseModel):
    start_sec: float = Field(ge=0.0, description="Segment start timestamp in seconds.")
    end_sec: float = Field(gt=0.0, description="Segment end timestamp in seconds.")
    score: float = Field(ge=0.0, le=1.0, description="Relative suspicion score for this segment.")
    mel_image_url: str = Field(description="Public URL to a mel spectrogram image.")
    mfcc_image_url: str = Field(description="Public URL to an MFCC image.")


class PredictionResponse(BaseModel):
    status: str = Field(description="Predicted class label, e.g. 'ai' or 'real'.")
    accuracy: float = Field(ge=0.0, le=1.0, description="Model confidence score.")
    analysis_id: str = Field(description="Unique id for this analysis result.")
    suspicious_parts: List[SuspiciousPart] = Field(
        default_factory=list,
        description="Suspicious audio segments with visualization URLs. Empty for non-AI results.",
    )


class ErrorResponse(BaseModel):
    detail: str
