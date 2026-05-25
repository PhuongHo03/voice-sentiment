from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from uuid import UUID


class AnalysisInputType(StrEnum):
    AUDIO = "audio"
    TEXT = "text"


class AnalysisStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class AnalysisJob:
    id: UUID
    input_type: AnalysisInputType
    status: AnalysisStatus


@dataclass(frozen=True)
class AnalysisResult:
    job_id: UUID
    transcript: list[dict[str, Any]]
    summary: list[str]
    sentiment: str
    sentiment_reason: str
    confidence: float
