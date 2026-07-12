import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

from config import DATABASE_DIR


class JsonDB:
    _locks: dict[str, threading.Lock] = {}
    _global_lock = threading.Lock()

    def __init__(self, filename: str):
        self.path: Path = DATABASE_DIR / filename
        self._init_lock()

    def _init_lock(self) -> None:
        with self._global_lock:
            if self.path.name not in self._locks:
                self._locks[self.path.name] = threading.Lock()

    @property
    def _lock(self) -> threading.Lock:
        return self._locks[self.path.name]

    def _default_data(self) -> Any:
        return [] if self.path.name != "settings.json" else {}

    def _read(self) -> Any:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return self._default_data()
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return self._default_data()

    def _write(self, data: Any) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self.path.parent, delete=False) as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
            temp_path = f.name
        os.replace(temp_path, self.path)

    def read(self) -> Any:
        with self._lock:
            return self._read()

    def write(self, data: Any) -> None:
        with self._lock:
            self._write(data)

    def append(self, item: Any) -> list:
        with self._lock:
            data = self._read()
            if isinstance(data, list):
                data.append(item)
            elif isinstance(data, dict):
                key = str(len(data) + 1)
                data[key] = item
            self._write(data)
            return data

    def delete(self, pred) -> list:
        with self._lock:
            data = self._read()
            if isinstance(data, list):
                data = [x for x in data if not pred(x)]
            self._write(data)
            return data

    def update(self, pred, updates: dict) -> Any:
        with self._lock:
            data = self._read()
            if isinstance(data, list):
                for item in data:
                    if pred(item):
                        item.update(updates)
            elif isinstance(data, dict):
                for key, item in data.items():
                    if pred(item):
                        data[key].update(updates)
            self._write(data)
            return data


accounts_db = JsonDB("accounts.json")
uploads_db = JsonDB("uploads.json")
settings_db = JsonDB("settings.json")
users_db = JsonDB("users.json")
contents_db = JsonDB("contents.json")
schedules_db = JsonDB("schedules.json")
