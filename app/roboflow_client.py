from datetime import datetime, timezone
from pathlib import Path

import requests

from app.models import BoundingBox, Detection


class RoboflowClient:
    def __init__(self, api_url: str, api_key: str, model_id: str) -> None:
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.model_id = model_id.strip("/")

    def infer(self, image_path: Path, confidence_threshold: float) -> list[Detection]:
        if not self.api_key:
            raise RuntimeError("ROBOFLOW_API_KEY is not configured")

        url = f"{self.api_url}/{self.model_id}"
        params = {
            "api_key": self.api_key,
            "confidence": int(confidence_threshold * 100),
            "format": "json",
        }
        with image_path.open("rb") as image_file:
            response = requests.post(
                url,
                params=params,
                data=image_file.read(),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )
        response.raise_for_status()
        payload = response.json()
        return parse_roboflow_predictions(payload, datetime.now(timezone.utc))


def parse_roboflow_predictions(payload: dict, timestamp: datetime) -> list[Detection]:
    detections: list[Detection] = []
    for prediction in payload.get("predictions", []):
        class_name = str(prediction.get("class", "")).strip()
        if not class_name:
            continue
        detections.append(
            Detection(
                class_name=class_name,
                confidence=float(prediction.get("confidence", 0.0)),
                bbox=BoundingBox(
                    x=float(prediction.get("x", 0.0)),
                    y=float(prediction.get("y", 0.0)),
                    width=float(prediction.get("width", 0.0)),
                    height=float(prediction.get("height", 0.0)),
                ),
                timestamp=timestamp,
            )
        )
    return detections
