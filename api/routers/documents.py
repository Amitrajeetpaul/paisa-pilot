"""Upload -> Read. Consent must already exist for the session (brief
principle 5); nothing from these endpoints is trusted until the user
confirms it on the Confirm screen (api/routers/confirm.py) -- these
endpoints only ever return the AI's raw, per-field-confidence guess.
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, HTTPException, UploadFile

from api.db import get_db
from api.storage import get_storage
from llm.client import gemini_configured
from llm.reader import mime_type_for_filename, read_document
from llm.schemas import READER_OUTPUT_MODELS

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
ALLOWED_SUFFIXES = (".pdf", ".jpg", ".jpeg", ".png")

router = APIRouter(prefix="/sessions/{session_id}/documents", tags=["documents"])


def _require_session(session_id: str) -> None:
    if not get_db().session_exists(session_id):
        raise HTTPException(status_code=404, detail="Unknown session -- call /consent first")


def _require_document_type(document_type: str) -> None:
    if document_type not in READER_OUTPUT_MODELS:
        raise HTTPException(status_code=400, detail=f"Unknown document_type: {document_type!r}")


def _check_upload(filename_raw: str | None, content: bytes) -> str:
    """Reject files we cannot or should not read, with a message a person can act on."""
    filename = (filename_raw or "").lower()
    if not filename.endswith(ALLOWED_SUFFIXES):
        raise HTTPException(
            status_code=422,
            detail={"code": "unsupported_file", "message": "Please upload a PDF or a photo (JPG or PNG)."},
        )
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail={"code": "too_large", "message": "That file is too large. Please upload one under 15 MB."},
        )
    if filename.endswith(".pdf") and b"/Encrypt" in content:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "password_protected",
                "message": "This PDF is password protected, so we can't read it. Remove the password "
                "(open it, then save or print it as a new PDF) and upload it again.",
            },
        )
    return filename


def _read_bytes(document_type: str, content: bytes, filename: str) -> dict:
    """Read one document. Fixture mode (tests, local dev) returns the sample; live mode asks Gemini."""
    if os.environ.get("READER_MODE", "fixture") == "fixture":
        return read_document(document_type, mode="fixture").model_dump(mode="json")
    if not gemini_configured():
        raise HTTPException(
            status_code=503,
            detail={
                "code": "reader_unavailable",
                "message": "Reading uploaded documents isn't switched on in this demo yet. "
                "Try the sample profile to see the whole app.",
            },
        )
    try:
        result = read_document(document_type, file_bytes=content, mime_type=mime_type_for_filename(filename), mode="live")
    except Exception as exc:
        logger.exception("Document read failed for %s", document_type)
        raise HTTPException(
            status_code=502,
            detail={
                "code": "read_failed",
                "message": "We couldn't read this document right now. Please try again in a moment, "
                "or upload a clearer copy.",
            },
        ) from exc
    return result.model_dump(mode="json")


@router.post("/{document_type}/upload")
async def upload_document(session_id: str, document_type: str, file: UploadFile) -> dict:
    _require_session(session_id)
    _require_document_type(document_type)
    content = await file.read()
    _check_upload(file.filename, content)
    key = f"{session_id}/{document_type}/{file.filename}"
    get_storage().save(key, content)
    return {"upload_key": key}


@router.post("/{document_type}/extract")
def extract_document(session_id: str, document_type: str, file: UploadFile) -> dict:
    """Upload and read in ONE request. The file is read in memory and never stored, so it works
    on hosts where requests land on different servers, and nothing needs deleting afterwards."""
    _require_session(session_id)
    _require_document_type(document_type)
    content = file.file.read()
    filename = _check_upload(file.filename, content)
    return _read_bytes(document_type, content, filename)


@router.post("/{document_type}/read")
def read_uploaded_document(session_id: str, document_type: str, body: dict) -> dict:
    _require_session(session_id)
    _require_document_type(document_type)
    upload_key = body.get("upload_key")
    if not upload_key:
        raise HTTPException(status_code=400, detail="upload_key is required")
    if os.environ.get("READER_MODE", "fixture") == "fixture":
        return _read_bytes(document_type, b"", upload_key)
    if not gemini_configured():
        return _read_bytes(document_type, b"", upload_key)  # raises the plain "not switched on" message
    try:
        content = get_storage().read(upload_key)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _read_bytes(document_type, content, upload_key)
