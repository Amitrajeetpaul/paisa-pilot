""""Try with sample data" button: runs upload -> read -> confirm against
the Riya Sharma fixtures in one call, so the demo flow in brief section 10
works without anyone touching a real file. Every amount this unlocks must
still be labeled "Sample data" in the UI -- this endpoint doesn't relax
that, it just skips the manual upload/confirm clicks.
"""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter

from api.db import get_db
from api.models import (
    ConfirmedBankStatement,
    ConfirmedForm16,
    ConfirmedPayslip,
    ConfirmedPfPassbook,
)
from llm.reader import read_document
from llm.schemas import (
    BankStatementReaderOutput,
    Form16ReaderOutput,
    PayslipReaderOutput,
    PfPassbookReaderOutput,
)

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/sample-session")
def create_sample_session() -> dict:
    db = get_db()
    session_id = db.create_session()

    payslip = ConfirmedPayslip.prefill_from_reader(cast(PayslipReaderOutput, read_document("payslip", mode="fixture")))
    form16 = ConfirmedForm16.prefill_from_reader(cast(Form16ReaderOutput, read_document("form16", mode="fixture")))
    bank_statement = ConfirmedBankStatement.prefill_from_reader(
        cast(BankStatementReaderOutput, read_document("bank_statement", mode="fixture"))
    )
    pf_passbook = ConfirmedPfPassbook.prefill_from_reader(
        cast(PfPassbookReaderOutput, read_document("pf_passbook", mode="fixture"))
    )

    db.save_confirmed_fields(session_id, "payslip", payslip.model_dump(mode="json"))
    db.save_confirmed_fields(session_id, "form16", form16.model_dump(mode="json"))
    db.save_confirmed_fields(session_id, "bank_statement", bank_statement.model_dump(mode="json"))
    db.save_confirmed_fields(session_id, "pf_passbook", pf_passbook.model_dump(mode="json"))

    return {
        "session_id": session_id,
        "sample_data": True,
        "confirmed": {
            "payslip": payslip.model_dump(mode="json"),
            "form16": form16.model_dump(mode="json"),
            "bank_statement": bank_statement.model_dump(mode="json"),
            "pf_passbook": pf_passbook.model_dump(mode="json"),
        },
    }
