"""Data refresh script — downloads fresh data and rebuilds the SQLite store.

Run on a schedule (cron, ECS scheduled task, Lambda, etc.):
  - Zillow: monthly (updates ~3rd week of month)
  - FRED: weekly (mortgage rates update Thursdays)

Safe to run while the API is serving — SQLite WAL mode allows concurrent reads.
After refresh, the API picks up new data on next cache miss (LRU eviction)
or after process restart.

Usage:
    python refresh_data.py              # refresh everything
    python refresh_data.py --fred-only  # just FRED macro data
    python refresh_data.py --zillow-only # just Zillow ZIP data
"""

import os
import sys
import json
import time
import sqlite3
import pandas as pd
import numpy as np
import requests
from io import StringIO
from pathlib import Path

from data_store import DB_PATH, get_connection, init_db, invalidate_zip_cache

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# FRED (small, fast)
# ---------------------------------------------------------------------------

def fetch_fred_series(series_id: str, start: str = "2000-01-01") -> pd.DataFrame:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd={start}"
    print(f"  Fetching {series_id}...")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    df = pd.read_csv(StringIO(resp.text))
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna()


def refresh_fred():
    print("=== Refreshing FRED data ===")
    series_map = {
        "CPIAUCSL": "cpi.csv",
        "SP500": "dow.csv",
        "CSUSHPINSA": "hpi.csv",
        "MORTGAGE30US": "mort.csv",
    }

    for series_id, filename in series_map.items():
        df = fetch_fred_series(series_id)
        quarterly = df.set_index("date")["value"].resample("QS").mean().dropna()
        path = os.path.join(DATA_DIR, filename)
        quarterly.to_csv(path, index=False, header=False)
        print(f"  Saved {filename}: {len(quarterly)} quarters")

    # Record refresh time
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO data_meta (source, last_refreshed, notes) VALUES (?, ?, ?)",
        ("fred", time.time(), "CPI, SP500, HPI, MORT30"),
    )
    conn.commit()
    conn.close()
    print("  Done.\n")


# ---------------------------------------------------------------------------
# Zillow → SQLite (large, monthly)
# ---------------------------------------------------------------------------

ZILLOW_HISTORY_URL = "https://files.zillowstatic.com/research/public_csvs/zhvi/Zip_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
ZILLOW_FORECAST_URL = "https://files.zillowstatic.com/research/public_csvs/zhvf_growth/Zip_zhvf_growth_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
HIST_MONTHS_TO_KEEP = 72


def refresh_zillow():
    print("=== Refreshing Zillow data ===")
    conn = get_connection()

    # --- History ---
    # Use local file if it exists (avoid re-downloading 115 MB)
    local_hist = os.path.join(DATA_DIR, "Zhistory.csv")
    if os.path.exists(local_hist):
        print(f"  Loading ZHVI history from local file ({HIST_MONTHS_TO_KEEP} months)...")
        df = pd.read_csv(local_hist, dtype={"RegionName": str})
    else:
        print(f"  Downloading ZHVI history ({HIST_MONTHS_TO_KEEP} months)...")
        resp = requests.get(ZILLOW_HISTORY_URL, timeout=180)
        resp.raise_for_status()
        df = pd.read_csv(StringIO(resp.text), dtype={"RegionName": str})

    # Identify date columns (everything after the metadata columns)
    meta_cols = ["RegionID", "SizeRank", "RegionName", "RegionType", "StateName",
                 "State", "City", "Metro", "CountyName"]
    date_cols = [c for c in df.columns if c not in meta_cols]

    # Keep only the last N months
    date_cols_to_keep = date_cols[-HIST_MONTHS_TO_KEEP:]

    print(f"  Processing {len(df)} ZIPs...")
    conn.execute("DELETE FROM zip_history")

    batch = []
    for _, row in df.iterrows():
        zip_code = str(row.get("RegionName", "")).zfill(5)
        state = row.get("State", row.get("StateName", ""))
        city = row.get("City", "")
        metro = row.get("Metro", "")

        monthly = []
        for col in date_cols_to_keep:
            val = row.get(col)
            if pd.notna(val):
                monthly.append({"date": col, "value": float(val)})

        if not monthly:
            continue

        batch.append((
            zip_code, str(state), str(city), str(metro),
            json.dumps(monthly),
        ))

        if len(batch) >= 1000:
            conn.executemany(
                "INSERT OR REPLACE INTO zip_history (zip_code, state, city, metro, monthly_values) "
                "VALUES (?, ?, ?, ?, ?)",
                batch,
            )
            batch = []

    if batch:
        conn.executemany(
            "INSERT OR REPLACE INTO zip_history (zip_code, state, city, metro, monthly_values) "
            "VALUES (?, ?, ?, ?, ?)",
            batch,
        )

    conn.commit()
    hist_count = conn.execute("SELECT COUNT(*) FROM zip_history").fetchone()[0]
    print(f"  Loaded {hist_count} ZIPs into zip_history")

    # --- Forecast ---
    local_fcst = os.path.join(DATA_DIR, "Zforecast.csv")
    if os.path.exists(local_fcst):
        print("  Loading ZHVF forecast from local file...")
        fcst_df = pd.read_csv(local_fcst, dtype={"RegionName": str})
    else:
        print("  Downloading ZHVF forecast...")
        resp = requests.get(ZILLOW_FORECAST_URL, timeout=60)
        resp.raise_for_status()
        fcst_df = pd.read_csv(StringIO(resp.text), dtype={"RegionName": str})

    fcst_meta = ["RegionID", "SizeRank", "RegionName", "RegionType", "StateName",
                 "State", "City", "Metro", "CountyName", "BaseDate"]
    fcst_date_cols = [c for c in fcst_df.columns if c not in fcst_meta]

    conn.execute("DELETE FROM zip_forecast")
    batch = []
    for _, row in fcst_df.iterrows():
        zip_code = str(row.get("RegionName", "")).zfill(5)
        state = row.get("State", row.get("StateName", ""))

        forecasts = []
        for col in fcst_date_cols:
            val = row.get(col)
            if pd.notna(val):
                forecasts.append({"date": col, "change": float(val)})

        if not forecasts:
            continue

        batch.append((zip_code, str(state), json.dumps(forecasts)))

        if len(batch) >= 1000:
            conn.executemany(
                "INSERT OR REPLACE INTO zip_forecast (zip_code, state, monthly_forecasts) "
                "VALUES (?, ?, ?)",
                batch,
            )
            batch = []

    if batch:
        conn.executemany(
            "INSERT OR REPLACE INTO zip_forecast (zip_code, state, monthly_forecasts) "
            "VALUES (?, ?, ?)",
            batch,
        )

    conn.commit()
    fcst_count = conn.execute("SELECT COUNT(*) FROM zip_forecast").fetchone()[0]
    print(f"  Loaded {fcst_count} ZIPs into zip_forecast")

    conn.execute(
        "INSERT OR REPLACE INTO data_meta (source, last_refreshed, row_count, notes) VALUES (?, ?, ?, ?)",
        ("zillow", time.time(), hist_count, f"history: {HIST_MONTHS_TO_KEEP}mo, forecast: {len(fcst_date_cols)} periods"),
    )
    conn.commit()
    conn.close()

    # Clear in-memory caches so API picks up new data
    invalidate_zip_cache()
    print("  Done.\n")


# ---------------------------------------------------------------------------
# Geo + Tax data
# ---------------------------------------------------------------------------

GEO_URL = "https://raw.githubusercontent.com/scpike/us-state-county-zip/refs/heads/master/geo-data.csv"


def refresh_geo_and_tax():
    print("=== Refreshing geo + tax data ===")
    conn = get_connection()

    # Geo lookup
    print("  Downloading geo data...")
    resp = requests.get(GEO_URL, timeout=30)
    resp.raise_for_status()
    df = pd.read_csv(StringIO(resp.text), dtype=str)

    conn.execute("DELETE FROM geo_lookup")
    batch = []
    # Column names vary — try common ones
    zip_col = next((c for c in df.columns if "zip" in c.lower()), df.columns[0])
    county_col = next((c for c in df.columns if "county" in c.lower()), df.columns[1])
    state_col = next((c for c in df.columns if "state" in c.lower()), df.columns[2])

    for _, row in df.iterrows():
        batch.append((str(row[zip_col]).zfill(5), str(row[county_col]), str(row[state_col])))
        if len(batch) >= 1000:
            conn.executemany("INSERT OR REPLACE INTO geo_lookup VALUES (?, ?, ?)", batch)
            batch = []
    if batch:
        conn.executemany("INSERT OR REPLACE INTO geo_lookup VALUES (?, ?, ?)", batch)
    conn.commit()
    geo_count = conn.execute("SELECT COUNT(*) FROM geo_lookup").fetchone()[0]
    print(f"  Loaded {geo_count} ZIP codes into geo_lookup")

    # Tax data — fetch from US Census Bureau ACS 5-year estimates
    # B25103_001E = median property tax paid ($)
    # B25077_001E = median home value ($)
    # Effective rate = tax_paid / home_value
    conn.execute("DELETE FROM tax_rates")
    tax_count = 0

    census_url = "https://api.census.gov/data/2023/acs/acs5?get=B25103_001E,B25077_001E,NAME&for=county:*&in=state:*"
    try:
        print("  Fetching property tax rates from Census Bureau ACS...")
        resp = requests.get(census_url, timeout=60)
        resp.raise_for_status()
        rows = resp.json()
        header = rows[0]

        # Census returns: [tax_paid, home_value, name, state_fips, county_fips]
        # We key by state FIPS to match geo_lookup (which also uses FIPS)
        state_totals: dict[str, list] = {}  # state_fips → [(tax, value), ...]

        def normalize_county(name: str) -> str:
            return (name.strip().lower()
                    .replace(" county", "").replace(" parish", "")
                    .replace(" borough", "").replace(" census area", "")
                    .replace(" municipality", "").replace(" city and", "")
                    .replace(".", "").replace("'", ""))

        for row in rows[1:]:
            tax_paid = row[0]
            home_value = row[1]
            name = row[2]           # e.g. "Autauga County, Alabama"
            state_fips = row[3]     # e.g. "01"

            if not tax_paid or not home_value or tax_paid == "null" or home_value == "null":
                continue
            tax_paid = float(tax_paid)
            home_value = float(home_value)
            if home_value <= 0 or tax_paid <= 0:
                continue

            rate = tax_paid / home_value

            # Parse county name from "County Name, State Name"
            parts = name.rsplit(", ", 1)
            if len(parts) != 2:
                continue
            county_name = normalize_county(parts[0])

            # Key: "county_name|state_fips" (matches geo_lookup which stores state as FIPS)
            # Strip leading zeros from FIPS to match geo_lookup format
            state_fips_clean = str(int(state_fips))
            key = f"{county_name}|{state_fips_clean}"
            conn.execute("INSERT OR REPLACE INTO tax_rates VALUES (?, ?)", (key, rate))
            tax_count += 1

            if state_fips_clean not in state_totals:
                state_totals[state_fips_clean] = []
            state_totals[state_fips_clean].append((tax_paid, home_value))

        # State-level fallback rates (weighted average across counties)
        for state_fips, pairs in state_totals.items():
            total_tax = sum(t for t, v in pairs)
            total_value = sum(v for t, v in pairs)
            if total_value > 0:
                state_rate = total_tax / total_value
                key = f"|{state_fips}"
                conn.execute("INSERT OR REPLACE INTO tax_rates VALUES (?, ?)", (key, state_rate))
                tax_count += 1

        print(f"  Loaded {tax_count} tax rate entries (counties + state fallbacks)")

    except Exception as e:
        print(f"  [WARN] Census API failed: {e}")
        print("  Falling back to local CSV files if available...")

        # Fallback to local CSVs
        for path_dir in [DATA_DIR, os.path.join(os.path.dirname(__file__), "..", "rent-buy-api", "data")]:
            county_path = os.path.join(path_dir, "taxByCounty.csv")
            if os.path.exists(county_path):
                tdf = pd.read_csv(county_path, dtype=str)
                for _, row in tdf.iterrows():
                    county = row.get("County", "").strip().lower().replace(" county", "")
                    state = row.get("State", "").strip().lower()
                    rate_str = row.get("Effective Property Tax Rate (2023)", "0")
                    rate = float(rate_str.replace("%", "")) / 100
                    conn.execute("INSERT OR REPLACE INTO tax_rates VALUES (?, ?)", (f"{county}|{state}", rate))
                    tax_count += 1
                break

    conn.commit()
    print(f"  Total tax rate entries: {tax_count}")

    conn.execute(
        "INSERT OR REPLACE INTO data_meta (source, last_refreshed, row_count) VALUES (?, ?, ?)",
        ("geo_tax", time.time(), geo_count + tax_count),
    )
    conn.commit()
    conn.close()
    invalidate_zip_cache()
    print("  Done.\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def refresh_all():
    init_db()
    refresh_fred()
    refresh_zillow()
    refresh_geo_and_tax()

    # Print DB size
    db_size = os.path.getsize(DB_PATH) / (1024 * 1024)
    print(f"Database size: {db_size:.1f} MB at {DB_PATH}")

    conn = get_connection()
    for row in conn.execute("SELECT * FROM data_meta").fetchall():
        print(f"  {row['source']}: refreshed {time.strftime('%Y-%m-%d %H:%M', time.localtime(row['last_refreshed']))}")
    conn.close()


if __name__ == "__main__":
    if "--fred-only" in sys.argv:
        init_db()
        refresh_fred()
    elif "--zillow-only" in sys.argv:
        init_db()
        refresh_zillow()
    elif "--geo-only" in sys.argv:
        init_db()
        refresh_geo_and_tax()
    else:
        refresh_all()
