"""The built-in sample profile (Riya Sharma), rebuilt on demand.

Sample sessions use ids that start with "sample-". If a request arrives for one
this server instance has never seen (serverless instances do not share memory),
it is recreated from the fixtures instead of failing with "unknown session".
"""

from __future__ import annotations

import uuid
from typing import cast

from api.db.base import AppDatabase
from api.models import ConfirmedAis, ConfirmedBankStatement, ConfirmedForm16, ConfirmedPayslip, ConfirmedPfPassbook
from llm.reader import read_document
from llm.schemas import (
    AisReaderOutput,
    BankStatementReaderOutput,
    Form16ReaderOutput,
    PayslipReaderOutput,
    PfPassbookReaderOutput,
)

SAMPLE_PREFIX = "sample-"


def new_sample_id() -> str:
    return f"{SAMPLE_PREFIX}{uuid.uuid4()}"


def build_sample_documents() -> dict[str, dict]:
    docs = {
        "payslip": ConfirmedPayslip.prefill_from_reader(cast(PayslipReaderOutput, read_document("payslip", mode="fixture"))),
        "form16": ConfirmedForm16.prefill_from_reader(cast(Form16ReaderOutput, read_document("form16", mode="fixture"))),
        "bank_statement": ConfirmedBankStatement.prefill_from_reader(
            cast(BankStatementReaderOutput, read_document("bank_statement", mode="fixture"))
        ),
        "pf_passbook": ConfirmedPfPassbook.prefill_from_reader(
            cast(PfPassbookReaderOutput, read_document("pf_passbook", mode="fixture"))
        ),
        "ais": ConfirmedAis.prefill_from_reader(cast(AisReaderOutput, read_document("ais", mode="fixture"))),
    }
    return {name: model.model_dump(mode="json") for name, model in docs.items()}


def seed_sample_session(db: AppDatabase, session_id: str) -> dict[str, dict]:
    docs = build_sample_documents()
    db.create_session(session_id)
    for name, fields in docs.items():
        db.save_confirmed_fields(session_id, name, fields)
    return docs
