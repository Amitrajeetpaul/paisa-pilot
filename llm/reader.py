"""Document reader dispatcher: Gemini 3.8 Flash in "live" mode, a recorded
fixture in "fixture" mode (the default -- see llm/fixtures/build_fixtures.py).

READER_MODE=fixture is what every test and local-dev run uses, per the
brief's "a stub reader must exist so tests never call the live API" rule.
Only READER_MODE=live touches the network, and only once an upload actually
reaches api/ in a later milestone.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from google.genai import types
from pydantic import BaseModel

from llm.client import generate_structured, reader_model
from llm.prompts import load_reader_prompt
from llm.schemas import READER_OUTPUT_MODELS

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"

FIXTURE_FILES = {
    "payslip": "payslip_riya_sharma_apr2026.json",
    "form16": "form16_riya_sharma_fy2025-26.json",
    "bank_statement": "bank_statement_riya_sharma_q3fy26.json",
    "pf_passbook": "pf_passbook_riya_sharma.json",
}

_PDF_SUFFIXES = (".pdf",)
_IMAGE_MIME_BY_SUFFIX = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}


def _mime_type_for(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in _PDF_SUFFIXES:
        return "application/pdf"
    return _IMAGE_MIME_BY_SUFFIX.get(suffix, "application/octet-stream")


def _read_fixture(document_type: str, model_cls: type[BaseModel]) -> BaseModel:
    fixture_path = FIXTURE_DIR / FIXTURE_FILES[document_type]
    data = json.loads(fixture_path.read_text())
    return model_cls.model_validate(data)


def _read_live(document_type: str, source: Path, model_cls: type[BaseModel]) -> BaseModel:
    system_prompt = load_reader_prompt(document_type)
    file_part = types.Part.from_bytes(data=source.read_bytes(), mime_type=_mime_type_for(source))
    return generate_structured(
        model=reader_model(),
        system_instruction=system_prompt,
        parts=[file_part],
        response_schema=model_cls,
    )


def read_document(document_type: str, source: Path | str | None = None, mode: str | None = None) -> BaseModel:
    """source is required (and must exist) in "live" mode; ignored in
    "fixture" mode, which always returns the one recorded fixture for that
    document type regardless of what was uploaded."""
    if document_type not in READER_OUTPUT_MODELS:
        raise ValueError(f"Unknown document_type: {document_type!r}")
    resolved_mode = mode or os.environ.get("READER_MODE", "fixture")
    model_cls = READER_OUTPUT_MODELS[document_type]

    if resolved_mode == "fixture":
        return _read_fixture(document_type, model_cls)
    if resolved_mode == "live":
        if source is None:
            raise ValueError("source is required in live mode")
        return _read_live(document_type, Path(source), model_cls)
    raise ValueError(f"Unknown reader mode: {resolved_mode!r} (expected 'fixture' or 'live')")
