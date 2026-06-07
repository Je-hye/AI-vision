from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import cv2

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
        self._latest_frame: bytes | None = None
        self._latest_frame_version = 0
        self._cleanup_transient_frames()

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
            if self._latest_frame is not None:
                status.latest_frame_url = f"/frame/latest?ts={self._latest_frame_version}"
            return status

    def latest_frame(self) -> bytes | None:
        with self._lock:
            return self._latest_frame

    def _run(
        self,
        stream_url: str,
        confidence_threshold: float,
        sample_fps: float,
        consecutive_frames: int,
        cooldown_seconds: float,
        target_classes: list[str],
    ) -> None:
        rule = GestureEventRule(consecutive_frames, cooldown_seconds, target_classes)

        # URL이 숫자면 웹캠 인덱스로 처리 (예: "0" -> 0)
        capture_source = int(stream_url) if stream_url.isdigit() else stream_url
        capture = cv2.VideoCapture(capture_source)
        if not capture.isOpened():
            self._set_error("failed to open stream")
            return

        next_analysis_at = 0.0
        next_preview_at = 0.0
        sample_interval = 1.0 / sample_fps
        preview_interval = 0.2
        executor = ThreadPoolExecutor(max_workers=1)
        pending_analysis: Future | None = None
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
                if now >= next_preview_at:
                    self._set_latest_frame(frame)
                    next_preview_at = now + preview_interval

                analysis_ready = pending_analysis is None or pending_analysis.done()
                if now >= next_analysis_at and analysis_ready:
                    frame_path = self._write_frame(frame, prefix="analysis")
                    pending_analysis = executor.submit(
                        self._analyze_frame,
                        rule,
                        frame_path,
                        confidence_threshold,
                        stream_url,
                    )
                    next_analysis_at = now + sample_interval
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
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

    def _set_latest_frame(self, frame) -> None:
        ok, encoded = cv2.imencode(".jpg", frame)
        if not ok:
            self._set_error("failed to encode frame")
            return
        height, width = frame.shape[:2]
        with self._lock:
            self._latest_frame = encoded.tobytes()
            self._latest_frame_version = time.time_ns()
            self._status.latest_frame_width = int(width)
            self._status.latest_frame_height = int(height)

    def _analyze_frame(
        self,
        rule: GestureEventRule,
        frame_path: Path,
        confidence_threshold: float,
        stream_url: str,
    ) -> None:
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
        finally:
            if not frame_path.exists():
                return
            has_event_snapshot = any(event.snapshot_path == str(frame_path) for event in self.event_store.list())
            if not has_event_snapshot:
                frame_path.unlink(missing_ok=True)

    def _set_error(self, message: str) -> None:
        with self._lock:
            self._status.last_error = message
            self._status.status = "error"

    def _cleanup_transient_frames(self) -> None:
        for pattern in ("latest-*.jpg", "analysis-*.jpg"):
            for path in self.snapshot_dir.glob(pattern):
                path.unlink(missing_ok=True)
