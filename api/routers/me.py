"""My account: saved documents, history of results, progress since the last visit, and deleting it all.

Everything is keyed by the uid inside the verified sign-in token, so a person can only ever reach their
own data. Saving needs explicit consent (profile.consent); only confirmed values and numbers computed by
our rules engine are stored, never the uploaded files.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth import AuthUser, require_user
from api.confirmed import ConfirmedBody
from api.memory import build_memory
from api.routers.confirm import CONFIRMED_MODELS
from api.routers.tax_advice import tax_picture
from api.users import UserStore, ensure_persistent, get_user_store
from rules_engine.progress import compare_snapshots, progress_summary
from rules_engine.spending import spending_profile

router = APIRouter(prefix="/me", tags=["me"])

CONSENT_VERSION = "2026-11"


def _store() -> UserStore:
    store = get_user_store()
    ensure_persistent(store)
    return store


def _require_consent(store: UserStore, uid: str) -> None:
    p = store.get_profile(uid)
    if not p or not p.get("consent"):
        raise HTTPException(status_code=403, detail={"code": "saving_off", "message": "Saving is switched off for your account. Turn it on to keep your documents and history."})


def _snapshot_view(s: dict) -> dict:
    keep = ("id", "at", "docs_present", "money_found_yearly", "money_found_one_time", "leak_monthly", "tax_now", "cheaper_regime", "savings_rate_percent", "spending_per_month", "top_suggestions")
    return {k: s[k] for k in keep if k in s}


@router.get("")
def get_me(user: AuthUser = Depends(require_user)) -> dict:
    store = _store()
    profile = store.get_profile(user.uid)
    if profile is None:
        profile = {"email": user.email, "created_at": datetime.now(UTC).isoformat(), "consent": False}
        store.save_profile(user.uid, profile)
    docs = store.get_documents(user.uid)
    return {
        "uid": user.uid, "email": user.email,
        "saving_on": bool(profile.get("consent")),
        "documents": {t: d["fields"] for t, d in docs.items()},
        "documents_saved_at": {t: d.get("updated_at") for t, d in docs.items()},
        "snapshots": [_snapshot_view(s) for s in store.list_snapshots(user.uid, 12)],
    }


class ConsentBody(BaseModel):
    save: bool


@router.post("/consent")
def set_consent(body: ConsentBody, user: AuthUser = Depends(require_user)) -> dict:
    store = _store()
    profile = store.get_profile(user.uid) or {"email": user.email, "created_at": datetime.now(UTC).isoformat()}
    profile["consent"] = body.save
    profile["consent_version"] = CONSENT_VERSION
    profile["consent_at"] = datetime.now(UTC).isoformat()
    store.save_profile(user.uid, profile)
    return {"saving_on": body.save}


class DocumentBody(BaseModel):
    fields: dict


@router.put("/documents/{document_type}")
def save_document(document_type: str, body: DocumentBody, user: AuthUser = Depends(require_user)) -> dict:
    store = _store()
    _require_consent(store, user.uid)
    model = CONFIRMED_MODELS.get(document_type)
    if model is None:
        raise HTTPException(status_code=400, detail=f"Unknown document_type: {document_type!r}")
    try:
        clean = model.model_validate(body.fields).model_dump(mode="json")
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=422, detail={"code": "bad_confirmed", "message": "Those values are not valid. Please confirm the document again."}) from None
    store.save_document(user.uid, document_type, clean)
    return {"saved": True, "document_type": document_type}


def _compute_snapshot(docs: dict[str, dict]) -> dict:
    from api.routers.calculate import calculate_leak_fixer, calculate_money_finder
    from agents.tax_knowledge import opportunities

    snap: dict = {"at": datetime.now(UTC).isoformat(), "docs_present": sorted(docs)}
    body = ConfirmedBody(confirmed=docs)
    mf = calculate_money_finder("local-snapshot", body)
    snap["money_found_yearly"] = mf["yearly_total"]
    snap["money_found_one_time"] = mf["one_time_total"]
    if "bank_statement" in docs:
        try:
            snap["leak_monthly"] = calculate_leak_fixer("local-snapshot", body)["monthly_leak_total"]
        except HTTPException:
            pass
        sp = spending_profile(docs["bank_statement"]["transactions"])
        snap["spending_per_month"] = sp["spending_per_month"]
        snap["savings_rate_percent"] = sp["savings_rate_percent"]
    pic = tax_picture(docs)
    if pic:
        snap["tax_now"] = pic["tax_now"]
        snap["cheaper_regime"] = pic["cheaper_regime"]
        snap["top_suggestions"] = [{"id": o["id"], "title": o["title"], "saving": o["saving"]} for o in opportunities(docs)[:4] if o["id"] != "insight"]
    return snap


_COMPARED = ("money_found_yearly", "money_found_one_time", "leak_monthly", "tax_now", "cheaper_regime", "savings_rate_percent", "spending_per_month", "docs_present")


@router.post("/snapshot")
def take_snapshot(user: AuthUser = Depends(require_user)) -> dict:
    """Record today's numbers (computed from the saved documents) so progress can be shown next time."""
    store = _store()
    _require_consent(store, user.uid)
    docs = {t: d["fields"] for t, d in store.get_documents(user.uid).items()}
    if "payslip" not in docs and "form16" not in docs and "bank_statement" not in docs:
        raise HTTPException(status_code=400, detail={"code": "nothing_saved", "message": "Confirm a document first."})
    snap = _compute_snapshot(docs)
    last = store.list_snapshots(user.uid, 1)
    if last and last[0].get("at", "")[:10] == snap["at"][:10] and all(last[0].get(k) == snap.get(k) for k in _COMPARED):
        return {"recorded": False, "snapshot": _snapshot_view(last[0])}  # same day, same numbers
    snap["id"] = store.add_snapshot(user.uid, snap)
    return {"recorded": True, "snapshot": _snapshot_view(snap)}


@router.get("/progress")
def progress(user: AuthUser = Depends(require_user)) -> dict:
    store = _store()
    snaps = store.list_snapshots(user.uid, 2)
    if len(snaps) < 2:
        return {"has_history": False, "changes": [], "summary": "", "latest_at": snaps[0]["at"] if snaps else None, "previous_at": None}
    changes = compare_snapshots(snaps[0], snaps[1])
    return {"has_history": True, "changes": changes, "summary": progress_summary(changes), "latest_at": snaps[0]["at"], "previous_at": snaps[1]["at"]}


@router.delete("")
def delete_everything(user: AuthUser = Depends(require_user)) -> dict:
    """Erase every saved document, snapshot and memory for this account (DPDP: right to erasure)."""
    _store().delete_all(user.uid)
    return {"deleted": True}


def remember_question(user: AuthUser, question: str) -> None:
    """Called by the chat: keep a short note of what was asked, if the person agreed to saving."""
    try:
        store = get_user_store()
        p = store.get_profile(user.uid)
        if p and p.get("consent"):
            store.add_memory(user.uid, {"q": question.strip()[:200], "at": datetime.now(UTC).isoformat()})
    except Exception:  # noqa: BLE001 - memory is a bonus, never break an answer for it
        pass


def memory_for(user: AuthUser | None) -> dict | None:
    if user is None:
        return None
    try:
        return build_memory(get_user_store(), user.uid)
    except Exception:  # noqa: BLE001
        return None
