from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

# Project root's Sessions/ folder — sibling to README.md and the .command
# launcher, so it's easy to find in Finder.
SESSIONS_DIR = Path(__file__).resolve().parent.parent.parent / "Sessions"


class SessionRecorder:
    """Appends every environment_event to a timestamped JSONL file for the
    duration of one Start/Stop Session cycle — one file per session.

    JSONL (one JSON object per line, flushed after every write) rather than
    a single JSON array, so a crash mid-session still leaves every event up
    to that point readable, instead of one truncated/invalid file.
    """

    def __init__(self, sessions_dir: Path = SESSIONS_DIR):
        self._sessions_dir = sessions_dir
        self._file = None

    def start(self) -> Path:
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path = self._sessions_dir / f"{timestamp}.jsonl"
        self._file = path.open("w", encoding="utf-8")
        self._write({"event": "SessionStarted", "started_at": datetime.now().isoformat()})
        return path

    def record(self, event: dict):
        if self._file is None:
            return
        self._write({"timestamp": datetime.now().isoformat(), **event})

    def stop(self):
        if self._file is None:
            return
        self._write({"event": "SessionStopped", "stopped_at": datetime.now().isoformat()})
        self._file.close()
        self._file = None

    def _write(self, record: dict):
        self._file.write(json.dumps(record) + "\n")
        self._file.flush()
