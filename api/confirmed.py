"""Where a request's confirmed documents come from.

Two modes, one code path:
  * stored sessions (local dev, Cloud Run): the confirmed values live in the database;
  * stateless sessions (serverless hosts, ids that start with "local-"): the browser holds
    them and sends them with each request, so no server-side memory is needed.
A "confirmed" payload sent by the browser is validated against the same models the
Confirm screen uses, so a tampered or malformed payload is rejected, never trusted.
"""

from __future__ import annotations

from fastapi import HTTPException
from pydantic import BaseModel, ValidationError

from api.db import get_db
from api.routers.confirm import CONFIRMED_MODELS

LOCAL_PREFIX = "local-"
DOCUMENT_TYPES = ["payslip", "form16", "bank_statement", "pf_passbook", "ais"]


class ConfirmedBody(BaseModel):
    confirmed: dict[str, dict] | None = None


def is_local(session_id: str) -> bool:
    return session_id.startswith(LOCAL_PREFIX)


def load_confirmed(session_id: str, override: dict[str, dict] | None) -> dict[str, dict]:
    if override:
        out: dict[str, dict] = {}
        for doc_type, data in override.items():
            model = CONFIRMED_MODELS.get(doc_type)
            if model is None:
                continue
            try:
                out[doc_type] = model.model_validate(data).model_dump(mode="json")
            except ValidationError as exc:
                raise HTTPException(
                    status_code=422,
                    detail={"code": "bad_confirmed", "message": f"The saved {doc_type} values are not valid. Please confirm that document again."},
                ) from exc
        return out
    db = get_db()
    return {t: f for t in DOCUMENT_TYPES if (f := db.get_confirmed_fields(session_id, t)) is not None}
