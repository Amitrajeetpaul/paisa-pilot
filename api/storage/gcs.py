"""Cloud Storage upload backend. Not exercised by the automated test suite
(no GCP credentials in CI) -- see LIMITATIONS.md. Server-side encryption is
on by default for all GCS buckets; the TTL is enforced by the bucket's own
lifecycle rule (infra/cloud_storage_lifecycle.json), so delete_expired() is
a no-op here rather than a client-side scan.

google-cloud-storage is imported lazily so importing this module (or the
whole api package) never requires it unless STORAGE_BACKEND=gcs.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from api.storage.base import UploadStorage


class GcsUploadStorage(UploadStorage):
    def __init__(self, bucket_name: str) -> None:
        from google.cloud import storage  # lazy import, see module docstring

        self._client = storage.Client()
        self._bucket = self._client.bucket(bucket_name)

    def save(self, key: str, content: bytes) -> None:
        blob = self._bucket.blob(key)
        blob.upload_from_string(content)

    def read(self, key: str) -> bytes:
        blob = self._bucket.blob(key)
        if not blob.exists():
            raise FileNotFoundError(f"No upload found for key {key!r} (never existed, or deleted after TTL)")
        return blob.download_as_bytes()

    def delete(self, key: str) -> None:
        self._bucket.blob(key).delete(timeout=30)

    def delete_expired(self, ttl_hours: int) -> int:
        return 0  # handled server-side by the bucket's lifecycle rule

    def generate_signed_upload_url(self, key: str, content_type: str, expires_minutes: int = 15) -> Any:
        """Lets the browser upload directly to GCS instead of through the
        API. Not wired into the current upload flow (api/routers/documents.py
        takes multipart uploads through the API directly, which is simpler
        for the demo) -- available for a later direct-upload optimization.
        See docs/ROADMAP.md."""
        blob = self._bucket.blob(key)
        return blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=expires_minutes),
            method="PUT",
            content_type=content_type,
        )
