import time

import pytest

from api.db.sqlite import SqliteDatabase
from api.storage.local import LocalUploadStorage


def test_local_storage_save_read_delete(tmp_path):
    storage = LocalUploadStorage(str(tmp_path))
    storage.save("doc1.pdf", b"hello world")
    assert storage.read("doc1.pdf") == b"hello world"
    storage.delete("doc1.pdf")
    with pytest.raises(FileNotFoundError):
        storage.read("doc1.pdf")


def test_local_storage_handles_nested_keys(tmp_path):
    # keys look like "{session_id}/{document_type}/{filename}" -- parent
    # dirs must be created on save, and rglob must find them for expiry.
    storage = LocalUploadStorage(str(tmp_path))
    storage.save("session1/payslip/payslip.pdf", b"nested content")
    assert storage.read("session1/payslip/payslip.pdf") == b"nested content"


def test_local_storage_read_missing_key_raises(tmp_path):
    storage = LocalUploadStorage(str(tmp_path))
    with pytest.raises(FileNotFoundError):
        storage.read("nope.pdf")


def test_local_storage_delete_expired(tmp_path):
    storage = LocalUploadStorage(str(tmp_path))
    storage.save("old.pdf", b"old")
    old_path = tmp_path / "old.pdf"
    one_day_ago = time.time() - 48 * 3600
    import os

    os.utime(old_path, (one_day_ago, one_day_ago))
    storage.save("new.pdf", b"new")

    deleted = storage.delete_expired(ttl_hours=24)
    assert deleted == 1
    with pytest.raises(FileNotFoundError):
        storage.read("old.pdf")
    assert storage.read("new.pdf") == b"new"


def test_sqlite_session_lifecycle(tmp_path):
    db = SqliteDatabase(str(tmp_path / "test.db"))
    session_id = db.create_session()
    assert db.session_exists(session_id)
    assert not db.session_exists("not-a-real-session")


def test_sqlite_confirmed_fields_roundtrip(tmp_path):
    db = SqliteDatabase(str(tmp_path / "test.db"))
    session_id = db.create_session()
    assert db.get_confirmed_fields(session_id, "payslip") is None

    fields = {"monthly_gross_salary": 83333, "employee_name": "Riya Sharma"}
    db.save_confirmed_fields(session_id, "payslip", fields)
    assert db.get_confirmed_fields(session_id, "payslip") == fields

    # Overwrite works (user edits a field twice before confirming).
    updated = {**fields, "monthly_gross_salary": 84000}
    db.save_confirmed_fields(session_id, "payslip", updated)
    assert db.get_confirmed_fields(session_id, "payslip") == updated


def test_sqlite_source_trail_roundtrip(tmp_path):
    db = SqliteDatabase(str(tmp_path / "test.db"))
    session_id = db.create_session()

    db.save_source_trail_entry(session_id, "tax_regime_saving", {"rule": "compare_regimes", "inputs": {"gross": 1000000}})
    db.save_source_trail_entry(session_id, "pf_dormant", {"rule": "review_pf_accounts", "inputs": {}})

    assert db.get_source_trail_entry(session_id, "tax_regime_saving")["rule"] == "compare_regimes"
    assert db.get_source_trail_entry(session_id, "not_a_card") is None

    all_entries = db.list_source_trail(session_id)
    assert set(all_entries) == {"tax_regime_saving", "pf_dormant"}
