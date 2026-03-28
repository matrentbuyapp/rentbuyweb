"""Sensitivity analysis — runs the simulation across varied parameters.

Two modes:
1. **1D axes**: Vary one parameter at a time (bar charts)
2. **2D heatmap**: Cross two parameters (rate × price grid)

Designed for frontend visualization: bar charts, heatmaps, summary cards.
"""

from dataclasses import dataclass, field
from market import HistoricalData
from models import SimulationInput
from simulator import run_simulation

import copy


@dataclass
class SensitivityPoint:
    """One cell in the sensitivity matrix."""
    label: str          # human-readable label for the varied param value
    param_name: str     # which param was varied
    param_value: float  # the actual value used
    buyer_net_worth: float
    renter_net_worth: float
    net_difference: float  # buyer - renter (positive = buying wins)
    breakeven_month: int | None  # first month buyer NW > renter NW, or None


@dataclass
class HeatmapCell:
    """One cell in the 2D heatmap."""
    x_label: str
    y_label: str
    x_value: float
    y_value: float
    net_difference: float
    breakeven_month: int | None
    buy_score: int  # 0-100 deterministic score


@dataclass
class HeatmapResult:
    x_axis: str            # param name (e.g. "house_price")
    y_axis: str            # param name (e.g. "mortgage_rate")
    x_labels: list[str]
    y_labels: list[str]
    cells: list[list[HeatmapCell]]  # cells[y_idx][x_idx]


@dataclass
class SensitivityResult:
    base_buyer_nw: float
    base_renter_nw: float
    base_net_diff: float
    base_buy_score: int
    axes: dict[str, list[SensitivityPoint]]  # param_name → list of points
    heatmap: HeatmapResult | None = None


def _find_breakeven(monthly: list) -> int | None:
    for i, m in enumerate(monthly):
        if m.buyer_net_worth > m.renter_net_worth:
            return i
    return None


def _run_variant(
    inputs: SimulationInput,
    data: HistoricalData,
    param_name: str,
    param_value: float,
    label: str,
) -> SensitivityPoint:
    """Run one simulation variant and extract summary metrics."""
    result = run_simulation(inputs, data)
    return SensitivityPoint(
        label=label,
        param_name=param_name,
        param_value=param_value,
        buyer_net_worth=result.avg_buyer_net_worth,
        renter_net_worth=result.avg_renter_net_worth,
        net_difference=result.avg_buyer_net_worth - result.avg_renter_net_worth,
        breakeven_month=_find_breakeven(result.monthly),
    )


def _clone_inputs(inputs: SimulationInput) -> SimulationInput:
    return copy.deepcopy(inputs)


def run_sensitivity(
    inputs: SimulationInput,
    data: HistoricalData,
) -> SensitivityResult:
    """Run sensitivity analysis across mortgage rate, house price, down payment, and outlook.

    Varies each parameter while holding others at their base values.
    Uses fewer simulations (100) per variant for speed.
    """
    base = run_simulation(inputs, data)
    base_diff = base.avg_buyer_net_worth - base.avg_renter_net_worth

    axes: dict[str, list[SensitivityPoint]] = {}

    # Use fewer sims for sensitivity (speed)
    def fast_inputs(inp: SimulationInput) -> SimulationInput:
        c = _clone_inputs(inp)
        c.config.num_simulations = min(c.config.num_simulations, 100)
        return c

    # --- Axis 1: Mortgage rate ±2% in 0.5% steps ---
    base_rate = base.mortgage_rate_used
    rate_points = []
    for delta in [-0.02, -0.01, -0.005, 0, 0.005, 0.01, 0.02]:
        rate = base_rate + delta
        if rate < 0.01:
            continue
        v = fast_inputs(inputs)
        v.mortgage.rate = rate
        label = f"{rate:.1%}" if delta == 0 else f"{rate:.1%} ({delta:+.1%})"
        rate_points.append(_run_variant(v, data, "mortgage_rate", rate, label))
    axes["mortgage_rate"] = rate_points

    # --- Axis 2: House price ±20% in 10% steps ---
    base_price = base.house_price_used
    price_points = []
    for pct in [-0.20, -0.10, 0, 0.10, 0.20]:
        price = round(base_price * (1 + pct) / 10_000) * 10_000
        v = fast_inputs(inputs)
        v.property.house_price = price
        label = f"${price:,.0f}" if pct == 0 else f"${price:,.0f} ({pct:+.0%})"
        price_points.append(_run_variant(v, data, "house_price", price, label))
    axes["house_price"] = price_points

    # --- Axis 3: Down payment 5% to 30% ---
    dp_points = []
    for dp in [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]:
        v = fast_inputs(inputs)
        v.property.down_payment_pct = dp
        dp_points.append(_run_variant(v, data, "down_payment_pct", dp, f"{dp:.0%} down"))
    axes["down_payment_pct"] = dp_points

    # --- Axis 4: Market outlook presets ---
    from models import MarketOutlook
    outlook_presets = ["optimistic", "historical", "cautious", "pessimistic", "crisis"]
    outlook_points = []
    for preset_name in outlook_presets:
        v = fast_inputs(inputs)
        v.outlook = MarketOutlook.from_preset(preset_name)
        outlook_points.append(_run_variant(
            v, data, "outlook", outlook_presets.index(preset_name), preset_name,
        ))
    axes["outlook"] = outlook_points

    # --- 2D Heatmap: mortgage rate × house price ---
    heatmap = _build_heatmap(inputs, data, base)

    from scoring import compute_buy_score
    return SensitivityResult(
        base_buyer_nw=base.avg_buyer_net_worth,
        base_renter_nw=base.avg_renter_net_worth,
        base_net_diff=base_diff,
        base_buy_score=compute_buy_score(base),
        axes=axes,
        heatmap=heatmap,
    )


def _build_heatmap(
    inputs: SimulationInput,
    data: HistoricalData,
    base_result,
) -> HeatmapResult:
    """Build a 2D grid: mortgage rate (Y) × house price (X).

    5 rates × 5 prices = 25 simulations at 50 sims each.
    Target: < 3 seconds total.
    """
    from scoring import compute_buy_score

    base_rate = base_result.mortgage_rate_used
    base_price = base_result.house_price_used

    # X axis: house price at -20%, -10%, base, +10%, +20%
    price_pcts = [-0.20, -0.10, 0.0, 0.10, 0.20]
    prices = [round(base_price * (1 + p) / 10_000) * 10_000 for p in price_pcts]
    x_labels = []
    for pct, price in zip(price_pcts, prices):
        if pct == 0:
            x_labels.append(f"${price // 1000}k")
        else:
            x_labels.append(f"${price // 1000}k ({pct:+.0%})")

    # Y axis: mortgage rate at -1.5%, -0.75%, base, +0.75%, +1.5%
    rate_deltas = [-0.015, -0.0075, 0.0, 0.0075, 0.015]
    rates = [max(0.01, base_rate + d) for d in rate_deltas]
    y_labels = []
    for delta, rate in zip(rate_deltas, rates):
        if delta == 0:
            y_labels.append(f"{rate:.2%}")
        else:
            y_labels.append(f"{rate:.2%} ({delta:+.2%})")

    # Run the grid
    cells: list[list[HeatmapCell]] = []
    for yi, rate in enumerate(rates):
        row: list[HeatmapCell] = []
        for xi, price in enumerate(prices):
            v = copy.deepcopy(inputs)
            v.config.num_simulations = 50  # fast
            v.mortgage.rate = rate
            v.property.house_price = price

            result = run_simulation(v, data)

            row.append(HeatmapCell(
                x_label=x_labels[xi],
                y_label=y_labels[yi],
                x_value=price,
                y_value=rate,
                net_difference=result.avg_buyer_net_worth - result.avg_renter_net_worth,
                breakeven_month=_find_breakeven(result.monthly),
                buy_score=compute_buy_score(result),
            ))
        cells.append(row)

    return HeatmapResult(
        x_axis="house_price",
        y_axis="mortgage_rate",
        x_labels=x_labels,
        y_labels=y_labels,
        cells=cells,
    )
