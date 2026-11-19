"""Local-disk upload storage for dev/CI. No cloud account needed."""

from __future__ import annotations

import time
from pathlib import Path

from api.storage.base import UploadStorage


class LocalUploadStorage(UploadStorage):
    def __init__(self, directory: str) -> None:
        self._dir = Path(directory)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self._dir / key

    def save(self, key: str, content: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def read(self, key: str) -> bytes:
        path = self._path(key)
        if not path.exists():
            raise FileNotFoundError(f"No upload found for key {key!r} (never existed, or deleted after TTL)")
        return path.read_bytes()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def delete_expired(self, ttl_hours: int) -> int:
        cutoff = time.time() - ttl_hours * 3600
        deleted = 0
        for path in self._dir.rglob("*"):
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()
                deleted += 1
        return deleted
