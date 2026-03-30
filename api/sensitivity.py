"""Sensitivity analysis — runs the simulation across varied parameters.

Three modes:
1. **1D axes**: Vary one parameter at a time (bar charts). 8 available dimensions.
2. **2D heatmap**: Cross any two parameters (configurable grid).
3. **What-if scenarios**: Named stories that map to specific parameter changes.

Designed for frontend visualization: bar charts, heatmaps, scenario cards.
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
    """Sustained breakeven: when buyer durably pulls ahead through the end."""
    n = len(monthly)
    if n == 0 or monthly[-1].buyer_net_worth <= monthly[-1].renter_net_worth:
        return None
    for i in range(n - 1, -1, -1):
        if monthly[i].buyer_net_worth <= monthly[i].renter_net_worth:
            return i + 1 if i + 1 < n else None
    return 0  # buyer always ahead


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


# ---------------------------------------------------------------------------
# Axis definitions — each knows how to generate variants from a base input
# ---------------------------------------------------------------------------

@dataclass
class AxisDef:
    name: str
    values: list  # param values to sweep
    labels: list[str]
    apply: object  # callable(SimulationInput, value) → mutated SimulationInput


def _rate_axis(base_rate: float) -> AxisDef:
    deltas = [-0.02, -0.01, -0.005, 0, 0.005, 0.01, 0.02]
    rates = [base_rate + d for d in deltas if base_rate + d >= 0.01]
    labels = [f"{r:.1%}" + (f" ({r - base_rate:+.1%})" if abs(r - base_rate) > 0.001 else "")
              for r in rates]
    def apply(inp, val):
        inp.mortgage.rate = val
    return AxisDef("mortgage_rate", rates, labels, apply)


def _price_axis(base_price: float) -> AxisDef:
    pcts = [-0.20, -0.10, 0, 0.10, 0.20]
    prices = [round(base_price * (1 + p) / 10_000) * 10_000 for p in pcts]
    labels = [f"${p:,.0f}" + (f" ({pct:+.0%})" if pct != 0 else "") for p, pct in zip(prices, pcts)]
    def apply(inp, val):
        inp.property.house_price = val
    return AxisDef("house_price", prices, labels, apply)


def _dp_axis() -> AxisDef:
    dps = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
    def apply(inp, val):
        inp.property.down_payment_pct = val
    return AxisDef("down_payment_pct", dps, [f"{d:.0%} down" for d in dps], apply)


def _outlook_axis() -> AxisDef:
    from models import MarketOutlook
    names = ["optimistic", "historical", "cautious", "pessimistic", "crisis"]
    def apply(inp, val):
        inp.outlook = MarketOutlook.from_preset(val)
    return AxisDef("outlook", names, names, apply)


def _stay_axis(max_years: int) -> AxisDef:
    stays = [y for y in [2, 3, 5, 7, 10, 15] if y <= max_years]
    def apply(inp, val):
        inp.config.stay_years = val
    return AxisDef("stay_years", stays, [f"{y} years" for y in stays], apply)


def _income_axis(base_income: float) -> AxisDef:
    if base_income <= 0:
        base_income = 100_000
    pcts = [-0.20, -0.10, 0, 0.10, 0.20, 0.50]
    incomes = [round(base_income * (1 + p) / 1000) * 1000 for p in pcts]
    labels = [f"${i:,.0f}" + (f" ({p:+.0%})" if p != 0 else "") for i, p in zip(incomes, pcts)]
    def apply(inp, val):
        inp.user.yearly_income = val
    return AxisDef("yearly_income", incomes, labels, apply)


def _cash_axis(base_cash: float) -> AxisDef:
    pcts = [-0.50, 0, 0.50, 1.0, 2.0]
    vals = [round(base_cash * (1 + p) / 1000) * 1000 for p in pcts if base_cash * (1 + p) > 0]
    labels = [f"${v:,.0f}" for v in vals]
    def apply(inp, val):
        inp.user.initial_cash = val
    return AxisDef("initial_cash", vals, labels, apply)


def _risk_axis() -> AxisDef:
    levels = ["savings_only", "conservative", "moderate", "aggressive"]
    def apply(inp, val):
        inp.user.risk_appetite = val
    return AxisDef("risk_appetite", levels, levels, apply)


# Registry of all available axes
def _get_axis(name: str, base_result, inputs: SimulationInput) -> AxisDef | None:
    """Look up an axis definition by name."""
    return {
        "mortgage_rate": lambda: _rate_axis(base_result.mortgage_rate_used),
        "house_price": lambda: _price_axis(base_result.house_price_used),
        "down_payment_pct": lambda: _dp_axis(),
        "outlook": lambda: _outlook_axis(),
        "stay_years": lambda: _stay_axis(inputs.config.years),
        "yearly_income": lambda: _income_axis(inputs.user.yearly_income),
        "initial_cash": lambda: _cash_axis(inputs.user.initial_cash),
        "risk_appetite": lambda: _risk_axis(),
    }.get(name, lambda: None)()


AVAILABLE_AXES = [
    "mortgage_rate", "house_price", "down_payment_pct", "outlook",
    "stay_years", "yearly_income", "initial_cash", "risk_appetite",
]


def run_sensitivity(
    inputs: SimulationInput,
    data: HistoricalData,
    axes_to_run: list[str] | None = None,
    heatmap_x: str | None = None,
    heatmap_y: str | None = None,
) -> SensitivityResult:
    """Run sensitivity analysis across specified parameter dimensions.

    Args:
        axes_to_run: Which 1D axes to sweep. Default: rate, price, down payment, outlook.
        heatmap_x: X axis for 2D heatmap. Default: "house_price".
        heatmap_y: Y axis for 2D heatmap. Default: "mortgage_rate".
    """
    base = run_simulation(inputs, data)
    base_diff = base.avg_buyer_net_worth - base.avg_renter_net_worth

    if axes_to_run is None:
        axes_to_run = ["mortgage_rate", "house_price", "down_payment_pct", "outlook"]

    axes: dict[str, list[SensitivityPoint]] = {}

    for axis_name in axes_to_run:
        axis_def = _get_axis(axis_name, base, inputs)
        if not axis_def:
            continue
        points = []
        for val, label in zip(axis_def.values, axis_def.labels):
            v = _clone_inputs(inputs)
            v.config.num_simulations = min(v.config.num_simulations, 100)
            axis_def.apply(v, val)
            points.append(_run_variant(v, data, axis_def.name, val if isinstance(val, (int, float)) else 0, label))
        axes[axis_name] = points

    # 2D Heatmap — configurable axes
    hm_x = heatmap_x or "house_price"
    hm_y = heatmap_y or "mortgage_rate"
    heatmap = _build_heatmap(inputs, data, base, x_axis=hm_x, y_axis=hm_y)

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
    x_axis: str = "house_price",
    y_axis: str = "mortgage_rate",
) -> HeatmapResult:
    """Build a 2D grid crossing any two parameter axes.

    5 × 5 = 25 simulations at 50 sims each. Target: < 3 seconds total.
    """
    from scoring import compute_buy_score

    x_def = _get_axis(x_axis, base_result, inputs)
    y_def = _get_axis(y_axis, base_result, inputs)
    if not x_def or not y_def:
        # Fallback to defaults if unknown axis requested
        x_def = _price_axis(base_result.house_price_used)
        y_def = _rate_axis(base_result.mortgage_rate_used)

    # Trim to 5 values for heatmap (pick evenly spaced subset if more)
    def pick5(vals, labels):
        if len(vals) <= 5:
            return vals, labels
        indices = [0, len(vals) // 4, len(vals) // 2, 3 * len(vals) // 4, len(vals) - 1]
        return [vals[i] for i in indices], [labels[i] for i in indices]

    x_vals, x_labels = pick5(x_def.values, x_def.labels)
    y_vals, y_labels = pick5(y_def.values, y_def.labels)

    cells: list[list[HeatmapCell]] = []
    for yi, y_val in enumerate(y_vals):
        row: list[HeatmapCell] = []
        for xi, x_val in enumerate(x_vals):
            v = copy.deepcopy(inputs)
            v.config.num_simulations = 50
            x_def.apply(v, x_val)
            y_def.apply(v, y_val)

            result = run_simulation(v, data)

            row.append(HeatmapCell(
                x_label=x_labels[xi],
                y_label=y_labels[yi],
                x_value=x_val if isinstance(x_val, (int, float)) else xi,
                y_value=y_val if isinstance(y_val, (int, float)) else yi,
                net_difference=result.avg_buyer_net_worth - result.avg_renter_net_worth,
                breakeven_month=_find_breakeven(result.monthly),
                buy_score=compute_buy_score(result),
            ))
        cells.append(row)

    return HeatmapResult(
        x_axis=x_def.name,
        y_axis=y_def.name,
        x_labels=x_labels,
        y_labels=y_labels,
        cells=cells,
    )


# ---------------------------------------------------------------------------
# What-if scenarios — named stories
# ---------------------------------------------------------------------------

@dataclass
class WhatIfScenario:
    id: str
    name: str
    description: str
    buyer_net_worth: float
    renter_net_worth: float
    net_difference: float
    delta_from_base: float  # change vs base scenario
    breakeven_month: int | None
    buy_score: int


# Predefined scenario definitions: (id, name, description, apply_fn)
def _whatif_defs(base_result, inputs: SimulationInput) -> list[tuple]:
    """Return list of (id, name, description, apply_fn) tuples."""
    base_rate = base_result.mortgage_rate_used
    base_price = base_result.house_price_used
    from models import MarketOutlook

    defs = [
        ("rates_drop_1pct", "Rates drop 1%",
         f"Mortgage rate falls to {base_rate - 0.01:.1%}",
         lambda v: setattr(v.mortgage, 'rate', base_rate - 0.01)),

        ("rates_drop_2pct", "Rates drop 2%",
         f"Mortgage rate falls to {base_rate - 0.02:.1%}",
         lambda v: setattr(v.mortgage, 'rate', base_rate - 0.02)),

        ("rates_rise_1pct", "Rates rise 1%",
         f"Mortgage rate climbs to {base_rate + 0.01:.1%}",
         lambda v: setattr(v.mortgage, 'rate', base_rate + 0.01)),

        ("cheaper_home", "Buy 15% cheaper",
         f"Find a home at ${base_price * 0.85:,.0f} instead of ${base_price:,.0f}",
         lambda v: setattr(v.property, 'house_price', round(base_price * 0.85 / 10_000) * 10_000)),

        ("save_2_more_years", "Save for 2 more years",
         "Keep renting and saving for 24 months before buying",
         lambda v: setattr(v.config, 'buy_delay_months', 24)),

        ("20pct_down", "Put 20% down",
         "Larger down payment eliminates PMI",
         lambda v: setattr(v.property, 'down_payment_pct', 0.20)),

        ("crash_next_year", "Market crash next year",
         "Pessimistic outlook with 25% housing + 25% stock crash probability",
         lambda v: setattr(v, 'outlook', MarketOutlook.from_preset("pessimistic"))),

        ("stay_5_sell", "Stay 5 years then sell",
         "Own for 5 years, sell, rent and invest the rest",
         lambda v: setattr(v.config, 'stay_years', min(5, v.config.years))),

        ("conservative_investing", "Keep cash in savings",
         "Don't invest surplus in stocks — HYSA at 4.5% only",
         lambda v: setattr(v.user, 'risk_appetite', 'savings_only')),
    ]

    # Filter out scenarios that duplicate the base case
    if inputs.config.buy_delay_months >= 24:
        defs = [(i, n, d, f) for i, n, d, f in defs if i != "save_2_more_years"]
    if inputs.property.down_payment_pct >= 0.20:
        defs = [(i, n, d, f) for i, n, d, f in defs if i != "20pct_down"]
    if inputs.user.risk_appetite == "savings_only":
        defs = [(i, n, d, f) for i, n, d, f in defs if i != "conservative_investing"]

    return defs


def run_whatif_scenarios(
    inputs: SimulationInput,
    data: HistoricalData,
    scenario_ids: list[str] | None = None,
) -> tuple[float, list[WhatIfScenario]]:
    """Run named what-if scenarios and return results with deltas from base.

    Returns: (base_net_diff, list of WhatIfScenario)
    """
    from scoring import compute_buy_score

    base = run_simulation(inputs, data)
    base_diff = base.avg_buyer_net_worth - base.avg_renter_net_worth
    defs = _whatif_defs(base, inputs)

    if scenario_ids:
        defs = [(i, n, d, f) for i, n, d, f in defs if i in scenario_ids]

    results = []
    for sid, name, desc, apply_fn in defs:
        v = _clone_inputs(inputs)
        v.config.num_simulations = min(v.config.num_simulations, 100)
        apply_fn(v)
        result = run_simulation(v, data)
        diff = result.avg_buyer_net_worth - result.avg_renter_net_worth

        results.append(WhatIfScenario(
            id=sid,
            name=name,
            description=desc,
            buyer_net_worth=result.avg_buyer_net_worth,
            renter_net_worth=result.avg_renter_net_worth,
            net_difference=diff,
            delta_from_base=diff - base_diff,
            breakeven_month=_find_breakeven(result.monthly),
            buy_score=compute_buy_score(result),
        ))

    return base_diff, results
