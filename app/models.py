from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float


class Detection(BaseModel):
    class_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: BoundingBox
    timestamp: datetime


class GestureEvent(BaseModel):
    gesture: str
    confidence: float
    timestamp: datetime
    source: str
    bbox: BoundingBox
    snapshot_path: str | None = None


class StreamStartRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    stream_url: str
    confidence_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    frame_sample_fps: float | None = Field(default=None, gt=0.0, le=30.0)
    consecutive_frames: int | None = Field(default=None, ge=1)
    cooldown_seconds: float | None = Field(default=None, ge=0.0)
    target_classes: list[str] = Field(default_factory=list)

    @field_validator("stream_url")
    @classmethod
    def validate_stream_url(cls, value: str) -> str:
        if not value:
            raise ValueError("stream_url is required")
        if not value.startswith(("http://", "https://", "rtsp://", "rtsps://")):
            raise ValueError("stream_url must start with http://, https://, rtsp://, or rtsps://")
        return value


class StreamStatus(BaseModel):
    running: bool
    stream_url: str | None = None
    status: str
    last_error: str | None = None
    frame_count: int = 0
    analyzed_count: int = 0
    last_detections: list[Detection] = Field(default_factory=list)
    latest_frame_url: str | None = None


class HealthResponse(BaseModel):
    ok: bool
    roboflow_configured: bool
    model_id: str
