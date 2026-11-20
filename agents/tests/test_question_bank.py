"""The questions an evaluator is likely to ask, answered by the rules engine alone (no Gemini), with the exact
figure checked against an independent calculation. And questions no rule covers must never get a rules answer
or an invented number: they go to Gemini, or get an honest "can't answer that reliably"."""

import pytest
from fastapi.testclient import TestClient

from agents.consultant import RULES_CHIP, answer_question
from agents.runtime import _inr, route_consultant
from api.main import app
from rules_engine.fd_sip import fd_maturity, sip_future_value
from rules_engine.goals import plan_goal

DOCS = TestClient(app).post("/demo/sample-session").json()["confirmed"]

SIP = _inr(sip_future_value(monthly_amount=5000, annual_return_percent=10, tenure_months=120).future_value)
FD = _inr(fd_maturity(principal=100000, annual_rate_percent=7, tenure_months=36).maturity_value)
GOAL = _inr(plan_goal(2_000_000, 10, "education")["future_cost"])

ANSWERED_BY_RULES = [
    ("Hi", "Namaste"),
    ("What can you do?", "Ask me about"),
    ("Which tax regime is better for me?", "new tax regime"),
    ("How much tax on a 15 lakh salary?", "₹97,500"),           # 14.25L taxable: 20,000 + 40,000 + 33,750, plus 4% cess
    ("What is the tax on 20 LPA?", "taxable ₹19,25,000"),
    ("How is my tax calculated?", "taxable ₹9,25,000"),
    ("Why is my tax zero?", "less rebate ₹32,500"),
    ("Will I get a refund?", "₹92,500"),
    ("Is my TDS correct?", "₹2,500 more than your Form 16"),
    ("When should I pay advance tax?", "Advance tax: not needed"),
    ("Which ITR form should I use?", "ITR-1"),
    ("What documents do I need to file?", "documents you need"),
    ("How can I save tax?", "Income-tax Act Sec"),
    ("I donate Rs 20000 to charity every year. What do I save in tax?", "80G"),
    ("What is Section 80D?", "25,000"),
    ("What is AIS?", "Annual Information Statement"),
    ("What is HRA?", "rent"),
    ("What is the standard deduction?", "75,000"),
    ("Is income from FD taxable?", "194A"),
    ("Is gift money from my parents taxable?", "tax free"),
    ("Can I withdraw my PF before 5 years?", "5 years"),
    ("Do I have old PF accounts?", "₹1,11,300"),
    ("Explain my salary", "take-home"),
    ("How big should my emergency fund be?", "months of expenses"),
    ("Where is my money going?", "₹83,133"),
    ("Which subscriptions should I cancel?", "a month"),
    ("I sold shares and made a profit of 3 lakh after holding 8 months. How much tax?", "₹62,400"),
    ("I sold my flat for a gain of 40 lakh after 5 years", "₹5,20,000"),
    ("I am a freelancer earning 18 lakh a year, how is my tax calculated?", "44ADA"),
    ("GST on 1 lakh at 18%", "₹18,000"),
    ("How much GST is included in 1180?", "₹180 GST"),
    ("Do I need GST registration as a freelancer?", "20 lakh"),
    ("What is GSTR-3B?", "Table 3.1"),
    ("What is the last date to claim GST input credit?", "30 November"),
    ("FD of 1 lakh at 7% for 3 years", FD),
    ("If I invest 5000 per month in SIP for 10 years", SIP),
    ("I need 20 lakh for my child's education in 10 years", GOAL),
    ("What happens if I miss the ITR deadline?", "5,000"),
    ("What is the new income tax act?", "1 April 2026"),
    ("Which mutual fund should I buy?", "SEBI-registered"),
]

NOT_FOR_RULES = [
    "Should I buy a car on loan or pay cash?",
    "Is Bitcoin a good investment right now?",
    "What will the Sensex do next year?",
    "Write me a poem about money",
    "How do I negotiate a higher salary?",
    "Should I quit my job to start a business?",
    "Can you compare HDFC and ICICI home loans?",
    "Should I invest in gold or real estate?",
    "Explain inflation to a child",
    "मेरे लिए कौन सा टैक्स विकल्प बेहतर है?",
]


@pytest.mark.parametrize("question,expected", ANSWERED_BY_RULES)
def test_rules_engine_answers_without_gemini(question, expected):
    a = answer_question(DOCS, question, mode="fixture")
    assert a.source_chip == RULES_CHIP, f"{question!r} was not answered by the rules engine"
    assert expected in a.answer, f"{question!r}: expected {expected!r} in {a.answer[:300]!r}"


@pytest.mark.parametrize("question", NOT_FOR_RULES)
def test_off_topic_questions_never_get_a_rules_answer_or_an_invented_number(question):
    calls, confident = route_consultant(DOCS, question)
    assert not confident, f"{question!r} should go to Gemini, not a rule"
    a = answer_question(DOCS, question, mode="fixture")  # no Gemini in tests: the honest answer
    assert "reliably" in a.answer and "₹" not in a.answer


def test_live_mode_calls_gemini_only_when_no_rule_covers_it(monkeypatch):
    import agents.consultant as consultant

    calls = []
    monkeypatch.setattr(consultant, "_live_answer", lambda *a, **k: calls.append(a[1]) or ("from gemini", consultant.AI_CHIP))
    monkeypatch.setattr("llm.client.gemini_configured", lambda: True)
    consultant.answer_question(DOCS, "How much tax on a 15 lakh salary?", mode="live")
    assert calls == []  # rules answered; Gemini was not called
    consultant.answer_question(DOCS, "Should I invest in gold or real estate?", mode="live")
    assert calls == ["Should I invest in gold or real estate?"]
