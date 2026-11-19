from __future__ import annotations

from functools import lru_cache

from api.settings import Settings, get_settings
from api.storage.base import UploadStorage


@lru_cache(maxsize=1)
def get_storage() -> UploadStorage:
    settings: Settings = get_settings()
    if settings.storage_backend == "local":
        from api.storage.local import LocalUploadStorage

        return LocalUploadStorage(settings.local_storage_dir)
    if settings.storage_backend == "gcs":
        from api.storage.gcs import GcsUploadStorage

        if not settings.gcs_bucket:
            raise RuntimeError("GCS_BUCKET must be set when STORAGE_BACKEND=gcs")
        return GcsUploadStorage(settings.gcs_bucket)
    raise ValueError(f"Unknown STORAGE_BACKEND: {settings.storage_backend!r}")
