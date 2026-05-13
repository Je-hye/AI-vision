from functools import lru_cache
import os
from pathlib import Path

from pydantic import BaseModel, Field


class Settings(BaseModel):
    roboflow_api_key: str = Field(default="", alias="ROBOFLOW_API_KEY")
    roboflow_model_id: str = Field(
        default="roboflow-100/hand-gestures-jps7z/1", alias="ROBOFLOW_MODEL_ID"
    )
    roboflow_api_url: str = Field(default="https://detect.roboflow.com", alias="ROBOFLOW_API_URL")
    confidence_threshold: float = Field(default=0.5, alias="CONFIDENCE_THRESHOLD", ge=0.0, le=1.0)
    frame_sample_fps: float = Field(default=1.0, alias="FRAME_SAMPLE_FPS", gt=0.0, le=30.0)
    consecutive_frames: int = Field(default=2, alias="CONSECUTIVE_FRAMES", ge=1)
    event_cooldown_seconds: float = Field(default=5.0, alias="EVENT_COOLDOWN_SECONDS", ge=0.0)
    event_log_path: Path = Field(default=Path("data/events.jsonl"), alias="EVENT_LOG_PATH")
    snapshot_dir: Path = Field(default=Path("data/snapshots"), alias="SNAPSHOT_DIR")


@lru_cache
def get_settings() -> Settings:
    env = _load_dotenv(Path(".env"))
    data = {**env, **os.environ}
    return Settings.model_validate(data)


def _load_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values
