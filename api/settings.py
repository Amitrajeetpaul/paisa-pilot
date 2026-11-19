"""Env-driven settings. Defaults make local dev work with zero cloud
account: local disk for uploads, SQLite for confirmed fields/source trail.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    storage_backend: str  # "local" | "gcs"
    db_backend: str  # "sqlite" | "firestore"
    upload_ttl_hours: int
    local_storage_dir: str
    sqlite_path: str
    gcs_bucket: str | None
    firestore_project: str | None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        storage_backend=os.environ.get("STORAGE_BACKEND", "local"),
        db_backend=os.environ.get("DB_BACKEND", "sqlite"),
        upload_ttl_hours=int(os.environ.get("UPLOAD_TTL_HOURS", "24")),
        local_storage_dir=os.environ.get("LOCAL_STORAGE_DIR", "./.data/uploads"),
        sqlite_path=os.environ.get("SQLITE_PATH", "./.data/paisa_pilot.db"),
        gcs_bucket=os.environ.get("GCS_BUCKET"),
        firestore_project=os.environ.get("FIRESTORE_PROJECT"),
    )
