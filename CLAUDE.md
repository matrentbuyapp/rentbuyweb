# Rent vs Buy Simulator

## Cross-Agent Contract

**Every agent must follow these rules. Non-negotiable.**

### On every session start
- **Backend/API agents**: Before writing code, check if `web/src/lib/types.ts` or `web/FRONTEND.md` reference anything you're about to change. If so, update `api/API.md` and note what the frontend agent needs to pick up in the "Known Drift" section below.
- **Frontend agent**: Before writing code, read `api/API.md` and the "Known Drift" section below. If the backend has added or changed endpoints since your last session, update `web/src/lib/types.ts` and `web/src/lib/api.ts` to match before doing anything else. Clear resolved items from "Known Drift".
- **Any agent**: If you touch files outside your layer, update the relevant interface spec (`api/API.md`, `web/src/lib/types.ts`, `web/FRONTEND.md`) in the same session. Do not leave it for "later".

### Interface docs are load-bearing
- `api/API.md` is the **source of truth** for the API contract. Backend agents must keep it current. Frontend agents must read it before every session.
- `web/src/lib/types.ts` must mirror `api/API.md` exactly. Frontend agent owns this file.
- `web/FRONTEND.md` documents component architecture and state flow. Frontend agent owns it.
- This file (`CLAUDE.md`) documents project-wide architecture and conventions. Any agent may update it.

### When you change an interface
1. Update the spec doc (`api/API.md` or `web/FRONTEND.md`) in the same commit as the code change.
2. If the change affects the other layer, add an entry to "Known Drift" below with the date and what needs updating.
3. The consuming agent must resolve drift entries at the start of their next session.

---

## Agent Standing Orders

**These apply to every agent working in this repo.**

1. **Tests are mandatory — both backend and frontend.**
   - **Backend**: Every code change that touches business logic, API endpoints, or data transformations must include or update tests. Run `cd api && pytest tests/` before considering work done. Never merge code that breaks existing tests. Target: maintain >90% coverage on `mortgage.py`, `scoring.py`, `simulator.py`.
   - **Frontend**: Every new component, hook, or page must have a smoke test. Every bug fix must add a regression test. Run `cd web && npm test` before considering work done. Never merge code that breaks existing tests. The suite runs in <1 second — there is no excuse to skip it.

2. **Keep documentation in sync.** When you add/change an API endpoint, update `api/API.md`. When you add/change frontend types or components, update `web/FRONTEND.md`. When you change project structure, update this file. Stale docs are worse than no docs.

3. **Respect role boundaries.** This project has three layers with clear ownership — see "Ownership & Roles" below. Do not make changes across boundaries without updating the interface spec (`api/API.md` or `web/src/lib/types.ts`). The API contract in `api/API.md` is the source of truth for backend–frontend integration.

4. **Interface-first.** When adding features that span API + frontend, define the API contract first (request/response shapes in `api/API.md`, TypeScript types in `web/src/lib/types.ts`), then implement backend, then frontend. This prevents drift.

5. **Test before refactoring.** If you plan to refactor, first ensure the area has test coverage. If it doesn't, add tests for current behavior, then refactor.

6. **No silent data format changes.** Any field rename must be coordinated across all three layers. See "Known Drift" below for current mismatches.


## Ownership & Roles

### Layer 1: Business Logic (Python, `api/`)
**Owner: Backend Agent**

Core simulation engine — pure math, no HTTP concerns.

| Module | Responsibility |
|--------|---------------|
| `models.py` | Dataclasses: `UserProfile`, `PropertyParams`, `MortgageParams`, `SimulationConfig`, `MarketOutlook`, `SimulationInput` |
| `mortgage.py` | Amortization, PMI, credit rate adjustment, tax savings |
| `simulator.py` | Two-layer MC engine (Layer 1: cached market paths, Layer 2: per-request cash flow) |
| `market.py` | FRED data loading, stochastic path generators, `HistoricalData` container |
| `scoring.py` | Buy score (0–100) + verdict computation |
| `sensitivity.py` | What-if analysis (vary inputs, measure output impact) |
| `trend.py` | Timing analysis, ZIP comparison |
| `llm_summary.py` | Claude API integration for narrative insights |
| `data_store.py` | SQLite CRUD: ZIP data, tax rates, devices, scenarios, alerts. LRU cache layer |
| `refresh_data.py` | Scheduled job: FRED + Zillow + Census → SQLite. Post-refresh notification hook |

### Layer 2: API (FastAPI, `api/api.py` + routers)
**Owner: API Agent**

Thin HTTP layer. Converts Pydantic models ↔ business logic dataclasses. No business logic here.

| Module | Responsibility |
|--------|---------------|
| `api.py` | FastAPI app, `/summary`, `/sensitivity`, `/trend`, `/zip-compare`, `/llm-summary`, `/health`. Request/response Pydantic models. Mounts routers |
| `scenarios.py` | PRO router: `POST/GET/DELETE /scenarios`, `POST /scenarios/{id}/run` |
| `notifications.py` | PRO router: alert CRUD (`/scenarios/{id}/alerts`), diff engine, SES email, `POST /devices/email`, `run_post_refresh_check()` |

**Interface spec**: `api/API.md` — every endpoint's request/response shapes, error codes, and integration guide.

### Layer 3: Frontend (Next.js 15, `web/`)
**Owner: Frontend Agent**

Static-export React app. Consumes the API, renders charts and forms.

| Path | Responsibility |
|------|---------------|
| `src/lib/types.ts` | TypeScript interfaces mirroring API shapes — **must stay in sync with `api/API.md`** |
| `src/lib/api.ts` | Fetch wrappers, `formToRequest()` conversion (% → decimals, etc.) |
| `src/lib/defaults.ts` | Default form values |
| `src/lib/device.ts` | Device UUID generation (localStorage) |
| `src/lib/formatters.ts` | Currency/percentage/number formatting |
| `src/lib/premium.ts` | PRO tier feature flags |
| `src/components/form/` | Multi-step input form (4 steps) |
| `src/components/results/` | Charts (Recharts), metrics, insights |
| `src/components/scenarios/` | PRO: save/load scenarios, alert toggles |
| `src/components/ui/` | Reusable primitives |
| `src/hooks/` | `useSimulation`, `useScenarios`, `usePremium` |

**Interface spec**: `web/FRONTEND.md` — component architecture, state flow, build/deploy.


## Known Drift (Must Fix)

These are field name mismatches between frontend and backend:

| Frontend (types.ts / api.ts) | Backend (api.py) | Status |
|------------------------------|-------------------|--------|
| `crash_outlook` → `outlook_preset` | `outlook_preset` | **FIXED 2026-03-30** — all frontend uses `outlook_preset` |
| `Warning` type | `InputWarning` | **FIXED 2026-03-29** — `Warning` interface defined in types.ts with code, severity, message |
| `mortgage_rate` percentiles | `PercentilesData` | **FIXED 2026-03-29** — added to `Percentiles` interface |
| PRO outlook overrides | Present in backend | **FIXED 2026-03-29** — all override fields in `SummaryRequest` + `FormData` + Advanced settings UI |
| Refi fields | `refi_enabled`, `refi_*` overrides | **FIXED 2026-03-30** — `RefiSummary` type, request fields, Pro controls |


## Open Tickets

### API-001: Replace first-crossing breakeven with sustained crossover (API Agent)

**Problem**: `breakeven_month` in `simulator.py:519-524` uses first-crossing — the first month where average buyer NW > renter NW. But the lines can zig-zag (crash recoveries, PMI cancellation, sell events). A user seeing "Buying pays off at Year 3" doesn't know the buyer falls behind again at Year 4 and doesn't durably lead until Year 8.

The `buy_score` in `scoring.py` component 2 (25% weight) also uses first-crossing, so a brief early lead inflates the score.

**Required changes** (all in API layer):

1. **`simulator.py`**: Change `breakeven_month` to sustained crossover — the first month where buyer NW exceeds renter NW and *stays ahead through the end*. Add `crossing_count` (number of times the lines cross) to `SimulationResult`.

2. **`scoring.py`**: Component 2 (breakeven timing, 25%) should use the sustained breakeven, not first-crossing.

3. **`api.py`**: Add `crossing_count: int` to `SummaryResponse`. Keep `breakeven_month` (now sustained semantics). Update API.md.

4. **`notifications.py`**: The alert diff engine compares `breakeven_month` — no code change needed, but the semantics shift (sustained is more stable, fewer false alerts).

**Suggested sustained breakeven logic**:
```python
# Find first month where buyer leads and stays ahead through the end
sustained_breakeven = None
for i in range(months):
    if all(accum[j].buyer_net_worth > accum[j].renter_net_worth for j in range(i, months)):
        sustained_breakeven = i
        break

crossing_count = sum(
    1 for i in range(1, months)
    if (accum[i].buyer_net_worth > accum[i].renter_net_worth) !=
       (accum[i-1].buyer_net_worth > accum[i-1].renter_net_worth)
)
```

**Frontend implications** (no breaking changes):
- `breakeven_month` field name stays the same, semantics improve
- New `crossing_count` field available for UI — frontend agent can show "steady winner" vs "lead changes X times"
- No frontend changes required for this to ship

### API-002: Fix SALT cap to $10,000 (API Agent)

**Problem**: `mortgage.py:176` has `SALT_CAP = 40_000`. The legal SALT deduction cap is $10,000 ($5,000 MFS) under TCJA through 2025. The $40K figure is from a House proposal that has not become law. This overstates tax savings for buyers in high-tax states by thousands per year.

**Fix**: Change to `SALT_CAP = 10_000`. One-line change in `mortgage.py`. Update tests in `test_mortgage.py` that assert tax savings values.


## Project Structure

```
mortgage/
├── CLAUDE.md               ← THIS FILE — agent instructions, ownership, architecture
├── api/                    ← Python backend (FastAPI)
│   ├── api.py              — FastAPI app + Pydantic models, mounts routers
│   ├── models.py           — Dataclasses for simulation inputs
│   ├── mortgage.py         — Pure financial math
│   ├── simulator.py        — Two-layer Monte Carlo engine
│   ├── market.py           — FRED data loading, stochastic path generators
│   ├── scoring.py          — Buy score (0-100) + verdict
│   ├── sensitivity.py      — What-if analysis
│   ├── trend.py            — Timing analysis + ZIP comparison
│   ├── llm_summary.py      — Claude API narrative generation
│   ├── data_store.py       — SQLite store (ZIP data, tax, devices, scenarios, alerts)
│   ├── scenarios.py        — PRO: scenario CRUD router
│   ├── notifications.py    — PRO: alert engine, diff detection, SES email
│   ├── refresh_data.py     — Data refresh job + post-refresh notification hook
│   ├── fetch_data.py       — One-time FRED bootstrap
│   ├── API.md              — Endpoint reference (source of truth for API contract)
│   ├── data/               — market.db (SQLite, ~108 MB) + CSV data
│   └── tests/              — pytest suite (269+ tests)
│       ├── conftest.py     — Shared fixtures (synthetic_data)
│       ├── test_mortgage.py
│       ├── test_simulator.py
│       ├── test_scoring.py
│       ├── test_market.py
│       ├── test_premium.py
│       ├── test_scenarios.py
│       └── test_sanity_scenarios.py
├── web/                    ← Next.js 15 frontend (static export)
│   ├── FRONTEND.md         — Frontend architecture spec
│   ├── vitest.config.ts    — Test config (jsdom + React plugin)
│   ├── src/lib/            — Types, API client, defaults, formatters
│   ├── src/components/     — Form steps, result charts, scenarios, UI primitives
│   ├── src/hooks/          — useSimulation, useScenarios, usePremium, useZipPrices
│   ├── src/__tests__/      — Vitest smoke tests (55+ tests, <1s)
│   │   ├── setup.ts        — Mocks (localStorage, fetch, IntersectionObserver, ResizeObserver)
│   │   ├── fixtures.ts     — Mock data factories (MOCK_RESULT, MOCK_SCENARIO, etc.)
│   │   └── smoke.test.tsx  — Smoke tests for every component, hook, and utility
│   └── package.json        — Next 15.4, React 19.1, Recharts 2.15, Tailwind 4.2, Vitest 4.1
├── rent-buy-api/           ← DEPRECATED old Python backend (kept for reference data)
└── rent-buy-app/           ← DEPRECATED old Flutter app (replaced by web/)
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
3. **Property tax rates** → US Census Bureau ACS 5-year estimates (3,222 counties), computed as `median_tax_paid / median_home_value`. Keyed by state FIPS codes.
4. **Geo lookup** (33k ZIPs → county + state FIPS) from public GitHub dataset
5. **Data refresh**: `refresh_data.py` runs on schedule (cron/ECS task). Safe during live serving (SQLite WAL mode). Post-refresh: re-runs saved scenarios with alerts, sends notifications via SES.

### PRO Features
- **Saved Scenarios**: Device-based identity (UUID in `X-Device-Id` header). CRUD via `/scenarios` endpoints. Re-run with fresh market data via `/scenarios/{id}/run`.
- **Alerts**: Per-scenario alert configs. Types: `threshold` (verdict flips), `shift` (breakeven moves ≥3 months), `digest` (monthly summary). Email via AWS SES.
- **Sensitivity Analysis**: `/sensitivity` — vary each input, measure output impact + 2D heatmap.
- **Timing Analysis**: `/trend` — delay purchase 0–8 quarters, compare outcomes.
- **ZIP Comparison**: `/zip-compare` — compare neighboring ZIPs.
- **AI Narrative**: `/llm-summary` — Claude API generates buy/rent pros, verdict narrative.

### Market Outlook Presets
| Preset | Volatility Scale | Housing Crash Prob | Stock Crash Prob |
|--------|:---:|:---:|:---:|
| `optimistic` | 0.7× | 0% | 0% |
| `historical` | 1.0× | 0% | 0% |
| `cautious` | 1.2× | 10% | 10% |
| `pessimistic` | 1.4× | 25% | 25% |
| `crisis` | 1.6× | 50% | 50% |

### Key Financial Calculations (mortgage.py)
- **Amortization**: Standard formula, payment = P × r(1+r)^n / ((1+r)^n - 1)
- **PMI**: Based on initial LTV bracket + credit quality adjustment. Cancels at 80% LTV.
- **Credit rate adjustment**: Premium to base rate for credit quality + down payment size.
- **Tax savings**: 12-month block processing. Itemized vs standard deduction comparison. SALT cap: $40,000.

### Key Conventions
- All rates as decimals (0.065 = 6.5%), except `mortgage_rates` array which is in percent (legacy FRED format)
- Snake_case everywhere
- Dataclasses for models, Pydantic for API request/response
- `np.random.default_rng(seed=42+sim)` for reproducible MC runs
- Tests use fixed seeds and assert exact numeric outcomes


## Environment & Running

### Backend (Python 3.12+)
```bash
cd api
pip install numpy scipy pandas fastapi uvicorn requests boto3

# Data setup (one-time)
python refresh_data.py              # download all data (FRED + Zillow + Census)
python refresh_data.py --fred-only  # just FRED macro data
python refresh_data.py --zillow-only # just Zillow ZIP data
python refresh_data.py --geo-only   # just geo lookup + Census tax rates

# Run
uvicorn api:app --reload            # dev server at http://localhost:8000
pytest tests/                       # run API test suite (269+ tests)

# Frontend
cd web
npm run dev                         # dev server at http://localhost:3000
npm test                            # run frontend tests (55+ tests, <1s)
```

**Important**: Do not run `npm run build` while the dev server is active — it overwrites `.next` and breaks CSS.

Environment variables:
- `MORTGAGE_DATA_DIR` — override data directory (default: `api/data/`)
- `MORTGAGE_DB_PATH` — override SQLite path (default: `api/data/market.db`)
- `ANTHROPIC_API_KEY` — required for `/llm-summary` endpoint

### Frontend (Node 18+)
```bash
cd web
npm install
npm run dev                         # dev server at http://localhost:3000
npm run build                       # static export to web/out/
```

Environment variables:
- `NEXT_PUBLIC_API_URL` — API base URL (default: `http://localhost:8000`, production: `https://api.rentbuysellapp.com`)

### Deployment
- **API**: AWS ECS / uvicorn behind ALB. Domain: `api.rentbuysellapp.com`
- **Frontend**: Static export → S3 + CloudFront. Domain: `rentbuysellapp.com`
- **Data refresh**: ECS scheduled task or cron running `python refresh_data.py`
- **Alerts email**: AWS SES, sender `alerts@rentbuysellapp.com`


## SQLite Schema (data_store.py)

### Market Data Tables
- `zip_history` — monthly home values per ZIP (72 months)
- `zip_forecast` — monthly growth forecasts per ZIP
- `geo_lookup` — ZIP → county/state FIPS mapping
- `tax_rates` — property tax rates by county and state
- `data_meta` — tracks when each data source was last refreshed

### PRO Feature Tables
- `devices` — device_id (UUID), email, created_at, last_seen_at
- `scenarios` — id, device_id, name, inputs_json, response_json, timestamps
- `alerts` — id, scenario_id, device_id, alert_type, enabled, config_json, last_triggered_at
- `notification_log` — id, alert_id, scenario_id, device_id, diff_json, sent_at, channel
