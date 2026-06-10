from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests

from app.models import BoundingBox, Detection


class RoboflowAPIError(RuntimeError):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(message)


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
        if response.status_code >= 400:
            raise RoboflowAPIError(response.status_code, _format_error(response))
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


def _format_error(response: requests.Response) -> str:
    if response.status_code in {401, 403}:
        reason = "Roboflow authentication failed. Check ROBOFLOW_API_KEY and model access."
    elif response.status_code == 429:
        reason = "Roboflow rate limit exceeded. Lower sample FPS or retry later."
    elif response.status_code >= 500:
        reason = "Roboflow service error. Retry later."
    else:
        reason = response.reason or "Roboflow request failed."
    return f"{response.status_code} {reason} url={_sanitize_url(response.url)}"


def _sanitize_url(url: str) -> str:
    parts = urlsplit(url)
    query = [
        (key, "***masked***" if key.lower() == "api_key" else value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
