from agents.text import clean_answer, pretty_merchant

# Captured from a live Gemini answer that was shown raw to a user.
RAW = (
    "I have analyzed your bank statement.\n\n### **Monthly Leak Summary**\n* **Total Monthly Leak:** ₹648 per month\n---\n"
    "### **Detected Recurring Charges**\n1. **CloudNotes Premium** (`UPI-CLOUDNOTES PREMIUM-cloudnotes@upi`)\n"
    "   * **Monthly Amount:** ₹199\n   * **Initial Status Guess:** **Idle**\n"
    "2. **Fitzone Gym** (`UPI AUTOPAY-FITZONE GYM-fitzone@upi`) * **Monthly Amount:** ₹449 * *Active*"
)


def test_no_markdown_symbols_survive():
    out = clean_answer(RAW)
    for bad in ("###", "**", "`", "---"):
        assert bad not in out, (bad, out)


def test_bank_strings_become_plain_names_and_numbers_are_untouched():
    out = clean_answer(RAW)
    assert "UPI-CLOUDNOTES" not in out and "@upi" not in out
    assert "cloudnotes premium" in out.lower() and "Fitzone Gym" in out
    for n in ("₹648", "₹199", "₹449"):
        assert n in out


def test_bullets_are_one_per_line():
    out = clean_answer("• a\n* b\n- c item * d item")
    assert out.splitlines().count("• b") == 1 and "• d item" in out.splitlines()


def test_pretty_merchant():
    assert pretty_merchant("UPI AUTOPAY-FITZONE GYM-fitzone@upi") == "Fitzone Gym"
    assert pretty_merchant("NEFT-QUICKCASH LOANS EMI-LN00988123") == "Quickcash Loans EMI"


def test_no_duplicated_merchant_names():
    out = clean_answer(RAW)
    assert "Cloudnotes Premium Cloudnotes" not in out and "Fitzone Gym Fitzone Gym" not in out
