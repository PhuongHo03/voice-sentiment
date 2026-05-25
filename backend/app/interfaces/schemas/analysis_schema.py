from typing import Any

from pydantic import BaseModel, Field


class TextAnalysisRequest(BaseModel):
    text: str = Field(min_length=1)


class JobAcceptedResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    input_type: str | None = None
    result: dict[str, Any] | None = None
    error_message: str | None = None
