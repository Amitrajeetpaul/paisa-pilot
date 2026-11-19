"""Upload -> Read. Consent must already exist for the session (brief
principle 5); nothing from these endpoints is trusted until the user
confirms it on the Confirm screen (api/routers/confirm.py) -- these
endpoints only ever return the AI's raw, per-field-confidence guess.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, UploadFile

from api.db import get_db
from api.storage import get_storage
from llm.reader import mime_type_for_filename, read_document
from llm.schemas import READER_OUTPUT_MODELS

router = APIRouter(prefix="/sessions/{session_id}/documents", tags=["documents"])


def _require_session(session_id: str) -> None:
    if not get_db().session_exists(session_id):
        raise HTTPException(status_code=404, detail="Unknown session -- call /consent first")


def _require_document_type(document_type: str) -> None:
    if document_type not in READER_OUTPUT_MODELS:
        raise HTTPException(status_code=400, detail=f"Unknown document_type: {document_type!r}")


@router.post("/{document_type}/upload")
async def upload_document(session_id: str, document_type: str, file: UploadFile) -> dict:
    _require_session(session_id)
    _require_document_type(document_type)
    content = await file.read()
    key = f"{session_id}/{document_type}/{file.filename}"
    get_storage().save(key, content)
    return {"upload_key": key}


@router.post("/{document_type}/read")
def read_uploaded_document(session_id: str, document_type: str, body: dict) -> dict:
    _require_session(session_id)
    _require_document_type(document_type)
    upload_key = body.get("upload_key")
    if not upload_key:
        raise HTTPException(status_code=400, detail="upload_key is required")

    mode = os.environ.get("READER_MODE", "fixture")
    if mode == "fixture":
        result = read_document(document_type, mode="fixture")
    else:
        try:
            content = get_storage().read(upload_key)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        result = read_document(
            document_type,
            file_bytes=content,
            mime_type=mime_type_for_filename(upload_key),
            mode="live",
        )
    return result.model_dump(mode="json")
