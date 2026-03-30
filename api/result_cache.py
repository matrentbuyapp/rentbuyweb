"""Result caching layer for simulation outputs.

Deterministic simulations with the same inputs + data vintage produce the same
results. This module caches those results to avoid redundant MC runs.

Cache key = SHA-256(canonical_inputs_json + data_vintage).
Each endpoint's result is stored in a separate column, populated lazily.

Storage: SQLite locally, swappable to DynamoDB+S3 via StorageBackend protocol.
"""

import hashlib
import json
import time
from typing import Optional, Protocol
from dataclasses import dataclass

from data_store import get_connection, init_db


# ---------------------------------------------------------------------------
# Data vintage — when was the underlying market data last refreshed?
# ---------------------------------------------------------------------------

_cached_vintage: Optional[str] = None
_cached_vintage_at: float = 0


def get_data_vintage() -> str:
    """Return ISO date of the most recent data refresh. Cached for 60s."""
    global _cached_vintage, _cached_vintage_at
    now = time.time()
    if _cached_vintage and (now - _cached_vintage_at) < 60:
        return _cached_vintage

    conn = get_connection()
    rows = conn.execute("SELECT MAX(last_refreshed) as latest FROM data_meta").fetchone()
    conn.close()

    if rows and rows["latest"]:
        _cached_vintage = time.strftime("%Y-%m-%d", time.localtime(rows["latest"]))
    else:
        _cached_vintage = "unknown"
    _cached_vintage_at = now
    return _cached_vintage


def invalidate_vintage_cache():
    """Call after data refresh to force re-read of vintage."""
    global _cached_vintage, _cached_vintage_at
    _cached_vintage = None
    _cached_vintage_at = 0


# ---------------------------------------------------------------------------
# Canonical input normalization + cache key
# ---------------------------------------------------------------------------

# Fields that match these defaults are stripped before hashing (reduces key sensitivity)
_DEFAULTS = {
    "initial_cash": 150000,
    "yearly_income": 0,
    "filing_status": "single",
    "other_deductions": 0,
    "risk_appetite": "moderate",
    "zip_code": None,
    "house_price": None,
    "down_payment_pct": 0.10,
    "closing_cost_pct": 0.03,
    "maintenance_rate": 0.01,
    "insurance_annual": 0,
    "sell_cost_pct": 0.06,
    "move_in_cost": 0,
    "mortgage_rate": None,
    "term_years": 30,
    "credit_quality": "good",
    "years": 10,
    "stay_years": None,
    "num_simulations": 500,
    "buy_delay_months": 0,
    "outlook_preset": "historical",
    "volatility_scale": None,
    "housing_crash_prob": None,
    "housing_crash_drop": None,
    "housing_drawdown_months": None,
    "stock_crash_prob": None,
    "stock_crash_drop": None,
    "stock_drawdown_months": None,
    "housing_recovery_pct": None,
    "housing_recovery_months": None,
    "stock_recovery_pct": None,
    "stock_recovery_months": None,
    "rate_target": None,
    "rate_volatility_scale": None,
}


def canonical_inputs(request_dict: dict) -> str:
    """Normalize a request dict to a canonical JSON string for hashing.

    - Strips keys that match defaults (reduces false misses from absent vs default)
    - Rounds floats to 6 decimal places
    - Sorts keys
    - Strips null values
    """
    cleaned = {}
    for k, v in request_dict.items():
        # Skip nulls
        if v is None:
            continue
        # Skip values matching defaults
        if k in _DEFAULTS and v == _DEFAULTS[k]:
            continue
        # Round floats
        if isinstance(v, float):
            v = round(v, 6)
        cleaned[k] = v

    return json.dumps(cleaned, sort_keys=True, separators=(",", ":"))


def compute_cache_key(request_dict: dict, data_vintage: str) -> str:
    """SHA-256 of canonical inputs + data vintage."""
    canonical = canonical_inputs(request_dict)
    payload = f"{canonical}|{data_vintage}"
    return hashlib.sha256(payload.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Cache table schema
# ---------------------------------------------------------------------------

# Table is created by init_db() in data_store.py.


# ---------------------------------------------------------------------------
# Cache operations
# ---------------------------------------------------------------------------

@dataclass
class CacheEntry:
    cache_key: str
    data_vintage: str
    inputs_json: str
    summary_json: Optional[str] = None
    sensitivity_json: Optional[str] = None
    trend_json: Optional[str] = None
    zip_compare_json: Optional[str] = None
    llm_summary_json: Optional[str] = None
    created_at: float = 0


def get_cache_entry(cache_key: str) -> Optional[CacheEntry]:
    """Fetch a cache entry by key. Returns None on miss."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM result_cache WHERE cache_key = ?", (cache_key,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return CacheEntry(
        cache_key=row["cache_key"],
        data_vintage=row["data_vintage"],
        inputs_json=row["inputs_json"],
        summary_json=row["summary_json"],
        sensitivity_json=row["sensitivity_json"],
        trend_json=row["trend_json"],
        zip_compare_json=row["zip_compare_json"],
        llm_summary_json=row["llm_summary_json"],
        created_at=row["created_at"],
    )


def create_cache_entry(cache_key: str, data_vintage: str, inputs_json: str):
    """Create a new cache entry (columns start null, populated lazily)."""
    conn = get_connection()
    conn.execute(
        """INSERT OR IGNORE INTO result_cache
           (cache_key, data_vintage, inputs_json, created_at)
           VALUES (?, ?, ?, ?)""",
        (cache_key, data_vintage, inputs_json, time.time()),
    )
    conn.commit()
    conn.close()


def update_cache_column(cache_key: str, column: str, value: str):
    """Update a single result column in an existing cache entry."""
    allowed = {"summary_json", "sensitivity_json", "trend_json",
               "zip_compare_json", "llm_summary_json"}
    if column not in allowed:
        raise ValueError(f"Invalid cache column: {column}")
    conn = get_connection()
    conn.execute(
        f"UPDATE result_cache SET {column} = ? WHERE cache_key = ?",
        (value, cache_key),
    )
    conn.commit()
    conn.close()


def prune_cache(max_age_days: int = 90):
    """Delete cache entries older than max_age_days that aren't referenced by a scenario.

    Scenarios reference cache entries by storing the same inputs_json. We check
    by cache_key presence — if a scenario's inputs hash to a cache_key, keep it.
    """
    cutoff = time.time() - (max_age_days * 86400)
    conn = get_connection()
    conn.execute(
        "DELETE FROM result_cache WHERE created_at < ? AND cache_key NOT IN "
        "(SELECT DISTINCT cache_key FROM result_cache rc "
        " INNER JOIN scenarios s ON rc.inputs_json = s.inputs_json)",
        (cutoff,),
    )
    deleted = conn.total_changes
    conn.commit()
    conn.close()
    return deleted
