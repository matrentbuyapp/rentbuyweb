"""Persistent data store backed by SQLite.

Provides fast indexed lookups for ZIP-level housing data and tax rates,
with an in-memory LRU cache for hot queries. Data is refreshed by a
separate scheduled job (refresh_data.py), never during a request.

Schema:
  zip_history  — monthly home values per ZIP (last 72 months)
  zip_forecast — monthly growth forecasts per ZIP
  zip_meta     — region metadata (city, state, metro, etc.)
  geo_lookup   — ZIP → county/state mapping
  tax_rates    — property tax rates by county and state
  data_meta    — tracks when each data source was last refreshed
"""

import os
import sqlite3
import json
import time
import numpy as np
from functools import lru_cache
from typing import Optional
from dataclasses import dataclass
from pathlib import Path

DB_PATH = os.environ.get(
    "MORTGAGE_DB_PATH",
    os.path.join(os.path.dirname(__file__), "data", "market.db"),
)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # concurrent reads during writes
    conn.execute("PRAGMA cache_size=-20000")  # 20 MB page cache
    return conn


def init_db():
    """Create tables if they don't exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS zip_history (
            zip_code TEXT PRIMARY KEY,
            state TEXT,
            city TEXT,
            metro TEXT,
            -- JSON array of {date: value} pairs, last 72 months
            monthly_values TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS zip_forecast (
            zip_code TEXT PRIMARY KEY,
            state TEXT,
            -- JSON array of {date: pct_change} pairs
            monthly_forecasts TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS geo_lookup (
            zip_code TEXT PRIMARY KEY,
            county TEXT,
            state TEXT
        );

        CREATE TABLE IF NOT EXISTS tax_rates (
            -- county-level key: "county|state", state-level key: "|state"
            key TEXT PRIMARY KEY,
            rate REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS data_meta (
            source TEXT PRIMARY KEY,
            last_refreshed REAL,  -- unix timestamp
            row_count INTEGER,
            notes TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_zip_hist_state ON zip_history(state);
        CREATE INDEX IF NOT EXISTS idx_zip_fcst_state ON zip_forecast(state);
        CREATE INDEX IF NOT EXISTS idx_geo_state ON geo_lookup(state);
    """)
    conn.close()


# ---------------------------------------------------------------------------
# Querying (used at request time)
# ---------------------------------------------------------------------------

@dataclass
class ZipData:
    zip_code: str
    state: Optional[str]
    city: Optional[str]
    # Ordered arrays: dates and values
    hist_dates: list[str]
    hist_values: list[float]
    fcst_dates: list[str]
    fcst_changes: list[float]


@lru_cache(maxsize=2048)
def get_zip_data(zip_code: str) -> Optional[ZipData]:
    """Fetch historical + forecast data for a single ZIP. LRU cached."""
    zip_code = str(zip_code).zfill(5)
    conn = get_connection()

    hist_row = conn.execute(
        "SELECT * FROM zip_history WHERE zip_code = ?", (zip_code,)
    ).fetchone()

    fcst_row = conn.execute(
        "SELECT * FROM zip_forecast WHERE zip_code = ?", (zip_code,)
    ).fetchone()

    conn.close()

    if not hist_row:
        return None

    hist_data = json.loads(hist_row["monthly_values"])
    hist_dates = [d["date"] for d in hist_data]
    hist_values = [d["value"] for d in hist_data]

    fcst_dates, fcst_changes = [], []
    if fcst_row:
        fcst_data = json.loads(fcst_row["monthly_forecasts"])
        fcst_dates = [d["date"] for d in fcst_data]
        fcst_changes = [d["change"] for d in fcst_data]

    return ZipData(
        zip_code=zip_code,
        state=hist_row["state"],
        city=hist_row["city"],
        hist_dates=hist_dates,
        hist_values=hist_values,
        fcst_dates=fcst_dates,
        fcst_changes=fcst_changes,
    )


def get_zip_growth_index(zip_code: str, n_months: int = 180) -> Optional[np.ndarray]:
    """Build a cumulative growth index for a ZIP code.

    Blends historical price trend with forecast, returns array of length n_months
    starting at 1.0.
    """
    data = get_zip_data(zip_code)
    if not data or len(data.hist_values) < 2:
        return None

    # Historical: convert prices to cumulative index
    prices = np.array(data.hist_values)
    hist_growth = prices / prices[0]

    # Forecast: chain percentage changes
    if data.fcst_changes:
        fcst_index = [hist_growth[-1]]
        for pct in data.fcst_changes:
            fcst_index.append(fcst_index[-1] * (1 + pct / 100.0))
        combined = np.concatenate([hist_growth, np.array(fcst_index[1:])])
    else:
        combined = hist_growth

    # Interpolate to exactly n_months
    if len(combined) < 2:
        return None

    from scipy.interpolate import CubicSpline
    x = np.linspace(0, 1, len(combined))
    x_out = np.linspace(0, 1, n_months)
    cs = CubicSpline(x, combined, extrapolate=True)
    result = cs(x_out)

    # Normalize to start at 1.0
    result = result / result[0]
    return np.maximum(result, 0.1)  # floor at 10% to prevent negatives


def _normalize_county(name: str) -> str:
    """Normalize county name for matching: lowercase, strip suffixes."""
    return (name.strip().lower()
            .replace(" county", "").replace(" parish", "")
            .replace(" borough", "").replace(" census area", "")
            .replace(" municipality", "").replace(" city and", "")
            .replace(".", "").replace("'", ""))


@lru_cache(maxsize=4096)
def get_property_tax_rate_cached(zip_code: str) -> float:
    """Look up property tax rate for a ZIP. Falls back county → state → national avg.

    Keys in tax_rates use state FIPS codes (matching geo_lookup) for unambiguous matching.
    Format: county level = "county_name|state_fips", state level = "|state_fips".
    """
    zip_code = str(zip_code).zfill(5)
    conn = get_connection()

    geo = conn.execute(
        "SELECT county, state FROM geo_lookup WHERE zip_code = ?", (zip_code,)
    ).fetchone()

    if not geo:
        conn.close()
        return 0.009

    county = _normalize_county(geo["county"])
    state_fips = geo["state"].strip()

    # Try county level (key = "county_name|state_fips")
    county_key = f"{county}|{state_fips}"
    row = conn.execute(
        "SELECT rate FROM tax_rates WHERE key = ?", (county_key,)
    ).fetchone()
    if row:
        conn.close()
        return row["rate"]

    # Try state level (key = "|state_fips")
    state_key = f"|{state_fips}"
    row = conn.execute(
        "SELECT rate FROM tax_rates WHERE key = ?", (state_key,)
    ).fetchone()
    conn.close()

    if row:
        return row["rate"]

    return 0.009  # national average


def get_last_refresh(source: str) -> Optional[float]:
    """When was a data source last refreshed? Returns unix timestamp or None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT last_refreshed FROM data_meta WHERE source = ?", (source,)
    ).fetchone()
    conn.close()
    return row["last_refreshed"] if row else None


def invalidate_zip_cache():
    """Clear the LRU caches after a data refresh."""
    get_zip_data.cache_clear()
    get_property_tax_rate_cached.cache_clear()
