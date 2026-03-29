"""Market data loading and stochastic path generation for Monte Carlo simulation."""

import os
import json
import time
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.interpolate import CubicSpline
from typing import Optional
from dataclasses import dataclass

# Data directory: check local api/data/ first, fall back to rent-buy-api/data/,
# or override with DATA_DIR env var.
_API_DATA = os.path.join(os.path.dirname(__file__), "data")
_LEGACY_DATA = os.path.join(os.path.dirname(__file__), "..", "rent-buy-api", "data")
DATA_DIR = os.environ.get("MORTGAGE_DATA_DIR", _API_DATA if os.path.isdir(_API_DATA) else _LEGACY_DATA)

# In-memory cache for HistoricalData — loaded once per process.
_cached_data: Optional["HistoricalData"] = None
_cached_at: float = 0.0
CACHE_TTL_SECONDS = 24 * 3600  # reload data at most once per day


# ---------------------------------------------------------------------------
# Data loading (deterministic — called once at startup)
# ---------------------------------------------------------------------------

@dataclass
class HistoricalData:
    """Pre-loaded macro market data used as drift/center for MC paths.

    ZIP-level data and tax lookups live in SQLite via data_store module —
    not loaded into memory here.
    """
    cpi_monthly_growth: np.ndarray       # month-over-month CPI growth factors
    stock_monthly_growth: np.ndarray     # month-over-month stock (DOW) growth factors
    hpi_cumulative: np.ndarray           # cumulative home price index (base=1.0)
    mortgage_rates: np.ndarray           # monthly mortgage rate levels (percent)


def _interpolate_quarterly_to_monthly(values: np.ndarray, n_months: int) -> np.ndarray:
    """Cubic spline interpolation from quarterly data points to monthly."""
    x_quarterly = np.arange(len(values)) * 3
    x_monthly = np.linspace(0, x_quarterly[-1], n_months)
    spline = CubicSpline(x_quarterly, values, extrapolate=True)
    result = spline(x_monthly)
    # Fill any NaN from extrapolation
    mask = np.isnan(result)
    if mask.any():
        result[mask] = result[~mask][-1]
    return result


def _load_csv_column(filename: str) -> np.ndarray:
    """Load a single-column CSV of quarterly values."""
    path = os.path.join(DATA_DIR, filename)
    values = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    values.append(float(line))
                except ValueError:
                    continue  # skip header
    return np.array(values)


def _to_mom_growth(levels: np.ndarray) -> np.ndarray:
    """Convert level series to month-over-month growth factors [1.0, g1, g2, ...]."""
    growth = np.ones(len(levels))
    growth[1:] = levels[1:] / levels[:-1]
    return growth


def _to_cumulative(levels: np.ndarray) -> np.ndarray:
    """Convert level series to cumulative index starting at 1.0."""
    return levels / levels[0]


def load_historical_data(n_months: int = 180) -> HistoricalData:
    """Load and interpolate macro market series from quarterly CSVs.

    Only loads small FRED-sourced files (~2 KB each). ZIP-level data
    and tax rates are served from SQLite via data_store module.

    Args:
        n_months: Number of monthly data points to produce (default 180 = 15 years).
    """
    cpi_raw = _load_csv_column("cpi.csv")
    cpi_monthly = _interpolate_quarterly_to_monthly(cpi_raw, n_months)
    cpi_growth = _to_mom_growth(cpi_monthly)

    dow_raw = _load_csv_column("dow.csv")
    dow_monthly = _interpolate_quarterly_to_monthly(dow_raw, n_months)
    stock_growth = _to_mom_growth(dow_monthly)

    hpi_raw = _load_csv_column("hpi.csv")
    hpi_monthly = _interpolate_quarterly_to_monthly(hpi_raw, n_months)
    hpi_cumulative = _to_cumulative(hpi_monthly)

    mort_raw = _load_csv_column("mort.csv")
    mort_monthly = _interpolate_quarterly_to_monthly(mort_raw, n_months)

    return HistoricalData(
        cpi_monthly_growth=cpi_growth,
        stock_monthly_growth=stock_growth,
        hpi_cumulative=hpi_cumulative,
        mortgage_rates=mort_monthly,
    )


def get_data(n_months: int = 180) -> HistoricalData:
    """Get historical data with in-memory caching.

    Loads once per process, reloads if older than CACHE_TTL_SECONDS.
    Use this in the API instead of calling load_historical_data() directly.
    """
    global _cached_data, _cached_at
    now = time.time()
    if _cached_data is None or (now - _cached_at) > CACHE_TTL_SECONDS:
        _cached_data = load_historical_data(n_months)
        _cached_at = now
    return _cached_data


# ---------------------------------------------------------------------------
# Property tax + state tax lookups
# ---------------------------------------------------------------------------
# These delegate to data_store (SQLite + LRU cache) for fast lookups.
# Kept here as thin wrappers so the simulator doesn't import data_store directly.

_STATE_INCOME_TAX = {
    "CA": 0.06, "NY": 0.058, "NJ": 0.055, "IL": 0.0495, "PA": 0.0307,
    "GA": 0.0575, "MI": 0.0425, "UT": 0.0455, "IA": 0.038,
    "AK": 0.0, "FL": 0.0, "NV": 0.0, "NH": 0.0, "SD": 0.0,
    "TN": 0.0, "TX": 0.0, "WA": 0.0, "WY": 0.0,
    "AL": 0.04, "AZ": 0.025, "AR": 0.03, "CO": 0.044,
    "CT": 0.0699, "DE": 0.066, "HI": 0.08, "ID": 0.058,
    "IN": 0.0323, "KS": 0.05, "KY": 0.045, "LA": 0.0485,
    "ME": 0.065, "MD": 0.055, "MA": 0.05, "MN": 0.08,
    "MS": 0.04, "MO": 0.0495, "MT": 0.0675, "NE": 0.0664,
    "NM": 0.059, "NC": 0.0425, "ND": 0.025, "OH": 0.035,
    "OK": 0.045, "OR": 0.09, "RI": 0.0599, "SC": 0.05,
    "VT": 0.075, "VA": 0.0575, "WV": 0.0455, "WI": 0.053, "DC": 0.055,
}


def get_property_tax_rate(zip_code: str) -> float:
    """Look up property tax rate for a ZIP. Uses SQLite + LRU cache."""
    if not zip_code:
        return 0.009
    try:
        from data_store import get_property_tax_rate_cached
        return get_property_tax_rate_cached(zip_code)
    except Exception:
        return 0.009


def get_state_tax_rate(zip_code: str) -> float:
    """Get effective state income tax rate from ZIP code."""
    if not zip_code:
        return 0.03
    try:
        from data_store import get_zip_data
        data = get_zip_data(zip_code)
        if data and data.state:
            return _STATE_INCOME_TAX.get(data.state, 0.03)
    except Exception:
        pass
    return 0.03


# ---------------------------------------------------------------------------
# Mortgage rate forecasting
# ---------------------------------------------------------------------------

def _compute_rate_stats(mort_rates: np.ndarray) -> dict:
    """Compute rate statistics from the full historical monthly series.

    Returns dict with current rate, recent trend, and long-term mean.
    All rates in percent (e.g., 6.5 = 6.5%).
    """
    current = mort_rates[-1]

    # 9-month momentum: captures recent direction without excess noise.
    # Shorter than a full cycle so it doesn't wash out a clear trend reversal.
    lookback = min(9, len(mort_rates) - 1)
    trend = (mort_rates[-1] - mort_rates[-1 - lookback]) / lookback  # pct pts per month

    # 5-year average (or as much as we have)
    avg_5y = mort_rates[-min(60, len(mort_rates)):].mean()

    # 20-year average (long-term anchor for mean reversion)
    avg_20y = mort_rates[-min(240, len(mort_rates)):].mean()

    # Historical monthly volatility (standard deviation of month-to-month changes)
    diffs = np.diff(mort_rates[-min(120, len(mort_rates)):])
    monthly_vol = diffs.std()

    return {
        "current": current,
        "trend_per_month": trend,
        "avg_5y": avg_5y,
        "avg_20y": avg_20y,
        "monthly_vol": monthly_vol,
    }


def generate_rate_path(
    mort_rates: np.ndarray,
    n_months: int,
    rng: np.random.Generator,
    rate_target: float | None = None,
    rate_volatility_scale: float = 1.0,
) -> np.ndarray:
    """Generate a stochastic mortgage rate path (in percent, e.g. 6.5 = 6.5%).

    Three-regime forecast:
      1. Short-term (months 0-24): Extrapolate 2-year momentum with exponential decay.
         Market has inertia — if rates have been falling, they tend to keep falling
         for a while. Decay half-life = 12 months.
      2. Medium-term (months 24-60): Blend from decayed trend toward 5-year average.
         Represents the economy normalizing toward its recent equilibrium.
      3. Long-term (months 60+): Ornstein-Uhlenbeck mean reversion to 20-year average.
         Over long horizons, rates revert to structural levels.

    At all times, calibrated noise is added (from historical month-to-month volatility).
    Rates are floored at 1.0% and capped at 15.0%.

    Works for any forecast horizon — no hardcoded term dependency.
    """
    stats = _compute_rate_stats(mort_rates)
    current = stats["current"]
    trend = stats["trend_per_month"]
    avg_5y = stats["avg_5y"]
    avg_20y = stats["avg_20y"]
    vol = stats["monthly_vol"] * rate_volatility_scale

    # Pro override: custom target rate replaces the 20-year avg as mean-reversion anchor
    if rate_target is not None:
        avg_20y = rate_target * 100  # convert decimal to percent to match internal units
        avg_5y = (avg_5y + avg_20y) / 2  # blend medium-term toward target too

    # Mean-reversion speed (Ornstein-Uhlenbeck kappa).
    # Half-life of ~5 years = 60 months → kappa = ln(2)/60 ≈ 0.0116
    kappa = np.log(2) / 60

    # Trend decay half-life: 12 months
    trend_decay = np.log(2) / 12

    path = np.empty(n_months)
    rate = current
    noise = rng.normal(0, vol, n_months)

    for m in range(n_months):
        if m < 24:
            # Phase 1: decaying trend + noise
            decayed_trend = trend * np.exp(-trend_decay * m)
            drift = decayed_trend
        elif m < 60:
            # Phase 2: blend from trend toward 5-year avg
            blend = (m - 24) / 36  # 0 at month 24, 1 at month 60
            trend_pull = trend * np.exp(-trend_decay * m)
            mean_pull = kappa * (avg_5y - rate)
            drift = (1 - blend) * trend_pull + blend * mean_pull
        else:
            # Phase 3: pure mean-reversion to 20-year average
            drift = kappa * (avg_20y - rate)

        rate = rate + drift + noise[m]
        rate = np.clip(rate, 1.0, 15.0)
        path[m] = rate

    return path


# ---------------------------------------------------------------------------
# Stochastic path generation (the actual Monte Carlo)
# ---------------------------------------------------------------------------

def generate_stock_path(
    hist_growth: np.ndarray,
    n_months: int,
    rng: np.random.Generator,
    annual_vol: float = 0.15,
) -> np.ndarray:
    """Generate a random stock return path.

    Uses historical month-over-month growth as the drift (expected return),
    then adds log-normal noise around it.

    Returns: array of monthly growth factors (e.g., 1.005 = +0.5% that month).
    """
    # Convert historical growth factors to log returns for the drift
    hist_log = np.log(np.clip(hist_growth[:n_months], 0.001, None))
    monthly_vol = annual_vol / np.sqrt(12)

    noise = rng.normal(0, monthly_vol, n_months)
    log_returns = hist_log + noise
    return np.exp(log_returns)


def generate_home_appreciation_path(
    hist_cumulative: np.ndarray,
    zip_cumulative: Optional[np.ndarray],
    n_months: int,
    rng: np.random.Generator,
    annual_vol: float = 0.06,
) -> np.ndarray:
    """Generate a random home value path as a cumulative index (starting at 1.0).

    If ZIP-level forecast is available, blends it with national HPI.
    Adds noise per simulation to create spread.
    """
    # Use ZIP forecast if available, blend with national HPI
    if zip_cumulative is not None:
        min_len = min(len(zip_cumulative), len(hist_cumulative), n_months)
        base = (zip_cumulative[:min_len] + hist_cumulative[:min_len]) / 2
    else:
        base = hist_cumulative[:n_months]

    # Pad if needed
    if len(base) < n_months:
        last_growth = base[-1] / base[-2] if len(base) > 1 else 1.0
        extra = np.full(n_months - len(base), base[-1])
        for i in range(len(extra)):
            extra[i] = base[-1] * (last_growth ** (i + 1))
        base = np.concatenate([base, extra])

    # Convert to log returns, add noise, reconstruct cumulative
    log_returns = np.diff(np.log(np.clip(base[:n_months], 0.001, None)))
    monthly_vol = annual_vol / np.sqrt(12)
    noise = rng.normal(0, monthly_vol, len(log_returns))

    noisy_log_returns = log_returns + noise
    cumulative = np.ones(n_months)
    cumulative[1:] = np.exp(np.cumsum(noisy_log_returns))

    return cumulative


def generate_rent_path(
    hist_growth: np.ndarray,
    n_months: int,
    rng: np.random.Generator,
    annual_vol: float = 0.02,
) -> np.ndarray:
    """Generate a cumulative rent inflation path.

    Uses CPI growth as drift with small noise.
    Returns cumulative multiplier (starts at 1.0).
    """
    hist_log = np.log(np.clip(hist_growth[:n_months], 0.001, None))
    monthly_vol = annual_vol / np.sqrt(12)
    noise = rng.normal(0, monthly_vol, n_months)

    log_returns = hist_log + noise
    # First month: no inflation yet
    log_returns[0] = 0.0
    return np.exp(np.cumsum(log_returns))


def apply_crash(
    path: np.ndarray,
    crash_prob: float,
    crash_magnitude: float,
    horizon_months: int,
    rng: np.random.Generator,
    is_cumulative: bool = False,
    drawdown_months: int = 6,
    recovery_pct: float = 0.5,
    recovery_months: int = 60,
) -> np.ndarray:
    """Apply a crash with partial recovery on top of the base MC path.

    Three phases:
      1. Drawdown: prices drop over drawdown_months (gradual decline)
      2. Recovery: exponential recovery toward pre-crash level, recovering
         recovery_pct of the gap over recovery_months
      3. Residual: whatever gap remains is permanent (structural damage)

    Default: 50% recovery over 60 months (housing) or 70% over 36 months (stocks).
    recovery_pct=0 gives the old permanent-shift behavior.
    recovery_pct=1 gives a full V-shaped recovery.

    Args:
        crash_prob: Probability of crash occurring within horizon.
        crash_magnitude: Total drop (e.g., 0.20 = 20% decline).
        horizon_months: Window in which crash can start.
        is_cumulative: True for cumulative paths (housing), False for growth factors (stocks).
        drawdown_months: Months over which the drop happens.
        recovery_pct: Fraction of the crash gap that recovers (0=permanent, 1=full).
        recovery_months: Months over which recovery_pct of the gap is recovered.
    """
    if crash_prob <= 0 or crash_magnitude <= 0:
        return path

    result = path.copy()
    n = len(result)

    if rng.random() >= crash_prob:
        return result

    crash_start = rng.integers(0, min(horizon_months, n))
    recovery_start = crash_start + drawdown_months

    # Recovery rate: exponential decay of the gap.
    # After recovery_months, the gap is reduced by recovery_pct.
    # gap(t) = magnitude * (permanent_share + recoverable_share * exp(-lambda * t))
    # where permanent_share = 1 - recovery_pct, recoverable_share = recovery_pct
    # lambda = -ln(1 - recovery_pct) / recovery_months
    if recovery_pct >= 1.0:
        # Full recovery: use a fast decay that reaches ~99% recovery in recovery_months
        lam = np.log(100) / max(recovery_months, 1)  # exp(-lam*T) ≈ 0.01
    elif recovery_pct > 0 and recovery_months > 0:
        lam = -np.log(1 - recovery_pct) / recovery_months
    else:
        lam = 0  # no recovery

    permanent_floor = 1.0 - crash_magnitude * max(0, 1 - recovery_pct)

    envelope = np.ones(n)
    for i in range(crash_start, n):
        months_in = i - crash_start
        if months_in < drawdown_months:
            # Phase 1: gradual decline
            progress = (months_in + 1) / drawdown_months
            envelope[i] = 1.0 - crash_magnitude * progress
        else:
            # Phase 2+3: recovery from trough toward permanent_floor
            months_recovering = i - recovery_start
            if lam > 0:
                # Exponential recovery: trough → partial recovery
                remaining_gap = crash_magnitude * recovery_pct * np.exp(-lam * months_recovering)
                envelope[i] = permanent_floor - remaining_gap + crash_magnitude * recovery_pct
                # Simplified: envelope = 1 - magnitude*(1-recovery_pct) - magnitude*recovery_pct*exp(-lam*t)
                #           = 1 - magnitude * ((1-recovery_pct) + recovery_pct * exp(-lam*t))
                envelope[i] = 1.0 - crash_magnitude * ((1 - recovery_pct) + recovery_pct * np.exp(-lam * months_recovering))
            else:
                envelope[i] = 1.0 - crash_magnitude  # permanent shift (old behavior)

    if is_cumulative:
        result *= envelope
    else:
        # Convert envelope to month-over-month adjustments for growth factor paths
        envelope_growth = np.ones(n)
        for i in range(crash_start, n):
            if i == crash_start:
                envelope_growth[i] = envelope[i]
            else:
                envelope_growth[i] = envelope[i] / envelope[i - 1]
        result *= envelope_growth

    return result
