# Rent vs Buy Simulator

## Project Structure

```
mortgage/
├── api/                    ← NEW clean Python backend
│   ├── models.py           — Dataclasses: UserProfile, PropertyParams, MortgageParams, SimulationConfig, SimulationInput
│   ├── mortgage.py         — Pure math: amortization, PMI, credit rate adjustment, tax savings
│   ├── market.py           — FRED data loading (CPI, stocks, HPI, mortgage rates), stochastic path generators, tax lookups
│   ├── simulator.py        — Two-layer MC engine: Layer 1 (cacheable market paths), Layer 2 (per-request cash flow)
│   ├── data_store.py       — SQLite-backed store for ZIP-level data (Zillow) + tax rates, with LRU cache
│   ├── api.py              — FastAPI app: /summary endpoint, crash presets, Pydantic request/response models
│   ├── refresh_data.py     — Scheduled job to download fresh FRED + Zillow data into SQLite (run via cron)
│   ├── fetch_data.py       — One-time bootstrap script to populate api/data/ CSVs from FRED
│   ├── API.md              — Endpoint reference + frontend integration guide
│   ├── data/               — Quarterly CSVs (cpi, dow, hpi, mort) + Zillow CSVs + market.db (SQLite, ~108 MB)
│   ├── test_core.py        — Unit tests for mortgage math
│   ├── test_simulator.py   — End-to-end smoke test
│   └── tests/              — Comprehensive test suite (pytest)
├── rent-buy-api/           ← OLD Python backend (deprecated, kept for reference/data)
│   └── data/               — Zone.Identifier files pointing to original data sources
├── rent-buy-app/           ← OLD Flutter mobile app (being replaced with web frontend)
└── CLAUDE.md
```

## Architecture

### Two-Layer Monte Carlo Simulation
- **Layer 1 — Market Paths** (expensive, cached): Pre-generates N random paths for stocks, home values,
  and rent using historical FRED data as drift. Cached per `(ZIP, data_vintage, n_months, n_sims)`.
  Shared across all requests for the same area.
- **Layer 2 — Cash Flow** (cheap, per-request): Applies user-specific params (crash probability, budget,
  income, down payment, etc.) on top of cached paths. Pure arithmetic — enables slider UIs.

### Data Flow
1. **FRED CSVs** (cpi, stocks, HPI, mortgage rates) → loaded once at startup → in-memory cache (24h TTL)
2. **Zillow data** (26k ZIPs, 72 months history + forecasts) → SQLite `market.db` → queried per-ZIP with LRU cache (2048 entries)
3. **Property tax rates** → US Census Bureau ACS 5-year estimates (3,222 counties), computed as `median_tax_paid / median_home_value`.
   98.9% county-level match, 1.1% state fallback, 0% unmatched. Keyed by state FIPS codes matching geo_lookup.
4. **Geo lookup** (33k ZIPs → county + state FIPS) from public GitHub dataset
5. **Data refresh**: `refresh_data.py` runs on schedule (cron/ECS task), downloads fresh data, rebuilds SQLite.
   Safe during live serving (SQLite WAL mode). API picks up new data on next cache miss.
   - `--fred-only`: FRED macro data (~seconds)
   - `--zillow-only`: Zillow ZIP data, uses local CSVs if available (~30s from local, ~3min from web)
   - `--geo-only`: Geo lookup + Census tax rates (~10s)

### Crash Presets (Slider-Friendly)
User selects a crash outlook; the API maps it to probabilities:
- `none` → 0% prob
- `unlikely` → 5% prob, 15% housing / 20% stock drop
- `possible` → 15% prob, 20% / 25% drop (default)
- `likely` → 30% prob, 25% / 30% drop
- `very_likely` → 50% prob, 30% / 35% drop

### Key Financial Calculations (mortgage.py)
- **Amortization**: Standard formula, payment = P × r(1+r)^n / ((1+r)^n - 1)
- **PMI**: Based on initial LTV bracket + credit quality adjustment. Cancels at 80% LTV.
- **Credit rate adjustment**: Adds premium to base mortgage rate for credit quality + down payment size.
  Fixed bug from old code: `dp >= 0.05` threshold (was `0.5`).
- **Tax savings**: 12-month block processing. Compares itemized (mortgage interest + SALT-capped
  property tax + state income tax + other deductions) vs standard deduction. Uses marginal rate.
  SALT cap: $40,000.

### Key Conventions
- All rates as decimals (0.065 = 6.5%), except mortgage_rates array which is in percent (legacy FRED format)
- Snake_case everywhere (cleaned up from old camelCase mix)
- Dataclasses for models, not dicts with 30+ keys
- `np.random.default_rng(seed=42+sim)` for reproducible MC runs
- Tests use fixed seeds and assert exact numeric outcomes

## Environment
- Python 3.12+
- Key deps: numpy, scipy, pandas, fastapi, requests
- Data dir: `api/data/` (override via `MORTGAGE_DATA_DIR` env var)
- SQLite path: `api/data/market.db` (override via `MORTGAGE_DB_PATH` env var)
- AWS deployment, domain: rentbuysellapp.com

## Running
```bash
cd api
python refresh_data.py            # one-time: download all data (FRED + Zillow + Census) into SQLite
python refresh_data.py --fred-only    # just FRED macro data
python refresh_data.py --zillow-only  # just Zillow ZIP data
python refresh_data.py --geo-only     # just geo lookup + Census tax rates
pytest tests/                     # run test suite (89 tests)
uvicorn api:app --reload          # dev server
```

## What's Next
- [ ] Web frontend (Next.js) to replace Flutter app
- [ ] LLM summary endpoint (Claude API)
- [ ] Deploy frontend on AWS (S3 + CloudFront)
