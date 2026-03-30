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
        -- Device identity (MVP: localStorage UUID, no auth)
        CREATE TABLE IF NOT EXISTS devices (
            device_id TEXT PRIMARY KEY,
            email TEXT,
            created_at REAL NOT NULL,
            last_seen_at REAL NOT NULL
        );

        -- Saved scenarios
        CREATE TABLE IF NOT EXISTS scenarios (
            id TEXT PRIMARY KEY,
            device_id TEXT NOT NULL,
            name TEXT NOT NULL,
            inputs_json TEXT NOT NULL,
            response_json TEXT,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            FOREIGN KEY (device_id) REFERENCES devices(device_id)
        );
        CREATE INDEX IF NOT EXISTS idx_scenarios_device ON scenarios(device_id);

        -- Alert configurations per scenario
        CREATE TABLE IF NOT EXISTS alerts (
            id TEXT PRIMARY KEY,
            scenario_id TEXT NOT NULL,
            device_id TEXT NOT NULL,
            alert_type TEXT NOT NULL,  -- 'threshold', 'digest', 'shift'
            enabled INTEGER NOT NULL DEFAULT 1,
            config_json TEXT,
            last_triggered_at REAL,
            created_at REAL NOT NULL,
            FOREIGN KEY (scenario_id) REFERENCES scenarios(id) ON DELETE CASCADE,
            FOREIGN KEY (device_id) REFERENCES devices(device_id)
        );
        CREATE INDEX IF NOT EXISTS idx_alerts_scenario ON alerts(scenario_id);
        CREATE INDEX IF NOT EXISTS idx_alerts_device ON alerts(device_id);

        -- Notification log (sent alerts)
        CREATE TABLE IF NOT EXISTS notification_log (
            id TEXT PRIMARY KEY,
            alert_id TEXT NOT NULL,
            scenario_id TEXT NOT NULL,
            device_id TEXT NOT NULL,
            diff_json TEXT NOT NULL,
            sent_at REAL NOT NULL,
            channel TEXT NOT NULL DEFAULT 'email',
            FOREIGN KEY (alert_id) REFERENCES alerts(id),
            FOREIGN KEY (scenario_id) REFERENCES scenarios(id)
        );
        CREATE INDEX IF NOT EXISTS idx_notif_log_device ON notification_log(device_id);

        -- Result cache (transient, shared across users)
        CREATE TABLE IF NOT EXISTS result_cache (
            cache_key TEXT PRIMARY KEY,
            data_vintage TEXT NOT NULL,
            inputs_json TEXT NOT NULL,
            summary_json TEXT,
            sensitivity_json TEXT,
            trend_json TEXT,
            zip_compare_json TEXT,
            llm_summary_json TEXT,
            created_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_cache_vintage ON result_cache(data_vintage);
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


def get_median_home_price(zip_code: str) -> Optional[float]:
    """Return the latest Zillow ZHVI (median home value) for a ZIP, or None."""
    data = get_zip_data(zip_code)
    if data and data.hist_values:
        return data.hist_values[-1]
    return None


_national_median: Optional[float] = None


def get_national_median_home_price() -> float:
    """Return the national median home price across all ZIPs. Cached."""
    global _national_median
    if _national_median is not None:
        return _national_median
    conn = get_connection()
    rows = conn.execute("SELECT monthly_values FROM zip_history").fetchall()
    conn.close()
    vals = []
    for r in rows:
        data = json.loads(r[0])
        if data:
            vals.append(data[-1]["value"])
    vals.sort()
    _national_median = vals[len(vals) // 2] if vals else 300_000.0
    return _national_median


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


# ---------------------------------------------------------------------------
# Device identity (MVP)
# ---------------------------------------------------------------------------

def ensure_device(device_id: str, email: Optional[str] = None) -> None:
    """Insert or update device record. Called on every authenticated request."""
    now = time.time()
    conn = get_connection()
    existing = conn.execute(
        "SELECT device_id FROM devices WHERE device_id = ?", (device_id,)
    ).fetchone()
    if existing:
        if email:
            conn.execute(
                "UPDATE devices SET last_seen_at = ?, email = ? WHERE device_id = ?",
                (now, email, device_id),
            )
        else:
            conn.execute(
                "UPDATE devices SET last_seen_at = ? WHERE device_id = ?",
                (now, device_id),
            )
    else:
        conn.execute(
            "INSERT INTO devices (device_id, email, created_at, last_seen_at) VALUES (?, ?, ?, ?)",
            (device_id, email, now, now),
        )
    conn.commit()
    conn.close()


def get_device_email(device_id: str) -> Optional[str]:
    """Get the email for a device, if set."""
    conn = get_connection()
    row = conn.execute(
        "SELECT email FROM devices WHERE device_id = ?", (device_id,)
    ).fetchone()
    conn.close()
    return row["email"] if row else None


# ---------------------------------------------------------------------------
# Scenarios CRUD
# ---------------------------------------------------------------------------

@dataclass
class ScenarioRow:
    id: str
    device_id: str
    name: str
    inputs_json: str
    response_json: Optional[str]
    created_at: float
    updated_at: float


def save_scenario(scenario: ScenarioRow) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO scenarios (id, device_id, name, inputs_json, response_json, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (scenario.id, scenario.device_id, scenario.name, scenario.inputs_json,
         scenario.response_json, scenario.created_at, scenario.updated_at),
    )
    conn.commit()
    conn.close()


def get_scenarios_for_device(device_id: str) -> list[ScenarioRow]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM scenarios WHERE device_id = ? ORDER BY updated_at DESC",
        (device_id,),
    ).fetchall()
    conn.close()
    return [ScenarioRow(**dict(r)) for r in rows]


def get_scenario(scenario_id: str) -> Optional[ScenarioRow]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM scenarios WHERE id = ?", (scenario_id,)
    ).fetchone()
    conn.close()
    return ScenarioRow(**dict(row)) if row else None


def delete_scenario(scenario_id: str) -> bool:
    conn = get_connection()
    # Cascade deletes alerts via FK, but SQLite needs PRAGMA foreign_keys=ON
    conn.execute("PRAGMA foreign_keys=ON")
    cur = conn.execute("DELETE FROM scenarios WHERE id = ?", (scenario_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def update_scenario_response(scenario_id: str, response_json: str) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE scenarios SET response_json = ?, updated_at = ? WHERE id = ?",
        (response_json, time.time(), scenario_id),
    )
    conn.commit()
    conn.close()


def get_all_scenarios_with_alerts() -> list[ScenarioRow]:
    """Get all scenarios that have at least one enabled alert. Used by post-refresh hook."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT s.* FROM scenarios s "
        "JOIN alerts a ON a.scenario_id = s.id "
        "WHERE a.enabled = 1"
    ).fetchall()
    conn.close()
    return [ScenarioRow(**dict(r)) for r in rows]


# ---------------------------------------------------------------------------
# Alerts CRUD
# ---------------------------------------------------------------------------

@dataclass
class AlertRow:
    id: str
    scenario_id: str
    device_id: str
    alert_type: str  # 'threshold', 'digest', 'shift'
    enabled: int
    config_json: Optional[str]
    last_triggered_at: Optional[float]
    created_at: float


def save_alert(alert: AlertRow) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO alerts (id, scenario_id, device_id, alert_type, enabled, config_json, last_triggered_at, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (alert.id, alert.scenario_id, alert.device_id, alert.alert_type,
         alert.enabled, alert.config_json, alert.last_triggered_at, alert.created_at),
    )
    conn.commit()
    conn.close()


def get_alerts_for_scenario(scenario_id: str) -> list[AlertRow]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM alerts WHERE scenario_id = ?", (scenario_id,)
    ).fetchall()
    conn.close()
    return [AlertRow(**dict(r)) for r in rows]


def delete_alerts_for_scenario(scenario_id: str) -> int:
    conn = get_connection()
    cur = conn.execute("DELETE FROM alerts WHERE scenario_id = ?", (scenario_id,))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    return deleted


def delete_alert(alert_id: str) -> bool:
    conn = get_connection()
    cur = conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def update_alert_triggered(alert_id: str) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE alerts SET last_triggered_at = ? WHERE id = ?",
        (time.time(), alert_id),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Notification log
# ---------------------------------------------------------------------------

def log_notification(notif_id: str, alert_id: str, scenario_id: str,
                     device_id: str, diff_json: str, channel: str = "email") -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO notification_log (id, alert_id, scenario_id, device_id, diff_json, sent_at, channel) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (notif_id, alert_id, scenario_id, device_id, diff_json, time.time(), channel),
    )
    conn.commit()
    conn.close()
