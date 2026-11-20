"""Per-user storage for people who sign in: their saved confirmed documents, a history of results,
and a short memory of what they asked. Only values the person confirmed (never the uploaded files)
and numbers our rules engine computed are kept here.

Firestore layout: users/{uid} with subcollections documents/{type}, snapshots/{id}, memory/{id}.
Unlike anonymous sessions these do not expire; the person can delete everything at any time.
A process-memory store backs local development and tests; it is refused in deployment (see ensure_persistent).
"""

from __future__ import annotations

import os
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from functools import lru_cache

from fastapi import HTTPException

_MAX_SNAPSHOTS = 60
_MAX_MEMORY = 80


def _now() -> str:
    return datetime.now(UTC).isoformat()


class UserStore(ABC):
    persistent: bool = False

    @abstractmethod
    def get_profile(self, uid: str) -> dict | None: ...

    @abstractmethod
    def save_profile(self, uid: str, profile: dict) -> None: ...

    @abstractmethod
    def save_document(self, uid: str, document_type: str, fields: dict) -> None: ...

    @abstractmethod
    def get_documents(self, uid: str) -> dict[str, dict]: ...

    @abstractmethod
    def add_snapshot(self, uid: str, snapshot: dict) -> str: ...

    @abstractmethod
    def list_snapshots(self, uid: str, limit: int = 20) -> list[dict]:
        """Newest first."""

    @abstractmethod
    def add_memory(self, uid: str, entry: dict) -> None: ...

    @abstractmethod
    def list_memory(self, uid: str, limit: int = 10) -> list[dict]:
        """Newest first."""

    @abstractmethod
    def delete_all(self, uid: str) -> None: ...


class MemoryUserStore(UserStore):
    """Dev/test only: lost when the process restarts."""

    def __init__(self) -> None:
        self._d: dict[str, dict] = {}

    def _u(self, uid: str) -> dict:
        return self._d.setdefault(uid, {"profile": None, "documents": {}, "snapshots": [], "memory": []})

    def get_profile(self, uid: str) -> dict | None:
        return self._u(uid)["profile"]

    def save_profile(self, uid: str, profile: dict) -> None:
        self._u(uid)["profile"] = dict(profile)

    def save_document(self, uid: str, document_type: str, fields: dict) -> None:
        self._u(uid)["documents"][document_type] = {"fields": dict(fields), "updated_at": _now()}

    def get_documents(self, uid: str) -> dict[str, dict]:
        return dict(self._u(uid)["documents"])

    def add_snapshot(self, uid: str, snapshot: dict) -> str:
        sid = uuid.uuid4().hex
        snaps = self._u(uid)["snapshots"]
        snaps.append({**snapshot, "id": sid})
        del snaps[:-_MAX_SNAPSHOTS]
        return sid

    def list_snapshots(self, uid: str, limit: int = 20) -> list[dict]:
        return list(reversed(self._u(uid)["snapshots"]))[:limit]

    def add_memory(self, uid: str, entry: dict) -> None:
        mem = self._u(uid)["memory"]
        mem.append(dict(entry))
        del mem[:-_MAX_MEMORY]

    def list_memory(self, uid: str, limit: int = 10) -> list[dict]:
        return list(reversed(self._u(uid)["memory"]))[:limit]

    def delete_all(self, uid: str) -> None:
        self._d.pop(uid, None)


class FirestoreUserStore(UserStore):
    persistent = True

    def __init__(self, project: str) -> None:
        from google.cloud import firestore

        self._c = firestore.Client(project=project)
        self._fs = firestore

    def _ref(self, uid: str):
        return self._c.collection("users").document(uid)

    def get_profile(self, uid: str) -> dict | None:
        snap = self._ref(uid).get()
        return snap.to_dict() if snap.exists else None

    def save_profile(self, uid: str, profile: dict) -> None:
        self._ref(uid).set(profile)

    def save_document(self, uid: str, document_type: str, fields: dict) -> None:
        self._ref(uid).collection("documents").document(document_type).set({"fields": fields, "updated_at": _now()})

    def get_documents(self, uid: str) -> dict[str, dict]:
        return {d.id: d.to_dict() for d in self._ref(uid).collection("documents").stream()}

    def add_snapshot(self, uid: str, snapshot: dict) -> str:
        ref = self._ref(uid).collection("snapshots").document()
        ref.set(snapshot)
        return ref.id

    def list_snapshots(self, uid: str, limit: int = 20) -> list[dict]:
        q = self._ref(uid).collection("snapshots").order_by("at", direction=self._fs.Query.DESCENDING).limit(limit)
        return [{**d.to_dict(), "id": d.id} for d in q.stream()]

    def add_memory(self, uid: str, entry: dict) -> None:
        self._ref(uid).collection("memory").document().set(entry)

    def list_memory(self, uid: str, limit: int = 10) -> list[dict]:
        q = self._ref(uid).collection("memory").order_by("at", direction=self._fs.Query.DESCENDING).limit(limit)
        return [d.to_dict() for d in q.stream()]

    def delete_all(self, uid: str) -> None:
        ref = self._ref(uid)
        for sub in ("documents", "snapshots", "memory"):
            for d in ref.collection(sub).stream():
                d.reference.delete()
        ref.delete()


@lru_cache(maxsize=1)
def get_user_store() -> UserStore:
    from api.settings import get_settings

    s = get_settings()
    if s.db_backend == "firestore" and s.firestore_project:
        return FirestoreUserStore(s.firestore_project)
    return MemoryUserStore()


def ensure_persistent(store: UserStore) -> None:
    """Accounts must never silently lose data: a non-persistent store is allowed only on purpose (dev/tests)."""
    if not store.persistent and os.environ.get("ACCOUNTS_ALLOW_MEMORY", "0") != "1":
        raise HTTPException(
            status_code=503,
            detail={"code": "accounts_unavailable", "message": "Saving to an account is only available on our main server. Please try again there."},
        )
