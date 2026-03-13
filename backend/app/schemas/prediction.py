from pydantic import BaseModel, Field


class PredictionResponse(BaseModel):
    status: str = Field(description="Predicted class label, e.g. 'ai' or 'real'.")
    accuracy: float = Field(ge=0.0, le=1.0, description="Model confidence score.")


class ErrorResponse(BaseModel):
    detail: str
