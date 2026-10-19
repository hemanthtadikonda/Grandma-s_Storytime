from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    queued = "queued"
    scripting = "scripting"
    tts = "tts"
    images = "images"
    rendering = "rendering"
    uploading = "uploading"
    done = "done"
    failed = "failed"


class SubmitJobRequest(BaseModel):
    prompt: str = Field(min_length=1)
    template_id: str = "kids_moral_v1"
    duration_target_sec: int = Field(default=60, ge=15, le=180)
    content_source: str = Field(default="original", pattern="^(original|public_domain)$")
    idempotency_key: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class JobRecord(BaseModel):
    id: str
    status: JobStatus
    prompt: str
    template_id: str
    duration_target_sec: int
    content_source: str
    idempotency_key: str
    created_at: datetime
    updated_at: datetime
    error: Optional[str] = None
    script: Optional[dict[str, Any]] = None
    artifact_key: Optional[str] = None
    artifact_bytes: Optional[int] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @staticmethod
    def now() -> datetime:
        return datetime.now(timezone.utc)


class JobResponse(BaseModel):
    id: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    error: Optional[str] = None
    artifact_id: Optional[str] = None
    download_url: Optional[str] = None
    cached: bool = False


class ArtifactResponse(BaseModel):
    id: str
    job_id: str
    content_type: str = "video/mp4"
    bytes: Optional[int] = None
    download_url: str
