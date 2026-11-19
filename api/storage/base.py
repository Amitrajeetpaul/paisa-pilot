"""Upload storage interface. Two implementations behind this one contract:
local.py (disk, for dev/CI) and gcs.py (Cloud Storage, for deployment).
Swapped by STORAGE_BACKEND -- see api/settings.py and infra/deploy.md.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class UploadStorage(ABC):
    @abstractmethod
    def save(self, key: str, content: bytes) -> None:
        """Stores content under key, overwriting if it already exists."""

    @abstractmethod
    def read(self, key: str) -> bytes:
        """Raises FileNotFoundError if key doesn't exist or has expired/been deleted."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """No-op if key doesn't exist."""

    @abstractmethod
    def delete_expired(self, ttl_hours: int) -> int:
        """Deletes anything older than ttl_hours; returns count deleted.

        On GCS this is a no-op in practice (the bucket's own lifecycle rule
        -- infra/cloud_storage_lifecycle.json -- does the deleting
        server-side); it exists on this interface so local dev enforces
        the same "auto-delete uploads soon after use" rule without a real
        bucket. See DECISIONS.md.
        """

    @abstractmethod
    def delete_prefix(self, prefix: str) -> int:
        """Delete every upload whose key starts with prefix; returns how many."""
