"""Firestore implementation of AppDatabase. Not exercised by the automated
test suite (no GCP credentials in CI) -- see LIMITATIONS.md.

Collection layout: sessions/{session_id}, with confirmed_fields and
source_trail as subcollections keyed by document_type / card_id -- this is
exactly the SQLite tables' shape, by design (see sqlite.py's docstring).

google-cloud-firestore is imported lazily so importing this module never
requires it unless DB_BACKEND=firestore.
"""

from __future__ import annotations

import uuid

from api.db.base import AppDatabase


class FirestoreDatabase(AppDatabase):
    def __init__(self, project: str) -> None:
        from google.cloud import firestore  # lazy import, see module docstring

        self._client = firestore.Client(project=project)

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        self._client.collection("sessions").document(session_id).set({"created_at": _utc_now_iso()})
        return session_id

    def session_exists(self, session_id: str) -> bool:
        return self._client.collection("sessions").document(session_id).get().exists

    def save_confirmed_fields(self, session_id: str, document_type: str, fields: dict) -> None:
        (
            self._client.collection("sessions")
            .document(session_id)
            .collection("confirmed_fields")
            .document(document_type)
            .set(fields)
        )

    def get_confirmed_fields(self, session_id: str, document_type: str) -> dict | None:
        snap = (
            self._client.collection("sessions")
            .document(session_id)
            .collection("confirmed_fields")
            .document(document_type)
            .get()
        )
        return snap.to_dict() if snap.exists else None

    def save_source_trail_entry(self, session_id: str, card_id: str, entry: dict) -> None:
        (
            self._client.collection("sessions")
            .document(session_id)
            .collection("source_trail")
            .document(card_id)
            .set(entry)
        )

    def get_source_trail_entry(self, session_id: str, card_id: str) -> dict | None:
        snap = (
            self._client.collection("sessions")
            .document(session_id)
            .collection("source_trail")
            .document(card_id)
            .get()
        )
        return snap.to_dict() if snap.exists else None

    def list_source_trail(self, session_id: str) -> dict[str, dict]:
        docs = self._client.collection("sessions").document(session_id).collection("source_trail").stream()
        return {doc.id: doc.to_dict() for doc in docs}


def _utc_now_iso() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()
