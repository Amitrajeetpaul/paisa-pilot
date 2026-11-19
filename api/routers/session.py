"""Session lifecycle: let a person delete everything we hold about them,
now, instead of waiting for the automatic 24-hour expiry (DPDP: right to erasure)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.db import get_db
from api.storage import get_storage

router = APIRouter(prefix="/sessions", tags=["session"])


@router.delete("/{session_id}")
def delete_my_data(session_id: str) -> dict:
    db = get_db()
    if not db.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Unknown session")
    uploads_deleted = get_storage().delete_prefix(f"{session_id}/")
    db.delete_session(session_id)
    return {"deleted": True, "uploads_deleted": uploads_deleted}
