from datetime import datetime, timezone

from app.event_rules import GestureEventRule
from app.models import BoundingBox, Detection


def make_detection(class_name: str, confidence: float = 0.9) -> Detection:
    return Detection(
        class_name=class_name,
        confidence=confidence,
        bbox=BoundingBox(x=10, y=20, width=30, height=40),
        timestamp=datetime.now(timezone.utc),
    )


def test_event_requires_consecutive_frames() -> None:
    rule = GestureEventRule(consecutive_frames=2, cooldown_seconds=5, target_classes=[])

    first = rule.evaluate([make_detection("wave")], source="rtsp://example", snapshot_path="frame.jpg")
    second = rule.evaluate([make_detection("wave")], source="rtsp://example", snapshot_path="frame.jpg")

    assert first is None
    assert second is not None
    assert second.gesture == "wave"


def test_event_respects_target_classes() -> None:
    rule = GestureEventRule(consecutive_frames=1, cooldown_seconds=5, target_classes=["thumbs_up"])

    ignored = rule.evaluate([make_detection("wave")], source="rtsp://example", snapshot_path=None)
    accepted = rule.evaluate([make_detection("thumbs_up")], source="rtsp://example", snapshot_path=None)

    assert ignored is None
    assert accepted is not None
    assert accepted.gesture == "thumbs_up"


def test_event_cooldown_prevents_duplicates() -> None:
    rule = GestureEventRule(consecutive_frames=1, cooldown_seconds=60, target_classes=[])

    first = rule.evaluate([make_detection("wave")], source="rtsp://example", snapshot_path=None)
    duplicate = rule.evaluate([make_detection("wave")], source="rtsp://example", snapshot_path=None)

    assert first is not None
    assert duplicate is None
