import json
from pathlib import Path
from threading import Lock

from app.models import GestureEvent


class EventStore:
    def __init__(self, path: Path, max_events: int = 200) -> None:
        self.path = path
        self.max_events = max_events
        self._lock = Lock()
        self._events: list[GestureEvent] = []
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def add(self, event: GestureEvent) -> None:
        with self._lock:
            self._events.insert(0, event)
            self._events = self._events[: self.max_events]
            with self.path.open("a", encoding="utf-8") as file:
                file.write(event.model_dump_json() + "\n")

    def list(self) -> list[GestureEvent]:
        with self._lock:
            return list(self._events)

    def _load(self) -> None:
        if not self.path.exists():
            return
        loaded: list[GestureEvent] = []
        for line in self.path.read_text(encoding="utf-8").splitlines()[-self.max_events :]:
            if not line.strip():
                continue
            try:
                loaded.append(GestureEvent.model_validate(json.loads(line)))
            except ValueError:
                continue
        self._events = list(reversed(loaded))
