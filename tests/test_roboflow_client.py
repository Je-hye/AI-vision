from datetime import datetime, timezone
from pathlib import Path

import pytest
import requests

from app.roboflow_client import RoboflowAPIError, RoboflowClient, _sanitize_url, parse_roboflow_predictions


def test_parse_roboflow_predictions() -> None:
    timestamp = datetime.now(timezone.utc)
    payload = {
        "predictions": [
            {
                "x": 189.5,
                "y": 100,
                "width": 163,
                "height": 186,
                "class": "thumbs_up",
                "confidence": 0.87,
            }
        ]
    }

    detections = parse_roboflow_predictions(payload, timestamp)

    assert len(detections) == 1
    assert detections[0].class_name == "thumbs_up"
    assert detections[0].confidence == 0.87
    assert detections[0].bbox.x == 189.5
    assert detections[0].timestamp == timestamp


def test_parse_roboflow_predictions_skips_empty_class() -> None:
    detections = parse_roboflow_predictions({"predictions": [{"class": "", "confidence": 0.9}]}, datetime.now(timezone.utc))

    assert detections == []


def test_sanitize_url_masks_api_key() -> None:
    sanitized = _sanitize_url("https://detect.roboflow.com/model/1?api_key=secret&confidence=50")

    assert "secret" not in sanitized
    assert "api_key=%2A%2A%2Amasked%2A%2A%2A" in sanitized


def test_infer_raises_sanitized_auth_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    image_path = tmp_path / "frame.jpg"
    image_path.write_bytes(b"frame")
    response = requests.Response()
    response.status_code = 401
    response.reason = "Unauthorized"
    response.url = "https://detect.roboflow.com/model/1?api_key=secret&confidence=50"

    def fake_post(*args, **kwargs):  # noqa: ANN001, ANN202
        return response

    monkeypatch.setattr(requests, "post", fake_post)
    client = RoboflowClient("https://detect.roboflow.com", "secret", "model/1")

    with pytest.raises(RoboflowAPIError) as exc_info:
        client.infer(image_path, 0.5)

    assert exc_info.value.status_code == 401
    assert "secret" not in str(exc_info.value)
    assert "authentication failed" in str(exc_info.value)
