"""Presentation helpers for agent output: plain, readable text with no markdown
symbols and no raw bank strings. The UI shows this text as-is."""

from __future__ import annotations

import re


def pretty_merchant(raw: str) -> str:
    """'UPI AUTOPAY-FITZONE GYM-fitzone@upi' -> 'Fitzone Gym'."""
    s = re.sub(r"[-\s]*[a-z0-9._]+@[a-z0-9._\-]+$", "", raw, flags=re.I)
    s = re.sub(r"^(UPI AUTOPAY|UPI|NEFT|IMPS|RTGS|ACH|NACH|POS)[-\s]+", "", s, flags=re.I)
    s = re.sub(r"-[A-Z]{2}\d{4,}$", "", s, flags=re.I)
    s = re.sub(r"[-_]+", " ", s).strip()
    return re.sub(r"\bEmi\b", "EMI", s.title()) or raw


_BANK_STRING = re.compile(
    r"[`'\"(]*\b(?:UPI AUTOPAY|UPI|NEFT|IMPS|RTGS|ACH|NACH)[-\s][A-Za-z0-9 .&_\-]+?(?:@[a-z0-9._\-]+|-[A-Z]{2}\d{4,})[`'\")]*"
)


def clean_answer(text: str) -> str:
    """Strip markdown and bank-string noise a model may add, and put every bullet
    on its own line. Never changes a number."""
    t = text.replace("\r", "")
    # "Cloudnotes Premium (`UPI-CLOUDNOTES PREMIUM-cloudnotes@upi`)" -> "Cloudnotes Premium"
    t = re.sub(r"\s*\(\s*`?(?:UPI AUTOPAY|UPI|NEFT|IMPS|RTGS|ACH|NACH)[-\s][^)]*\)", "", t)
    t = _BANK_STRING.sub(lambda m: pretty_merchant(m.group(0).strip("`'\"() ")), t)
    t = re.sub(r"^\s*#{1,6}\s*", "", t, flags=re.M)  # headings
    t = re.sub(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$", "", t, flags=re.M)  # rules
    t = re.sub(r"(?m)^\s*[-*+]\s+", "• ", t)  # list markers at line start
    t = re.sub(r"\s+[*]\s+(?=\S)", "\n• ", t)  # " * " bullets run together on one line
    t = t.replace("**", "").replace("__", "").replace("`", "")
    t = re.sub(r"(?<![\w*])\*(?!\s)([^*\n]+?)\*(?![\w*])", r"\1", t)  # *italic*
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()
