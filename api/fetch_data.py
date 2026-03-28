"""Fetch market data from FRED and Zillow and write to data/ directory.

Run this script to populate the data files needed by the simulator.
Uses public CSV endpoints — no API key required.

FRED series:
  - CPIAUCSL: Consumer Price Index (monthly, seasonally adjusted)
  - SP500: S&P 500 (monthly, better coverage than DOW on FRED)
  - CSUSHPINSA: Case-Shiller Home Price Index (monthly)
  - MORTGAGE30US: 30-Year Fixed Mortgage Rate (weekly → we resample quarterly)
  - MORTGAGE15US: 15-Year Fixed Mortgage Rate

Zillow data:
  - ZHVI: Zillow Home Value Index by ZIP (historical)
  - ZHVF: Zillow Home Value Forecast by ZIP
"""

import os
import pandas as pd
import requests
from io import StringIO
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)


def fetch_fred_series(series_id: str, start: str = "2000-01-01") -> pd.DataFrame:
    """Fetch a FRED series as CSV (no API key needed)."""
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd={start}"
    print(f"  Fetching {series_id} from FRED...")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    df = pd.read_csv(StringIO(resp.text))
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna()
    return df


def resample_to_quarterly(df: pd.DataFrame) -> pd.Series:
    """Resample a dated DataFrame to quarterly averages."""
    df = df.set_index("date")
    return df["value"].resample("QS").mean().dropna()


def save_quarterly_csv(series: pd.Series, filename: str):
    """Save a quarterly series as a single-column CSV (values only)."""
    path = os.path.join(DATA_DIR, filename)
    series.to_csv(path, index=False, header=False)
    print(f"  Saved {filename}: {len(series)} quarters")


def fetch_zillow_csv(url: str, filename: str):
    """Download a Zillow CSV file."""
    path = os.path.join(DATA_DIR, filename)
    print(f"  Fetching {filename} from Zillow...")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    with open(path, "w") as f:
        f.write(resp.text)
    # Count rows
    lines = resp.text.count("\n")
    print(f"  Saved {filename}: ~{lines} rows")


def fetch_geo_data():
    """Download ZIP-to-county-state mapping."""
    url = "https://raw.githubusercontent.com/scpike/us-state-county-zip/refs/heads/master/geo-data.csv"
    path = os.path.join(DATA_DIR, "geoData.csv")
    print("  Fetching geoData.csv...")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    with open(path, "w") as f:
        f.write(resp.text)
    print(f"  Saved geoData.csv")


def main():
    print("=== Fetching FRED data ===")

    # CPI
    cpi = fetch_fred_series("CPIAUCSL")
    cpi_q = resample_to_quarterly(cpi)
    save_quarterly_csv(cpi_q, "cpi.csv")

    # S&P 500 (as stock market proxy)
    sp500 = fetch_fred_series("SP500")
    sp500_q = resample_to_quarterly(sp500)
    save_quarterly_csv(sp500_q, "dow.csv")  # keeping filename for compat

    # Home Price Index (Case-Shiller)
    hpi = fetch_fred_series("CSUSHPINSA")
    hpi_q = resample_to_quarterly(hpi)
    save_quarterly_csv(hpi_q, "hpi.csv")

    # Mortgage rates (30Y)
    mort = fetch_fred_series("MORTGAGE30US")
    mort_q = resample_to_quarterly(mort)
    save_quarterly_csv(mort_q, "mort.csv")

    print("\n=== Fetching Zillow data ===")

    fetch_zillow_csv(
        "https://files.zillowstatic.com/research/public_csvs/zhvi/Zip_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv",
        "Zhistory.csv",
    )
    fetch_zillow_csv(
        "https://files.zillowstatic.com/research/public_csvs/zhvf_growth/Zip_zhvf_growth_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv",
        "Zforecast.csv",
    )

    print("\n=== Fetching geo data ===")
    fetch_geo_data()

    # Tax data needs to be manually sourced (Tax Foundation doesn't have a public CSV endpoint)
    tax_county_path = os.path.join(DATA_DIR, "taxByCounty.csv")
    tax_state_path = os.path.join(DATA_DIR, "taxByState.csv")
    if not os.path.exists(tax_county_path):
        print("\n[NOTE] taxByCounty.csv not found — copy from rent-buy-api/data/ or source from Tax Foundation")
    if not os.path.exists(tax_state_path):
        print("[NOTE] taxByState.csv not found — copy from rent-buy-api/data/ or source from Tax Foundation")

    print("\nDone!")


if __name__ == "__main__":
    main()
