from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.event_rules import GestureEventRule
from app.event_store import EventStore
from app.models import Detection, StreamStartRequest, StreamStatus
from app.roboflow_client import RoboflowClient


class StreamProcessor:
    def __init__(self, client: RoboflowClient, event_store: EventStore, snapshot_dir: Path) -> None:
        self.client = client
        self.event_store = event_store
        self.snapshot_dir = snapshot_dir
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._status = StreamStatus(running=False, status="idle")
        self._latest_frame_path: Path | None = None

    def start(self, request: StreamStartRequest, defaults: dict[str, float | int]) -> StreamStatus:
        self.stop()
        self._stop_event.clear()
        stream_url = str(request.stream_url)
        confidence = request.confidence_threshold
        if confidence is None:
            confidence = float(defaults["confidence_threshold"])
        sample_fps = request.frame_sample_fps
        if sample_fps is None:
            sample_fps = float(defaults["frame_sample_fps"])
        consecutive = request.consecutive_frames
        if consecutive is None:
            consecutive = int(defaults["consecutive_frames"])
        cooldown = request.cooldown_seconds
        if cooldown is None:
            cooldown = float(defaults["cooldown_seconds"])

        with self._lock:
            self._status = StreamStatus(running=True, stream_url=stream_url, status="starting")

        self._thread = threading.Thread(
            target=self._run,
            args=(stream_url, confidence, sample_fps, consecutive, cooldown, request.target_classes),
            daemon=True,
        )
        self._thread.start()
        return self.status()

    def stop(self) -> StreamStatus:
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout=5)
        with self._lock:
            if self._status.running:
                self._status.running = False
                self._status.status = "stopped"
        return self.status()

    def status(self) -> StreamStatus:
        with self._lock:
            status = self._status.model_copy(deep=True)
            if self._latest_frame_path is not None:
                status.latest_frame_url = f"/frame/latest?ts={int(time.time())}"
            return status

    def latest_frame_path(self) -> Path | None:
        with self._lock:
            return self._latest_frame_path

    def _run(
        self,
        stream_url: str,
        confidence_threshold: float,
        sample_fps: float,
        consecutive_frames: int,
        cooldown_seconds: float,
        target_classes: list[str],
    ) -> None:
        try:
            import cv2
        except ModuleNotFoundError:
            self._set_error("opencv-python is not installed")
            return

        rule = GestureEventRule(consecutive_frames, cooldown_seconds, target_classes)
        capture = cv2.VideoCapture(stream_url)
        if not capture.isOpened():
            self._set_error("failed to open stream")
            return

        next_analysis_at = 0.0
        sample_interval = 1.0 / sample_fps
        try:
            while not self._stop_event.is_set():
                ok, frame = capture.read()
                if not ok:
                    self._set_error("failed to read frame")
                    time.sleep(1)
                    continue

                with self._lock:
                    self._status.frame_count += 1
                    self._status.status = "running"

                now = time.monotonic()
                if now < next_analysis_at:
                    continue
                next_analysis_at = now + sample_interval

                frame_path = self._write_frame(frame, prefix="latest")
                try:
                    detections = [
                        item
                        for item in self.client.infer(frame_path, confidence_threshold)
                        if item.confidence >= confidence_threshold
                    ]
                    event = rule.evaluate(detections, stream_url, str(frame_path))
                    if event is not None:
                        self.event_store.add(event)
                    self._set_detections(detections, frame_path)
                except Exception as exc:
                    self._set_error(str(exc))
                    time.sleep(1)
        finally:
            capture.release()
            with self._lock:
                self._status.running = False
                if self._status.status == "running":
                    self._status.status = "stopped"

    def _write_frame(self, frame, prefix: str) -> Path:
        path = self.snapshot_dir / f"{prefix}-{uuid4().hex}.jpg"
        cv2.imwrite(str(path), frame)
        return path

    def _set_detections(self, detections: list[Detection], frame_path: Path) -> None:
        with self._lock:
            self._status.analyzed_count += 1
            self._status.last_error = None
            self._status.last_detections = detections
            self._latest_frame_path = frame_path

    def _set_error(self, message: str) -> None:
        with self._lock:
            self._status.last_error = message
            self._status.status = "error"
