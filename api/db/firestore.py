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
        self._client.collection("sessions").document(session_id).set({"created_at": _utc_now_iso(), "expire_at": _expiry()})
        return session_id

    def session_exists(self, session_id: str) -> bool:
        return self._client.collection("sessions").document(session_id).get().exists

    def save_confirmed_fields(self, session_id: str, document_type: str, fields: dict) -> None:
        (
            self._client.collection("sessions")
            .document(session_id)
            .collection("confirmed_fields")
            .document(document_type)
            .set({**fields, "expire_at": _expiry()})
        )

    def get_confirmed_fields(self, session_id: str, document_type: str) -> dict | None:
        snap = (
            self._client.collection("sessions")
            .document(session_id)
            .collection("confirmed_fields")
            .document(document_type)
            .get()
        )
        if not snap.exists:
            return None
        data = snap.to_dict() or {}
        data.pop("expire_at", None)  # storage detail, not part of the document
        return data

    def save_source_trail_entry(self, session_id: str, card_id: str, entry: dict) -> None:
        (
            self._client.collection("sessions")
            .document(session_id)
            .collection("source_trail")
            .document(card_id)
            .set({**entry, "expire_at": _expiry()})
        )

    def get_source_trail_entry(self, session_id: str, card_id: str) -> dict | None:
        snap = (
            self._client.collection("sessions")
            .document(session_id)
            .collection("source_trail")
            .document(card_id)
            .get()
        )
        if not snap.exists:
            return None
        data = snap.to_dict() or {}
        data.pop("expire_at", None)
        return data

    def list_source_trail(self, session_id: str) -> dict[str, dict]:
        docs = self._client.collection("sessions").document(session_id).collection("source_trail").stream()
        return {doc.id: {k: v for k, v in (doc.to_dict() or {}).items() if k != "expire_at"} for doc in docs}


    def delete_session(self, session_id: str) -> None:
        session_ref = self._client.collection("sessions").document(session_id)
        for sub in ("confirmed_fields", "source_trail"):
            for doc in session_ref.collection(sub).stream():
                doc.reference.delete()
        session_ref.delete()


    def save_record(self, kind: str, record: dict, key: str | None = None) -> None:
        coll = self._client.collection(kind)
        doc = coll.document(key) if key else coll.document()
        doc.set({**record, "created_at": _utc_now_iso()})


def _expiry():
    """Firestore TTL policies on sessions, confirmed_fields and source_trail
    delete a document once this time passes (see infra/deploy.md)."""
    import os
    from datetime import UTC, datetime, timedelta

    days = int(os.environ.get("SESSION_TTL_DAYS", "7"))
    return datetime.now(UTC) + timedelta(days=days)


def _utc_now_iso() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()
