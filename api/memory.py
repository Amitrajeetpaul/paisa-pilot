"""What we remember about a signed-in person, handed to the agents as context: how their numbers moved
and what they asked before. Built from the per-user store; nothing here is invented."""

from __future__ import annotations

from api.users import UserStore
from rules_engine.progress import compare_snapshots, inr, progress_summary


def build_memory(store: UserStore, uid: str) -> dict | None:
    profile = store.get_profile(uid)
    if not profile or not profile.get("consent"):
        return None
    snaps = store.list_snapshots(uid, 3)
    questions = store.list_memory(uid, 6)
    if not snaps and not questions:
        return None
    changes = compare_snapshots(snaps[0], snaps[1]) if len(snaps) >= 2 else []
    return {"snapshots": snaps, "recent_questions": questions, "changes": changes, "progress_text": progress_summary(changes) if len(snaps) >= 2 else ""}


def memory_text(memory: dict | None) -> str:
    """A short block for the model's prompt."""
    if not memory:
        return ""
    parts = []
    snaps = memory.get("snapshots") or []
    if snaps:
        s = snaps[0]
        parts.append(
            "What we saved from their last visit"
            + (f" ({s.get('at', '')[:10]})" if s.get("at") else "")
            + f": yearly money found {inr(s.get('money_found_yearly') or 0)}, money leaking {inr(s.get('leak_monthly') or 0)} a month"
            + (f", tax about {inr(s['tax_now'])} a year ({s.get('cheaper_regime')} regime cheaper)" if s.get("tax_now") is not None else "")
            + "."
        )
    if memory.get("changes"):
        parts.append("Change since the visit before: " + " ".join(c["text"] for c in memory["changes"]))
    qs = [q["q"] for q in (memory.get("recent_questions") or []) if q.get("q")]
    if qs:
        parts.append("Things they asked before: " + "; ".join(qs[:5]) + ".")
    return "\n".join(parts)
