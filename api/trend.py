"""Trend analysis — how does the buy-vs-rent decision change over time?

Two distinct analyses:

1. **Timing trend**: "Should I buy now or wait?"
   - Forward offsets: buy_delay = N months (renting meanwhile, investing surplus)
   - Each offset uses the SAME market paths but different purchase timing
   - Shows whether waiting improves or worsens the outcome

2. **ZIP comparison**: "Which neighborhood should I buy in?"
   - Runs the simulation for multiple ZIP codes
   - Uses actual local home values and ZIP-level forecasts
   - Returns a score per ZIP for heatmap display

The old code also had a backward-looking analysis ("what if you'd bought N quarters ago?")
using shifted historical data. This is misleading for decision-making — you can't go back
in time — and it conflated "historical rates were lower" with "buying earlier is better."
Instead, we focus forward: the only actionable question is "buy now vs wait."
"""

from dataclasses import dataclass
from typing import Optional

from market import HistoricalData
from models import SimulationInput
from simulator import run_simulation, MonthlySnapshot
from data_store import get_zip_data

import copy


@dataclass
class TrendPoint:
    """One timing offset in the trend analysis."""
    delay_months: int
    label: str
    buyer_net_worth: float
    renter_net_worth: float
    net_difference: float      # buyer - renter (positive = buying wins)
    breakeven_month: int | None
    # Per-year normalized scores: (buyer_nw - renter_nw) / home_value
    yearly_scores: list[float]
    aggregate_score: float
    # Cost snapshot at purchase time
    mortgage_rate_used: float
    house_price_used: float
    first_month_cost: float    # total_housing_cost in first month of ownership


@dataclass
class TrendResult:
    points: list[TrendPoint]


@dataclass
class ZipScore:
    zip_code: str
    city: Optional[str]
    state: Optional[str]
    house_price: float
    buyer_net_worth: float
    renter_net_worth: float
    net_difference: float
    aggregate_score: float
    breakeven_month: int | None


@dataclass
class ZipMapResult:
    scores: list[ZipScore]


def _clone_inputs(inputs: SimulationInput) -> SimulationInput:
    return copy.deepcopy(inputs)


def _find_breakeven(monthly: list[MonthlySnapshot]) -> int | None:
    """Sustained breakeven: when buyer durably pulls ahead through the end."""
    n = len(monthly)
    if n == 0 or monthly[-1].buyer_net_worth <= monthly[-1].renter_net_worth:
        return None
    for i in range(n - 1, -1, -1):
        if monthly[i].buyer_net_worth <= monthly[i].renter_net_worth:
            return i + 1 if i + 1 < n else None
    return 0  # buyer always ahead


def _compute_yearly_scores(monthly: list[MonthlySnapshot]) -> list[float]:
    """Normalized score at each year-end: (buyer_nw - renter_nw) / home_value."""
    scores = []
    for year in range(len(monthly) // 12):
        m = monthly[year * 12 + 11]
        if m.home_value > 0:
            scores.append((m.buyer_net_worth - m.renter_net_worth) / m.home_value)
        else:
            scores.append(0.0)
    return scores


def _aggregate_score(yearly_scores: list[float]) -> float:
    """Weighted average emphasizing the mid-point of the horizon.

    Picks three anchor years (20%, 50%, 90% through the horizon) and weights
    the middle one highest. Adapts to any horizon from 2 to 15 years.
    """
    n = len(yearly_scores)
    if n == 0:
        return 0.0
    # Anchor at ~20%, ~50%, ~90% of the horizon (0-indexed)
    anchors = [
        (max(0, round(n * 0.2) - 1), 2),   # early
        (max(0, round(n * 0.5) - 1), 5),   # mid — heaviest weight
        (max(0, n - 1), 2),                 # final
    ]
    total_w = 0
    total = 0.0
    for idx, w in anchors:
        if idx < n:
            total += yearly_scores[idx] * w
            total_w += w
    return total / total_w if total_w > 0 else 0.0


def run_trend(
    inputs: SimulationInput,
    data: HistoricalData,
    max_delay_quarters: int = 8,
) -> TrendResult:
    """Simulate buying at different delays: now, +3mo, +6mo, ..., +N quarters.

    Each point answers: "If I wait N more months (renting in the meantime),
    what does my 10-year outcome look like?"

    Key insight: waiting has two opposing effects:
    - PRO: more time to save/invest before buying (larger down payment potential)
    - CON: home prices may rise, rates may change, less time as owner

    Uses fewer simulations (100) per point for speed.
    """
    points: list[TrendPoint] = []

    for q in range(max_delay_quarters + 1):
        delay = q * 3  # quarters → months
        v = _clone_inputs(inputs)
        v.config.num_simulations = min(v.config.num_simulations, 100)
        v.config.buy_delay_months = delay

        result = run_simulation(v, data)

        yearly = _compute_yearly_scores(result.monthly)
        agg = _aggregate_score(yearly)

        first_own = result.monthly[delay] if delay < len(result.monthly) else result.monthly[-1]

        if q == 0:
            label = "Buy now"
        elif q == 1:
            label = "Wait 3 months"
        else:
            label = f"Wait {q * 3} months"

        points.append(TrendPoint(
            delay_months=delay,
            label=label,
            buyer_net_worth=result.avg_buyer_net_worth,
            renter_net_worth=result.avg_renter_net_worth,
            net_difference=result.avg_buyer_net_worth - result.avg_renter_net_worth,
            breakeven_month=_find_breakeven(result.monthly),
            yearly_scores=yearly,
            aggregate_score=agg,
            mortgage_rate_used=result.mortgage_rate_used,
            house_price_used=result.house_price_used,
            first_month_cost=first_own.total_housing_cost,
        ))

    return TrendResult(points=points)


def run_zip_comparison(
    inputs: SimulationInput,
    data: HistoricalData,
    zip_codes: list[str],
) -> ZipMapResult:
    """Run simulation for multiple ZIP codes and return comparative scores.

    For each ZIP, uses the latest historical home value as the house price
    (if available), otherwise falls back to the user-specified price.
    Uses ZIP-level appreciation forecasts when available.
    """
    scores: list[ZipScore] = []

    for zc in zip_codes:
        v = _clone_inputs(inputs)
        v.config.num_simulations = min(v.config.num_simulations, 100)
        v.property.zip_code = zc

        zdata = get_zip_data(zc)
        if zdata and zdata.hist_values:
            v.property.house_price = zdata.hist_values[-1]

        result = run_simulation(v, data)

        yearly = _compute_yearly_scores(result.monthly)
        agg = _aggregate_score(yearly)

        scores.append(ZipScore(
            zip_code=zc,
            city=zdata.city if zdata else None,
            state=zdata.state if zdata else None,
            house_price=result.house_price_used,
            buyer_net_worth=result.avg_buyer_net_worth,
            renter_net_worth=result.avg_renter_net_worth,
            net_difference=result.avg_buyer_net_worth - result.avg_renter_net_worth,
            aggregate_score=agg,
            breakeven_month=_find_breakeven(result.monthly),
        ))

    return ZipMapResult(scores=scores)
