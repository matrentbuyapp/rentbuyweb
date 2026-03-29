"""Monte Carlo rent-vs-buy simulator.

Architecture: two layers for performance.

Layer 1 — Market Paths (expensive, cacheable):
  Pre-generate N random paths for stocks, home values, and rent using
  historical data as drift. Cached per (ZIP, data vintage) — shared across
  all requests for the same area.

Layer 2 — Cash Flow Simulation (cheap, per-request):
  Apply user-specific params (crash probability, budget, income, down payment)
  on top of cached paths. This is pure arithmetic — fast enough for slider UIs.
"""

import hashlib
import json
import numpy as np
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from models import SimulationInput
from mortgage import amortize, pmi_schedule, credit_rate_adjustment, monthly_tax_savings
from market import (
    HistoricalData,
    generate_stock_path,
    generate_home_appreciation_path,
    generate_rent_path,
    generate_rate_path,
    apply_crash,
    get_property_tax_rate,
    get_state_tax_rate,
)
from data_store import get_zip_growth_index, get_median_home_price, get_national_median_home_price


# ---------------------------------------------------------------------------
# Layer 1: Pre-generated market paths (cached)
# ---------------------------------------------------------------------------

@dataclass
class MarketPaths:
    """Pre-generated random market paths for N simulations.

    These are independent of user-specific params (budget, income, crash prefs)
    and can be reused across requests.
    """
    stock_paths: np.ndarray     # shape: (n_sims, n_months) — monthly growth factors
    home_paths: np.ndarray      # shape: (n_sims, n_months) — cumulative index (base=1.0)
    rent_paths: np.ndarray      # shape: (n_sims, n_months) — cumulative multiplier
    rate_paths: np.ndarray      # shape: (n_sims, n_months) — mortgage rate forecast (percent)


def _generate_market_paths(
    data: HistoricalData,
    zip_code: Optional[str],
    n_months: int,
    n_sims: int,
    rate_target: float | None = None,
    rate_volatility_scale: float = 1.0,
) -> MarketPaths:
    """Generate all random market paths. No crash applied yet."""
    zip_cumulative = None
    if zip_code:
        zip_cumulative = get_zip_growth_index(zip_code, n_months + 1)

    stock = np.zeros((n_sims, n_months))
    home = np.zeros((n_sims, n_months))
    rent = np.zeros((n_sims, n_months))
    rate = np.zeros((n_sims, n_months))

    for sim in range(n_sims):
        rng = np.random.default_rng(seed=42 + sim)
        stock[sim] = generate_stock_path(data.stock_monthly_growth, n_months, rng)
        home[sim] = generate_home_appreciation_path(
            data.hpi_cumulative, zip_cumulative, n_months, rng,
        )
        rent[sim] = generate_rent_path(data.cpi_monthly_growth, n_months, rng)
        rate[sim] = generate_rate_path(
            data.mortgage_rates, n_months, rng,
            rate_target=rate_target,
            rate_volatility_scale=rate_volatility_scale,
        )

    return MarketPaths(stock_paths=stock, home_paths=home, rent_paths=rent, rate_paths=rate)


# Cache: maps (data_id, zip_code, n_months, n_sims) → MarketPaths
_paths_cache: dict[tuple, MarketPaths] = {}
_PATHS_CACHE_MAX = 64


def get_cached_paths(
    data: HistoricalData,
    zip_code: Optional[str],
    n_months: int,
    n_sims: int,
    rate_target: float | None = None,
    rate_volatility_scale: float = 1.0,
) -> MarketPaths:
    """Get or generate cached market paths.

    Keyed on (data identity, zip, months, sims, rate overrides). When HistoricalData
    reloads (new id), old cache entries become unreachable and get evicted.
    """
    key = (id(data), zip_code, n_months, n_sims, rate_target, rate_volatility_scale)
    if key in _paths_cache:
        return _paths_cache[key]

    paths = _generate_market_paths(
        data, zip_code, n_months, n_sims,
        rate_target=rate_target,
        rate_volatility_scale=rate_volatility_scale,
    )

    # Simple eviction: clear if too large
    if len(_paths_cache) >= _PATHS_CACHE_MAX:
        _paths_cache.clear()
    _paths_cache[key] = paths
    return paths


# ---------------------------------------------------------------------------
# Layer 2: Cash flow simulation (per-request, fast)
# ---------------------------------------------------------------------------

@dataclass
class MonthlySnapshot:
    """One month of simulation output (averaged across all MC runs)."""
    home_value: float = 0.0
    mortgage_payment: float = 0.0
    interest_payment: float = 0.0
    principal_payment: float = 0.0
    remaining_balance: float = 0.0
    maintenance: float = 0.0
    property_tax: float = 0.0
    insurance: float = 0.0
    pmi: float = 0.0
    tax_savings: float = 0.0
    total_housing_cost: float = 0.0
    rent: float = 0.0
    budget: float = 0.0
    buyer_investment: float = 0.0
    renter_investment: float = 0.0
    buyer_equity: float = 0.0
    buyer_net_worth: float = 0.0
    renter_net_worth: float = 0.0
    cumulative_buy_cost: float = 0.0
    cumulative_rent_cost: float = 0.0


@dataclass
class PercentileBands:
    """Percentile bands across MC simulations for one metric, per month."""
    p10: list[float]
    p25: list[float]
    p50: list[float]
    p75: list[float]
    p90: list[float]


@dataclass
class SimulationPercentiles:
    """Percentile bands for key metrics — lets UI show uncertainty fans."""
    buyer_net_worth: PercentileBands
    renter_net_worth: PercentileBands
    home_value: PercentileBands
    mortgage_rate: PercentileBands
    buyer_equity: PercentileBands


@dataclass
class SimulationResult:
    monthly: list[MonthlySnapshot]
    avg_buyer_net_worth: float
    avg_renter_net_worth: float
    house_price_used: float
    mortgage_rate_used: float
    property_tax_rate: float
    breakeven_month: int | None       # sustained: last durable crossing where buyer stays ahead
    crossing_count: int               # how many times buyer/renter lead swaps
    percentiles: SimulationPercentiles


def estimate_house_price(
    monthly_rent: float,
    monthly_budget: float,
    down_payment_pct: float,
    maintenance_rate: float,
    mortgage_rate: float,
    term_years: int,
) -> list[float]:
    """Estimate reasonable house prices from rent and budget.

    Returns [low, mid, high] prices rounded to nearest $10k.
    """
    base = 100_000
    loan = base * (1 - down_payment_pct)
    r = mortgage_rate / 12
    n = term_years * 12

    if r == 0:
        mortgage_pmt = loan / n
    else:
        mortgage_pmt = loan * (r * (1 + r) ** n) / ((1 + r) ** n - 1)

    monthly_cost_per_100k = mortgage_pmt + (maintenance_rate + 0.009) * base / 12

    price_at_rent = monthly_rent / monthly_cost_per_100k * base
    price_at_budget = monthly_budget / monthly_cost_per_100k * base

    low = round(min(price_at_rent, price_at_budget) / 10_000) * 10_000
    high = round(max(price_at_rent, price_at_budget) / 10_000) * 10_000
    mid = round((low + high) / 2 / 10_000) * 10_000

    return sorted(set([low, mid, high]))


def run_simulation(
    inputs: SimulationInput,
    data: HistoricalData,
    # Legacy params for backward compatibility — prefer using inputs.outlook instead
    housing_crash_prob: float | None = None,
    housing_crash_drop: float | None = None,
    stock_crash_prob: float | None = None,
    stock_crash_drop: float | None = None,
    crash_horizon_months: int | None = None,
) -> SimulationResult:
    """Run the full Monte Carlo simulation.

    Market paths are cached and shared across requests with the same ZIP.
    Only the crash/vol overlay and cash flow math run per-request.

    Crash/volatility settings come from inputs.outlook (MarketOutlook).
    Legacy crash params override outlook if provided (backward compat).
    """
    u = inputs.user
    p = inputs.property
    m = inputs.mortgage
    cfg = inputs.config

    months = cfg.years * 12
    n_sims = cfg.num_simulations
    buy_delay = cfg.buy_delay_months
    stay_months = (cfg.stay_years * 12) if cfg.stay_years else months
    sell_month = buy_delay + stay_months  # month when buyer sells (may be >= months if owning forever)

    # --- Resolve mortgage rate ---
    # If user explicitly set a rate, it's locked regardless of delay.
    # Otherwise, use today's rate for immediate purchase or the forecasted
    # rate at purchase month for delayed purchases (per-sim, below).
    rate_adj = credit_rate_adjustment(m.credit_quality, p.down_payment_pct)
    mortgage_term = m.term_years * 12
    if m.rate is not None:
        mortgage_rate = m.rate + rate_adj / 100
        use_forecasted_rate = False
    else:
        mortgage_rate = data.mortgage_rates[-1] / 100 + rate_adj / 100
        use_forecasted_rate = buy_delay > 0  # only matters if purchasing later

    # --- Resolve house price ---
    if p.house_price and p.house_price > 0:
        house_price = p.house_price
    else:
        # Use Zillow median for ZIP, national median otherwise
        median = get_median_home_price(p.zip_code) if p.zip_code else None
        house_price = median or get_national_median_home_price()

    # --- Resolve tax rates ---
    prop_tax_rate = get_property_tax_rate(p.zip_code)
    state_tax_rate = get_state_tax_rate(p.zip_code)

    # --- Risk appetite ---
    # "savings_only" bypasses the stock market entirely — cash grows at a
    # fixed savings account rate (no MC variance on the investment side).
    SAVINGS_APY = 0.045  # 4.5% — median HYSA rate
    savings_only = u.risk_appetite.lower() == "savings_only"
    stock_leverage = {"conservative": 0.5, "moderate": 1.0, "aggressive": 1.5}.get(
        u.risk_appetite.lower(), 1.0
    )
    monthly_savings_return = (1 + SAVINGS_APY) ** (1 / 12) if savings_only else None

    # --- Resolve outlook (legacy params override if provided) ---
    ol = inputs.outlook
    h_prob = housing_crash_prob if housing_crash_prob is not None else ol.housing_crash_prob
    h_drop = housing_crash_drop if housing_crash_drop is not None else ol.housing_crash_drop
    h_drawdown = ol.housing_drawdown_months
    s_prob = stock_crash_prob if stock_crash_prob is not None else ol.stock_crash_prob
    s_drop = stock_crash_drop if stock_crash_drop is not None else ol.stock_crash_drop
    s_drawdown = ol.stock_drawdown_months
    horizon = min(crash_horizon_months or ol.crash_horizon_months, months)
    vol_scale = ol.volatility_scale

    # --- Layer 1: Get cached market paths ---
    paths = get_cached_paths(
        data, p.zip_code, months, n_sims,
        rate_target=ol.rate_target,
        rate_volatility_scale=ol.rate_volatility_scale,
    )

    # --- Layer 2: Apply vol scaling + crashes + cash flow math per simulation ---
    accum = [MonthlySnapshot() for _ in range(months)]

    # Collect per-sim values for percentile computation
    _buyer_nw = np.empty((n_sims, months))
    _renter_nw = np.empty((n_sims, months))
    _home_val = np.empty((n_sims, months))
    _buyer_eq = np.empty((n_sims, months))

    for sim in range(n_sims):
        rng_crash = np.random.default_rng(seed=10_000 + sim)

        # Start from cached paths
        stock_path = paths.stock_paths[sim].copy()
        home_path = paths.home_paths[sim].copy()
        rent_path = paths.rent_paths[sim]  # no crash/vol adjustment on rent

        # Apply volatility scaling (amplify or dampen the noise around drift)
        if vol_scale != 1.0:
            # For growth factor paths: scale the deviation from 1.0
            stock_path = 1.0 + vol_scale * (stock_path - 1.0)
            # For cumulative paths: scale log-returns around trend
            log_home = np.log(np.clip(home_path, 0.001, None))
            trend = np.linspace(log_home[0], log_home[-1], len(log_home))
            deviation = log_home - trend
            log_home_scaled = trend + vol_scale * deviation
            home_path = np.exp(log_home_scaled)

        # Apply crash overlay (extra stress on top of base + vol scaling)
        stock_path = apply_crash(
            stock_path, s_prob, s_drop,
            horizon, rng_crash, is_cumulative=False,
            drawdown_months=s_drawdown,
            recovery_pct=ol.stock_recovery_pct,
            recovery_months=ol.stock_recovery_months,
        )
        home_path = apply_crash(
            home_path, h_prob, h_drop,
            horizon, rng_crash, is_cumulative=True,
            drawdown_months=h_drawdown,
            recovery_pct=ol.housing_recovery_pct,
            recovery_months=ol.housing_recovery_months,
        )

        # Apply leverage
        if stock_leverage != 1.0:
            stock_path = 1.0 + stock_leverage * (stock_path - 1.0)

        # Mortgage schedule — use forecasted rate at purchase month if delayed
        sim_rate = mortgage_rate
        if use_forecasted_rate:
            sim_rate = paths.rate_paths[sim][buy_delay] / 100 + rate_adj / 100
        loan_amount = house_price * (1 - p.down_payment_pct)
        amort = amortize(loan_amount, sim_rate, mortgage_term)
        pmi = pmi_schedule(house_price, p.down_payment_pct, m.credit_quality, amort)

        # Home values and property tax
        home_values = house_price * home_path
        monthly_prop_tax = prop_tax_rate * home_values / 12

        # Tax savings
        tax_save = monthly_tax_savings(
            amort, monthly_prop_tax[buy_delay:buy_delay + len(amort)],
            u.filing_status, u.yearly_income, state_tax_rate, u.other_deductions,
        )

        # --- Month-by-month cash flow ---
        buyer_inv = u.initial_cash
        renter_inv = u.initial_cash
        cum_buy = 0.0
        cum_rent = 0.0
        sold = False  # tracks whether buyer has sold

        for month in range(months):
            stock_return = monthly_savings_return if savings_only else stock_path[month]
            rent = u.monthly_rent * rent_path[month]
            budget = u.monthly_budget * rent_path[month]
            hv = home_values[month]

            renter_surplus = budget - rent
            renter_inv = renter_inv * stock_return + renter_surplus
            cum_rent += rent

            # --- Phase 1: Pre-purchase (buyer = renter) ---
            if month < buy_delay:
                buyer_inv = renter_inv
                cum_buy += rent
                snap = accum[month]
                snap.home_value += hv
                snap.total_housing_cost += rent
                snap.rent += rent
                snap.budget += budget
                snap.buyer_investment += buyer_inv
                snap.renter_investment += renter_inv
                snap.buyer_net_worth += buyer_inv
                snap.renter_net_worth += renter_inv
                snap.cumulative_buy_cost += cum_buy
                snap.cumulative_rent_cost += cum_rent
                _buyer_nw[sim, month] = buyer_inv
                _renter_nw[sim, month] = renter_inv
                _home_val[sim, month] = hv
                _buyer_eq[sim, month] = 0.0
                continue

            # --- Purchase event ---
            if month == buy_delay:
                down = house_price * p.down_payment_pct
                closing = house_price * p.closing_cost_pct
                buyer_inv = buyer_inv - down - closing - p.move_in_cost

            # --- Sell event: liquidate equity, become renter ---
            if not sold and month >= sell_month:
                sold = True
                m_idx = month - buy_delay
                if m_idx < len(amort):
                    balance = amort[m_idx].remaining_balance
                else:
                    balance = 0.0
                sale_proceeds = hv * (1 - p.sell_cost_pct) - balance
                buyer_inv += sale_proceeds

            # --- Phase 3: Post-sell (buyer is renting again) ---
            if sold:
                buyer_surplus = budget - rent
                buyer_inv = buyer_inv * stock_return + buyer_surplus
                cum_buy += rent
                buyer_nw = buyer_inv

                snap = accum[month]
                snap.home_value += hv
                snap.total_housing_cost += rent
                snap.rent += rent
                snap.budget += budget
                snap.buyer_investment += buyer_inv
                snap.renter_investment += renter_inv
                snap.buyer_net_worth += buyer_nw
                snap.renter_net_worth += renter_inv
                snap.cumulative_buy_cost += cum_buy
                snap.cumulative_rent_cost += cum_rent
                _buyer_nw[sim, month] = buyer_nw
                _renter_nw[sim, month] = renter_inv
                _home_val[sim, month] = hv
                _buyer_eq[sim, month] = 0.0
                continue

            # --- Phase 2: Owning ---
            m_idx = month - buy_delay
            if m_idx < len(amort):
                row = amort[m_idx]
                mort_pmt = row.payment
                interest = row.interest
                princ = row.principal
                balance = row.remaining_balance
                pmi_amt = pmi[m_idx]
            else:
                mort_pmt = interest = princ = balance = pmi_amt = 0.0

            maint = p.maintenance_rate * hv / 12
            ptax = monthly_prop_tax[month]
            ins = (p.insurance_annual * home_path[month]) / 12
            tsave = tax_save[m_idx] if m_idx < len(tax_save) else 0.0

            total_cost = mort_pmt + maint + ptax + ins + pmi_amt - tsave
            buyer_surplus = budget - total_cost
            buyer_inv = buyer_inv * stock_return + buyer_surplus
            equity = hv * (1 - p.sell_cost_pct) - balance
            buyer_nw = equity + buyer_inv
            cum_buy += total_cost

            snap = accum[month]
            snap.home_value += hv
            snap.mortgage_payment += mort_pmt
            snap.interest_payment += interest
            snap.principal_payment += princ
            snap.remaining_balance += balance
            snap.maintenance += maint
            snap.property_tax += ptax
            snap.insurance += ins
            snap.pmi += pmi_amt
            snap.tax_savings += tsave
            snap.total_housing_cost += total_cost
            snap.rent += rent
            snap.budget += budget
            snap.buyer_investment += buyer_inv
            snap.renter_investment += renter_inv
            snap.buyer_equity += equity
            snap.buyer_net_worth += buyer_nw
            snap.renter_net_worth += renter_inv
            snap.cumulative_buy_cost += cum_buy
            snap.cumulative_rent_cost += cum_rent
            _buyer_nw[sim, month] = buyer_nw
            _renter_nw[sim, month] = renter_inv
            _home_val[sim, month] = hv
            _buyer_eq[sim, month] = equity

    # --- Average all snapshots ---
    for snap in accum:
        for field_name in snap.__dataclass_fields__:
            setattr(snap, field_name, getattr(snap, field_name) / n_sims)

    # --- Compute percentile bands ---
    def _bands(arr: np.ndarray) -> PercentileBands:
        pcts = np.percentile(arr, [10, 25, 50, 75, 90], axis=0)
        return PercentileBands(
            p10=pcts[0].tolist(),
            p25=pcts[1].tolist(),
            p50=pcts[2].tolist(),
            p75=pcts[3].tolist(),
            p90=pcts[4].tolist(),
        )

    percentiles = SimulationPercentiles(
        buyer_net_worth=_bands(_buyer_nw),
        renter_net_worth=_bands(_renter_nw),
        home_value=_bands(_home_val),
        buyer_equity=_bands(_buyer_eq),
        mortgage_rate=_bands(paths.rate_paths[:n_sims, :months]),
    )

    # --- Breakeven analysis ---
    # Sustained breakeven: the last month where buyer crosses from behind to ahead
    # and stays ahead through the end. This is "when buying durably wins."
    # Crossing count: how many times the lead changes. 0 = clear winner, 3+ = volatile.
    buyer_ahead = [accum[i].buyer_net_worth > accum[i].renter_net_worth for i in range(months)]

    # Count crossings (transitions from ahead→behind or behind→ahead)
    crossing_count = 0
    for i in range(1, months):
        if buyer_ahead[i] != buyer_ahead[i - 1]:
            crossing_count += 1

    # Sustained breakeven: scan backward to find where buyer last crossed to ahead
    breakeven_month = None
    if buyer_ahead[-1]:
        # Buyer wins at the end — find when they durably took the lead
        for i in range(months - 1, -1, -1):
            if not buyer_ahead[i]:
                breakeven_month = i + 1 if i + 1 < months else None
                break
        else:
            breakeven_month = 0  # buyer was always ahead

    # Report the effective mortgage rate (median forecasted rate if delayed)
    effective_rate = mortgage_rate
    if use_forecasted_rate:
        effective_rate = float(np.median(paths.rate_paths[:n_sims, buy_delay])) / 100 + rate_adj / 100

    return SimulationResult(
        monthly=accum,
        avg_buyer_net_worth=accum[months - 1].buyer_net_worth,
        avg_renter_net_worth=accum[months - 1].renter_net_worth,
        house_price_used=house_price,
        mortgage_rate_used=effective_rate,
        property_tax_rate=prop_tax_rate,
        breakeven_month=breakeven_month,
        crossing_count=crossing_count,
        percentiles=percentiles,
    )
