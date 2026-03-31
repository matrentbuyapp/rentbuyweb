"""Deterministic buy-vs-rent scoring.

Computes a 0-100 score and verdict from simulation results.
This is pure math — no LLM, no randomness, same inputs → same output.

Score interpretation:
  0-20:  Renting is strongly favored
  20-40: Renting is moderately favored
  40-60: Roughly equal / depends on personal factors
  60-80: Buying is moderately favored
  80-100: Buying is strongly favored
"""

from dataclasses import dataclass

from simulator import SimulationResult, MonthlySnapshot


def compute_buy_score(result: SimulationResult) -> int:
    """Compute a deterministic 0-100 buy score from simulation results.

    Components (weighted):
    1. Net worth difference at year 10, normalized by home price (40%)
    2. Breakeven timing — how quickly buying overtakes renting (25%)
    3. Monthly affordability — how often costs exceed budget (15%)
    4. Equity position at year 10 relative to home value (20%)
    """
    m = result.monthly
    months = len(m)
    if months == 0:
        return 50

    final = m[-1]
    price = result.house_price_used

    # --- Component 1: Normalized net worth difference (40%) ---
    # (buyer_nw - renter_nw) / house_price, clamped to [-0.3, +0.3]
    if price > 0:
        nw_ratio = (final.buyer_net_worth - final.renter_net_worth) / price
    else:
        nw_ratio = 0
    nw_ratio = max(-0.3, min(0.3, nw_ratio))
    # Map [-0.3, +0.3] → [0, 100]
    nw_score = (nw_ratio + 0.3) / 0.6 * 100

    # --- Component 2: Breakeven timing (25%) ---
    # Uses sustained breakeven (when buyer durably pulls ahead), not first crossing.
    # Also penalizes volatile scenarios where the lead changes frequently.
    breakeven = result.breakeven_month  # None if buyer never durably leads
    crossings = result.crossing_count

    early = max(months * 0.20, 6)    # first 20% of horizon → strong
    mid = months * 0.50              # first 50% → decent
    if breakeven is None:
        breakeven_score = 15
    elif breakeven <= early:
        breakeven_score = 95
    elif breakeven <= mid:
        breakeven_score = 80 - (breakeven - early) * (40 / (mid - early))
    else:
        tail = months - mid
        breakeven_score = 40 - (breakeven - mid) * (25 / tail) if tail > 0 else 40
        breakeven_score = max(breakeven_score, 15)

    # Penalize volatile scenarios — each extra crossing beyond 1 costs 3 points
    if crossings > 1:
        breakeven_score = max(15, breakeven_score - (crossings - 1) * 3)

    # --- Component 3: Affordability (15%) ---
    # What fraction of months is total_housing_cost within budget?
    owned_months = [s for s in m if s.mortgage_payment > 0]
    if owned_months:
        affordable = sum(1 for s in owned_months if s.total_housing_cost <= s.budget * 1.05)
        afford_ratio = affordable / len(owned_months)
    else:
        afford_ratio = 1.0
    afford_score = afford_ratio * 100

    # --- Component 4: Equity position (20%) ---
    # equity / home_value — how much of the home you "own" net of sell costs
    if final.home_value > 0:
        equity_ratio = final.buyer_equity / final.home_value
    else:
        equity_ratio = 0
    equity_ratio = max(0, min(1, equity_ratio))
    # Map [0, 0.5] → [0, 100] (capped — 50% equity at year 10 is very strong)
    equity_score = min(equity_ratio / 0.5, 1.0) * 100

    # --- Weighted combination ---
    raw = (
        nw_score * 0.40
        + breakeven_score * 0.25
        + afford_score * 0.15
        + equity_score * 0.20
    )

    # Clamp to 8-96 range (never absolute)
    return max(8, min(96, round(raw)))


def compute_verdict(score: int) -> str:
    """Deterministic verdict from score. Same score → always same text."""
    if score >= 80:
        return "Buying looks like a strong financial move in your situation."
    elif score >= 65:
        return "Buying has a moderate edge over renting here — worth serious consideration."
    elif score >= 50:
        return "It's roughly a toss-up — your decision should weigh non-financial factors too."
    elif score >= 35:
        return "Renting has a moderate financial advantage in this scenario."
    else:
        return "Renting is the stronger financial choice here."


@dataclass
class Headline:
    """The single primary result a first-time user should see.

    Designed to answer three questions in order:
    1. "Should I buy or rent?" → winner + one-liner
    2. "By how much?" → dollar amount in plain language
    3. "How sure is that?" → confidence qualifier
    """
    winner: str               # "buy" | "rent" | "toss-up"
    short: str                # one sentence: "You'd be $47K richer buying"
    detail: str               # two sentences with context
    confidence: str           # "high" | "moderate" | "low"
    monthly_savings: float    # how much cheaper/month the winner's option is at start


def compute_headline(result: SimulationResult) -> Headline:
    """Build a user-friendly headline from simulation results."""
    m = result.monthly
    months = len(m)
    if months == 0:
        return Headline("toss-up", "Not enough data.", "", "low", 0)

    final = m[-1]
    diff = final.buyer_net_worth - final.renter_net_worth
    abs_diff = abs(diff)
    years = months // 12
    price = result.house_price_used
    crossings = result.crossing_count
    be = result.breakeven_month

    # Monthly cost comparison at month 0 (or first owned month)
    first_owned = next((s for s in m if s.mortgage_payment > 0), m[0])
    monthly_cost_diff = first_owned.total_housing_cost - first_owned.rent

    # Winner determination: use a materiality threshold (1% of house price)
    threshold = price * 0.01
    if abs_diff < threshold:
        winner = "toss-up"
    elif diff > 0:
        winner = "buy"
    else:
        winner = "rent"

    # Confidence: based on crossing count and magnitude
    if crossings <= 1 and abs_diff > price * 0.05:
        confidence = "high"
    elif crossings <= 2 and abs_diff > price * 0.02:
        confidence = "moderate"
    else:
        confidence = "low"

    # Format dollar amounts in human-readable form
    def _fmt(v: float) -> str:
        av = abs(v)
        if av >= 1_000_000:
            return f"${av / 1_000_000:.1f}M"
        elif av >= 1_000:
            return f"${av / 1_000:.0f}K"
        else:
            return f"${av:,.0f}"

    # Build the short headline
    if winner == "buy":
        short = f"You'd be {_fmt(diff)} better off buying after {years} years"
    elif winner == "rent":
        short = f"You'd be {_fmt(abs_diff)} better off renting after {years} years"
    else:
        short = f"It's essentially a wash after {years} years"

    # Build the detail with context
    if winner == "buy":
        if be is not None and be < months * 0.5:
            timing = f"Buying pulls ahead at year {be // 12 + 1} and stays ahead."
        elif be is not None:
            timing = f"Buying takes until year {be // 12 + 1} to pull ahead."
        else:
            timing = ""
        if monthly_cost_diff > 0:
            detail = f"Buying costs ${monthly_cost_diff:,.0f}/mo more than renting, " \
                     f"but equity growth more than makes up for it. {timing}"
        else:
            detail = f"Buying is actually cheaper month-to-month too. {timing}"
    elif winner == "rent":
        detail = f"Renting saves ${-monthly_cost_diff:,.0f}/mo if buying is cheaper, " \
                 f"or the investment returns on renter savings outpace home equity." \
                 if monthly_cost_diff <= 0 else \
                 f"Buying costs ${monthly_cost_diff:,.0f}/mo more, and the extra cost " \
                 f"doesn't pay off through equity growth over {years} years."
    else:
        detail = f"The difference is only {_fmt(abs_diff)} on a {_fmt(price)} home. " \
                 f"Non-financial factors should drive your decision."

    if crossings >= 3 and confidence != "high":
        detail += f" The lead changes {crossings} times — your timing matters."

    return Headline(
        winner=winner,
        short=short,
        detail=detail,
        confidence=confidence,
        monthly_savings=float(round(abs(monthly_cost_diff), 0)),
    )
