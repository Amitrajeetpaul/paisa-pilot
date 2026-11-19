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
    def create_session(self) -> str:
        """Returns a new session_id. No auth system in this demo -- see
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
