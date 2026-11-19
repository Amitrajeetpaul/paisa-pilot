"""Round-trips every ai_studio/test_cases/*.jsonl expected_output through
the matching Pydantic model and back, then validates the result against the
locked JSON Schema file. This is the drift check: if llm/schemas.py and
ai_studio/schema/*.json ever disagree, this fails.
"""

import json
from pathlib import Path

import jsonschema
import pytest

from llm.schemas import READER_OUTPUT_MODELS

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMA_DIR = REPO_ROOT / "ai_studio" / "schema"
TEST_CASES_DIR = REPO_ROOT / "ai_studio" / "test_cases"

SUITES = [
    ("payslip", "payslip_schema.json", "payslip_test_cases.jsonl"),
    ("form16", "form16_schema.json", "form16_test_cases.jsonl"),
    ("bank_statement", "bank_statement_schema.json", "bank_statement_test_cases.jsonl"),
    ("pf_passbook", "pf_passbook_schema.json", "pf_passbook_test_cases.jsonl"),
]


def _load_cases(filename: str) -> list[dict]:
    lines = (TEST_CASES_DIR / filename).read_text().splitlines()
    return [json.loads(line) for line in lines if line.strip()]


@pytest.mark.parametrize("doc_type,schema_file,cases_file", SUITES)
def test_every_case_round_trips_through_pydantic_and_back(doc_type, schema_file, cases_file):
    model_cls = READER_OUTPUT_MODELS[doc_type]
    schema = json.loads((SCHEMA_DIR / schema_file).read_text())
    cases = _load_cases(cases_file)
    assert len(cases) >= 10

    for case in cases:
        parsed = model_cls.model_validate(case["expected_output"])
        dumped = parsed.model_dump(mode="json")
        jsonschema.validate(dumped, schema)
