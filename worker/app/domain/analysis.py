from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class AnalysisStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class TranscriptTurn:
    speaker: str
    text: str
    start_seconds: float | None = None
    end_seconds: float | None = None


@dataclass(frozen=True)
class AnalysisOutput:
    transcript: list[dict[str, Any]]
    summary: list[str]
    sentiment: str
    sentiment_reason: str
    confidence: float
