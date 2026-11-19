"""SQLite implementation of AppDatabase. Dev/CI default -- no cloud account.

Mirrors Firestore's document shape on purpose (one JSON blob per confirmed
document, one per source-trail card) so switching DB_BACKEND=firestore
later doesn't change how callers use this interface.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

from api.db.base import AppDatabase

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS confirmed_fields (
    session_id TEXT NOT NULL,
    document_type TEXT NOT NULL,
    fields_json TEXT NOT NULL,
    PRIMARY KEY (session_id, document_type)
);
CREATE TABLE IF NOT EXISTS source_trail (
    session_id TEXT NOT NULL,
    card_id TEXT NOT NULL,
    entry_json TEXT NOT NULL,
    PRIMARY KEY (session_id, card_id)
);
"""


class SqliteDatabase(AppDatabase):
    def __init__(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        self._conn.execute("INSERT INTO sessions (id) VALUES (?)", (session_id,))
        self._conn.commit()
        return session_id

    def session_exists(self, session_id: str) -> bool:
        row = self._conn.execute("SELECT 1 FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return row is not None

    def save_confirmed_fields(self, session_id: str, document_type: str, fields: dict) -> None:
        self._conn.execute(
            "INSERT INTO confirmed_fields (session_id, document_type, fields_json) VALUES (?, ?, ?) "
            "ON CONFLICT (session_id, document_type) DO UPDATE SET fields_json = excluded.fields_json",
            (session_id, document_type, json.dumps(fields)),
        )
        self._conn.commit()

    def get_confirmed_fields(self, session_id: str, document_type: str) -> dict | None:
        row = self._conn.execute(
            "SELECT fields_json FROM confirmed_fields WHERE session_id = ? AND document_type = ?",
            (session_id, document_type),
        ).fetchone()
        return json.loads(row[0]) if row else None

    def save_source_trail_entry(self, session_id: str, card_id: str, entry: dict) -> None:
        self._conn.execute(
            "INSERT INTO source_trail (session_id, card_id, entry_json) VALUES (?, ?, ?) "
            "ON CONFLICT (session_id, card_id) DO UPDATE SET entry_json = excluded.entry_json",
            (session_id, card_id, json.dumps(entry)),
        )
        self._conn.commit()

    def get_source_trail_entry(self, session_id: str, card_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT entry_json FROM source_trail WHERE session_id = ? AND card_id = ?",
            (session_id, card_id),
        ).fetchone()
        return json.loads(row[0]) if row else None

    def list_source_trail(self, session_id: str) -> dict[str, dict]:
        rows = self._conn.execute(
            "SELECT card_id, entry_json FROM source_trail WHERE session_id = ?",
            (session_id,),
        ).fetchall()
        return {card_id: json.loads(entry_json) for card_id, entry_json in rows}
