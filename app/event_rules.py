from datetime import datetime, timedelta, timezone

from app.models import Detection, GestureEvent


class GestureEventRule:
    def __init__(self, consecutive_frames: int, cooldown_seconds: float, target_classes: list[str]) -> None:
        self.consecutive_frames = consecutive_frames
        self.cooldown = timedelta(seconds=cooldown_seconds)
        self.target_classes = {item.strip() for item in target_classes if item.strip()}
        self._current_class: str | None = None
        self._current_count = 0
        self._last_event_at: dict[str, datetime] = {}

    def evaluate(self, detections: list[Detection], source: str, snapshot_path: str | None) -> GestureEvent | None:
        detection = self._best_detection(detections)
        if detection is None:
            self._current_class = None
            self._current_count = 0
            return None

        if detection.class_name == self._current_class:
            self._current_count += 1
        else:
            self._current_class = detection.class_name
            self._current_count = 1

        if self._current_count < self.consecutive_frames:
            return None

        now = datetime.now(timezone.utc)
        last_event = self._last_event_at.get(detection.class_name)
        if last_event is not None and now - last_event < self.cooldown:
            return None

        self._last_event_at[detection.class_name] = now
        return GestureEvent(
            gesture=detection.class_name,
            confidence=detection.confidence,
            timestamp=now,
            source=source,
            bbox=detection.bbox,
            snapshot_path=snapshot_path,
        )

    def _best_detection(self, detections: list[Detection]) -> Detection | None:
        candidates = [
            detection
            for detection in detections
            if not self.target_classes or detection.class_name in self.target_classes
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda item: item.confidence)
