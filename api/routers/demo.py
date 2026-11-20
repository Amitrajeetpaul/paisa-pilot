""""Try with sample data" button: confirms the Riya Sharma fixtures in one call, so
the demo flow works without anyone touching a real file. Every amount this
unlocks is labeled "Sample data" in the UI.
"""

from __future__ import annotations

from fastapi import APIRouter

from api.db import get_db
from api.sample import new_sample_id, seed_sample_session

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/sample-session")
def create_sample_session() -> dict:
    session_id = new_sample_id()
    confirmed = seed_sample_session(get_db(), session_id)
    return {"session_id": session_id, "sample_data": True, "confirmed": confirmed}
