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
