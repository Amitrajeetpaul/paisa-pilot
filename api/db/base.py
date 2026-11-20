"""Confirmed-fields + source-trail storage interface. Two implementations:
sqlite.py (dev/CI, zero cloud account) and firestore.py (deployment).
Swapped by DB_BACKEND -- see api/settings.py, DECISIONS.md (Firestore is
the default once deployed; SQLite mirrors its document shape for local dev).

Only CONFIRMED fields and computed results ever reach here -- raw AI
extractions before the user confirms them never get this far, per the
brief's "nothing runs on unchecked data" rule.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class AppDatabase(ABC):
    @abstractmethod
    def create_session(self, session_id: str | None = None) -> str:
        """Returns a new session_id (or creates the one given; creating an existing id is a no-op). No auth system in this demo -- see
        LIMITATIONS.md; a session_id is a bearer capability, not a login."""

    @abstractmethod
    def session_exists(self, session_id: str) -> bool: ...

    @abstractmethod
    def save_confirmed_fields(self, session_id: str, document_type: str, fields: dict) -> None: ...

    @abstractmethod
    def get_confirmed_fields(self, session_id: str, document_type: str) -> dict | None: ...

    @abstractmethod
    def save_source_trail_entry(self, session_id: str, card_id: str, entry: dict) -> None: ...

    @abstractmethod
    def get_source_trail_entry(self, session_id: str, card_id: str) -> dict | None: ...

    @abstractmethod
    def list_source_trail(self, session_id: str) -> dict[str, dict]: ...

    @abstractmethod
    def delete_session(self, session_id: str) -> None:
        """Permanently remove the session and everything saved under it."""

    @abstractmethod
    def save_record(self, kind: str, record: dict, key: str | None = None) -> None:
        """Append a small non-session record ("waitlist", "events", "feedback").
        With a key, saving the same key again replaces it (used to dedupe emails)."""

    def _rebuild_if_sample(self, session_id: str) -> bool:
        """A sample session this instance has not seen is recreated from the fixtures
        (serverless instances do not share memory). Real sessions are never recreated."""
        from api.confirmed import LOCAL_PREFIX
        from api.sample import SAMPLE_PREFIX, seed_sample_session

        if session_id.startswith(LOCAL_PREFIX):
            return True  # stateless session: the browser holds the data
        if session_id.startswith(SAMPLE_PREFIX):
            seed_sample_session(self, session_id)
            return True
        return False
