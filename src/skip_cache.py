"""
Remember listings a task already rejected *after* opening their detail page (for
example a seller below the required level), so later runs do not spend another
detail request on them. Entries expire so a seller that improved gets a second look.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from typing import Optional

DEFAULT_PATH = os.path.join("logs", "task-skip-cache.json")
DEFAULT_TTL_SECONDS = 7 * 24 * 3600
_lock = threading.Lock()


class SkipCache:
    def __init__(self, path: str = DEFAULT_PATH, ttl_seconds: float = DEFAULT_TTL_SECONDS):
        self.path = path
        self.ttl_seconds = ttl_seconds

    def _load(self) -> dict:
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _write(self, data: dict) -> None:
        directory = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(directory, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".skip-", suffix=".tmp", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False)
            os.replace(tmp, self.path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    def has(self, task: str, key: str, *, now: Optional[float] = None) -> bool:
        stamp = self._load().get(task, {}).get(key)
        if not isinstance(stamp, (int, float)):
            return False
        return (time.time() if now is None else now) - stamp < self.ttl_seconds

    def add(self, task: str, key: str, *, now: Optional[float] = None) -> None:
        current = time.time() if now is None else now
        with _lock:
            data = self._load()
            entries = {k: v for k, v in (data.get(task) or {}).items()
                       if isinstance(v, (int, float)) and current - v < self.ttl_seconds}
            entries[key] = current
            data[task] = entries
            self._write(data)
