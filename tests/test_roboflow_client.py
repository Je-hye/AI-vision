from datetime import datetime, timezone

from app.roboflow_client import parse_roboflow_predictions


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
