from __future__ import annotations

from functools import lru_cache

from api.db.base import AppDatabase
from api.settings import Settings, get_settings


@lru_cache(maxsize=1)
def get_db() -> AppDatabase:
    settings: Settings = get_settings()
    if settings.db_backend == "sqlite":
        from api.db.sqlite import SqliteDatabase

        return SqliteDatabase(settings.sqlite_path)
    if settings.db_backend == "firestore":
        from api.db.firestore import FirestoreDatabase

        if not settings.firestore_project:
            raise RuntimeError("FIRESTORE_PROJECT must be set when DB_BACKEND=firestore")
        return FirestoreDatabase(settings.firestore_project)
    raise ValueError(f"Unknown DB_BACKEND: {settings.db_backend!r}")
