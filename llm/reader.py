"""Document reader dispatcher: Gemini 3.8 Flash in "live" mode, a recorded
fixture in "fixture" mode (the default -- see llm/fixtures/build_fixtures.py).

READER_MODE=fixture is what every test and local-dev run uses, per the
brief's "a stub reader must exist so tests never call the live API" rule.
Only READER_MODE=live touches the network, once an upload reaches api/.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from google.genai import types
from pydantic import BaseModel

from llm.client import generate_structured, reader_model
from llm.consistency import apply_consistency_checks
from llm.prompts import load_reader_prompt
from llm.schemas import READER_OUTPUT_MODELS

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"

# Photo sharpening is OFF by default. In a controlled test (3 runs per photo) it made
# blurry digits worse, not better, and it must never be paired with a prompt that asks
# the model to "reconstruct" digits: that yields confident, self-consistent, WRONG numbers
# that the arithmetic cross-check (llm/consistency.py) cannot detect. Set ENHANCE_PHOTOS=1
# to experiment.
def _enhance_enabled() -> bool:
    return os.environ.get("ENHANCE_PHOTOS", "0") == "1"


FIXTURE_FILES = {
    "payslip": "payslip_riya_sharma_apr2026.json",
    "form16": "form16_riya_sharma_fy2025-26.json",
    "bank_statement": "bank_statement_riya_sharma_q3fy26.json",
    "pf_passbook": "pf_passbook_riya_sharma.json",
    "ais": "ais_riya_sharma_fy2025-26.json",
}

_PDF_SUFFIXES = (".pdf",)
_IMAGE_MIME_BY_SUFFIX = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}


def mime_type_for_filename(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in _PDF_SUFFIXES:
        return "application/pdf"
    return _IMAGE_MIME_BY_SUFFIX.get(suffix, "application/octet-stream")


def _read_fixture(document_type: str, model_cls: type[BaseModel]) -> BaseModel:
    fixture_path = FIXTURE_DIR / FIXTURE_FILES[document_type]
    data = json.loads(fixture_path.read_text())
    return model_cls.model_validate(data)


def _read_live(document_type: str, file_bytes: bytes, mime_type: str, model_cls: type[BaseModel]) -> BaseModel:
    if _enhance_enabled():
        from llm.image_enhancer import enhance_document_image  # needs Pillow; only when the flag is on

        enhanced_bytes, was_enhanced = enhance_document_image(file_bytes, mime_type or "")
    else:
        enhanced_bytes, was_enhanced = file_bytes, False
    active_mime = "image/jpeg" if was_enhanced else (mime_type or "application/octet-stream")
    system_prompt = load_reader_prompt(document_type)
    file_part = types.Part.from_bytes(data=enhanced_bytes, mime_type=active_mime)
    result = generate_structured(
        model=reader_model(),
        system_instruction=system_prompt,
        parts=[file_part],
        response_schema=model_cls,
    )
    # Never trust a read blindly: flag anything whose arithmetic does not add up.
    return apply_consistency_checks(document_type, result)


def read_document(
    document_type: str,
    *,
    file_bytes: bytes | None = None,
    mime_type: str | None = None,
    mode: str | None = None,
) -> BaseModel:
    """file_bytes/mime_type are required in "live" mode; ignored in
    "fixture" mode (the default), which always returns the one recorded
    fixture for that document type regardless of what was uploaded."""
    if document_type not in READER_OUTPUT_MODELS:
        raise ValueError(f"Unknown document_type: {document_type!r}")
    resolved_mode = mode or os.environ.get("READER_MODE", "fixture")
    model_cls = READER_OUTPUT_MODELS[document_type]

    if resolved_mode == "fixture":
        return _read_fixture(document_type, model_cls)
    if resolved_mode == "live":
        if file_bytes is None or mime_type is None:
            raise ValueError("file_bytes and mime_type are required in live mode")
        return _read_live(document_type, file_bytes, mime_type, model_cls)
    raise ValueError(f"Unknown reader mode: {resolved_mode!r} (expected 'fixture' or 'live')")
