"""Goal planning: what a goal will cost in the future and the monthly amount needed to reach it.

Conventions a financial planner expects:
* the goal is priced in today's rupees and grown by an inflation rate suited to the goal;
* assumed returns stay inside 2%-13% a year (AMFI's guideline for calculators) and are always shown;
* the monthly amount is an annuity-due (invested at the start of each month), with an optional yearly step-up;
* only a category is named (FD/RD, a mix, or equity funds), never a product.
"""

from __future__ import annotations

from rules_engine.savings import goal_category_by_horizon

MIN_RETURN, MAX_RETURN = 2.0, 13.0  # AMFI best-practice guideline for return assumptions in calculators

# Planning defaults (conservative, not forecasts). Inflation by goal type, return by time horizon.
INFLATION_BY_GOAL = {"education": 8.0, "medical": 8.0, "home": 6.0, "wedding": 6.0, "car": 5.0, "travel": 6.0, "retirement": 6.0, "emergency": 6.0, "other": 6.0}


def default_return(years: float) -> float:
    if years < 3:
        return 6.5   # FD/RD category
    if years < 5:
        return 8.5   # a mix of debt and equity
    return 10.0      # equity category, deliberately below the long-run ~12% so plans are not over-optimistic


def clamp_return(r: float) -> tuple[float, bool]:
    c = min(MAX_RETURN, max(MIN_RETURN, r))
    return c, c != r


def monthly_sip_needed(target: float, years: float, annual_return: float, step_up_percent: float = 0.0, already_saved: float = 0.0) -> float:
    """Smallest first-year monthly amount that reaches target, counting money already saved (grown at the same rate)."""
    months = max(1, round(years * 12))
    i = annual_return / 100 / 12
    grown_existing = already_saved * (1 + i) ** months
    need = max(0.0, target - grown_existing)
    if need == 0:
        return 0.0

    def fv(first: float) -> float:
        total, amount = 0.0, first
        for m in range(months):
            if m and m % 12 == 0:
                amount *= 1 + step_up_percent / 100
            total += amount * (1 + i) ** (months - m)  # invested at the start of month m
        return total

    lo, hi = 0.0, need
    for _ in range(60):
        mid = (lo + hi) / 2
        if fv(mid) >= need:
            hi = mid
        else:
            lo = mid
    return round(hi, 2)


def plan_goal(
    cost_today: float, years: float, goal_type: str = "other", inflation_percent: float | None = None,
    annual_return_percent: float | None = None, already_saved: float = 0.0, step_up_percent: float = 0.0,
) -> dict:
    if cost_today <= 0 or years <= 0:
        raise ValueError("Cost and years must be more than zero")
    infl = inflation_percent if inflation_percent is not None else INFLATION_BY_GOAL.get(goal_type, INFLATION_BY_GOAL["other"])
    ret, capped = clamp_return(annual_return_percent if annual_return_percent is not None else default_return(years))
    future_cost = round(cost_today * (1 + infl / 100) ** years, 2)
    monthly = monthly_sip_needed(future_cost, years, ret, step_up_percent, already_saved)
    lump_sum_today = round(max(0.0, future_cost / (1 + ret / 100) ** years - already_saved), 2)
    return {
        "goal_type": goal_type, "cost_today": cost_today, "years": years, "inflation_percent": infl,
        "assumed_return_percent": ret, "return_was_capped": capped, "future_cost": future_cost,
        "monthly_needed": monthly, "step_up_percent": step_up_percent, "lump_sum_needed_today": lump_sum_today,
        "already_saved": already_saved, "category": goal_category_by_horizon(years),
        "note": (f"Assumes {infl:g}% yearly price rise and a {ret:g}% yearly return. Returns are not guaranteed; past "
                 "performance may or may not be sustained. A category is named, never a specific product."),
    }
