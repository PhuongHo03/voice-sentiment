from typing import Any
from datetime import datetime
from pydantic import BaseModel, Field


class TextAnalysisRequest(BaseModel):
    text: str = Field(min_length=1)


class JobAcceptedResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    name: str | None = None
    status: str
    input_type: str | None = None
    audio_object_key: str | None = None
    result: dict[str, Any] | None = None
    error_message: str | None = None


class RenameRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)


class AudioFromKeyRequest(BaseModel):
    object_key: str = Field(..., min_length=1)
    name: str | None = None


class SessionListItem(BaseModel):
    job_id: str
    name: str | None = None
    status: str
    input_type: str | None = None
    created_at: datetime
    sentiment: str | None = None
    confidence: float | None = None


class SessionListResponse(BaseModel):
    sessions: list[SessionListItem]
    total: int
    offset: int
    limit: int

