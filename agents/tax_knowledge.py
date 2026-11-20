"""Knowledge for the CA agents: retrieval over the income-tax and GST law notes, plus the
"opportunities" the rules engine computes from the user's own documents.

This is the RAG layer. For a question we RETRIEVE the relevant law passages (BM25 over
config/rules/tax_corpus.yaml and gst_corpus.yaml) and the person's computed tax opportunities,
and hand both to the model as grounding. The model explains; it never invents a rule or a number.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agents.gst_assistant import Corpus, corpus as gst_corpus
from rules_engine.config import load_rules_config
from rules_engine.spending import spending_profile
from rules_engine.tax_suggestions import build_suggestions

_TAX_PATH = Path(__file__).resolve().parent.parent / "config" / "rules" / "tax_corpus.yaml"
_TAX: Corpus | None = None
_CONFIG = load_rules_config()


def tax_corpus() -> Corpus:
    global _TAX
    if _TAX is None:
        _TAX = Corpus(_TAX_PATH)
    return _TAX


def search_law(query: str, k: int = 3) -> list[dict[str, Any]]:
    """Best law passages for a question across income tax and GST, each with its section and source."""
    wants_gst = "gst" in query.lower()
    # Scores come from two separate corpora, so lean towards the one the question is about.
    hits = [(p, s * (0.7 if wants_gst else 1.0), "income_tax") for p, s in tax_corpus().search(query, k)]
    hits += [(p, s * (1.0 if wants_gst else 0.7), "gst") for p, s in gst_corpus().search(query, k)]
    hits.sort(key=lambda h: -h[1])
    return [
        {"id": p.id, "domain": d, "section": p.section, "title": p.title, "text": p.text, "source_url": p.source_url, "score": round(sc, 2)}
        for p, sc, d in hits[:k]
    ]


def passage(law_id: str) -> dict[str, Any] | None:
    for p in tax_corpus().passages:
        if p.id == law_id:
            return {"id": p.id, "section": p.section, "title": p.title, "text": p.text, "source_url": p.source_url}
    return None


def opportunities(documents: dict[str, dict], metro: bool = False) -> list[dict[str, Any]]:
    """Tax-saving suggestions computed from the confirmed documents, each tied to its law section."""
    out = []
    for s in build_suggestions(documents, _CONFIG, metro=metro):
        law = passage(s.law_id)
        out.append({
            "id": s.id, "title": s.title, "why": s.why, "saving": s.saving, "action": s.action, "caveat": s.caveat,
            "law": {"section": law["section"], "title": law["title"], "excerpt": law["text"], "source_url": law["source_url"]} if law else None,
            "evidence": s.evidence,
        })
    return out


def grounding(confirmed: dict[str, dict], question: str, memory: dict | None = None) -> tuple[str, dict[str, Any]]:
    """Text appended to the model's prompt, and the same facts for the number-provenance check."""
    law = search_law(question, 3)
    opps = opportunities(confirmed)
    parts = []
    if law:
        parts.append("Relevant law notes (cite the section when you rely on one):\n" + "\n".join(f"- {p['section']}: {p['text']}" for p in law))
    if opps:
        parts.append(
            "Tax-saving opportunities already computed from this person's documents (quote these figures, never your own):\n"
            + "\n".join(f"- {o['title']}: {o['why']}" + (f" Saves about ₹{o['saving']:,.0f} a year." if o["saving"] else "") + (f" {o['caveat']}" if o["caveat"] else "") for o in opps)
        )
    profile = None
    bank = confirmed.get("bank_statement")
    if bank and bank.get("transactions"):
        profile = spending_profile(bank["transactions"])
        top = ", ".join(f"{e['label']} ₹{e['monthly_average']:,.0f}/month" for e in profile["categories"][:5])
        parts.append(
            f"Spending profile computed from their bank statement ({profile['months_covered']} months): income about ₹{profile['income_per_month']:,.0f}/month, "
            f"spending ₹{profile['spending_per_month']:,.0f}/month, savings rate {profile['savings_rate_percent']}%. Biggest costs: {top}. "
            + " ".join(f["text"] for f in profile["flags"])
        )
    if memory:
        from api.memory import memory_text

        parts.append("What we remember about this person from earlier visits (use it to personalise, and say when it is from before):\n" + memory_text(memory))
    return "\n\n".join(parts), {"law": law, "opportunities": opps, "spending": profile, "memory": memory}
