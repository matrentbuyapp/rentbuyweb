# API Changelog

## 2026-03-30 (continued)

### New Features
- **Refinance modeling** — on by default with conservative settings (1% threshold, $5K cost, 24mo cooldown, max 1 refi). Each MC sim checks the forecasted rate path monthly; if the market rate drops enough, the buyer refis (new amortization, closing costs deducted). Response includes `refi_summary` with: pct_sims_refinanced, avg_refi_month, avg_refi_rate, avg_payment_drop, refi_benefit (NW delta vs no-refi). PRO users can adjust all settings or disable.
- **Trend `delta_from_now`** — each delay point now shows the change vs buying now (0 for delay=0). Previously showed absolute buyer-renter difference which didn't answer "when should I buy?"
- **Home appreciation drift fix** — replaced historical HPI drift (which embedded the 2020-2025 boom at 15%/yr) with long-term national average (3.5%/yr) as baseline. Historical data contributes volatility only, not drift level. ZIP data still influences first 12 months when available. Non-monotonic timing trends are now possible.
- **What-if trimmed to 5 defaults** — rates drop 1%, rates rise 1%, cheaper home, save 2 more years, crash next year. The 4 removed scenarios (rates drop 2%, 20% down, stay 5yr, savings only) still available via `scenario_ids`.

## 2026-03-30

### New Features
- **`headline` object in SummaryResponse** — structured primary result for first-time users. Contains `winner` ("buy"/"rent"/"toss-up"), `short` (one-sentence answer with dollar amount), `detail` (two-sentence context with monthly cost comparison and breakeven timing), `confidence` ("high"/"moderate"/"low" based on crossing count and magnitude), `monthly_savings` (monthly cost difference). Score/verdict kept for PRO/power users.

## 2026-03-29 (continued, part 4)

### Improvements
- **Home appreciation mean reversion** — Historical HPI drift (which includes the 2020-2025 boom at ~8%/yr) now blends toward the long-term national average (3.5%/yr, Case-Shiller since 1991) beyond year 5. Months 0-60: full historical drift. 60-120: linear blend. 120+: long-term average. This prevents 15-year scenarios from inheriting unrealistic 8-9%/yr appreciation. 10-year scenarios see moderate impact (blend starts at month 60).

### Test Coverage
- **Granular math tests** — 9 new tests verifying exact dollar amounts: P&I matches formula, interest+principal=payment, NW identity, equity formula, cumulative cost sums, component sums, balance monotonicity, sell event math, savings-only renter reproducibility.
- **10 new real-life scenarios** — DC sell after 5yr, Phoenix delay 12mo, Miami savings-only, Chicago 15yr mortgage, Raleigh 3yr horizon, Houston 15yr horizon, Minneapolis pessimist, San Diego aggressive, Detroit 7yr stay, NYC delay+short stay.
- Total: 453 tests, all passing.

## 2026-03-29 (continued, part 3)

### New Features
- **Expanded sensitivity analysis** — 8 configurable 1D axes (was 4 hardcoded): `mortgage_rate`, `house_price`, `down_payment_pct`, `outlook`, `stay_years`, `yearly_income`, `initial_cash`, `risk_appetite`. Request specifies which to run via `axes` field.
- **Configurable heatmap** — 2D grid now accepts `heatmap_x` and `heatmap_y` to cross any two axes. Default remains rate × price.
- **`POST /whatif` endpoint** — 9 named what-if scenarios: rate changes, cheaper home, delay purchase, 20% down, crash, stay 5yr, conservative investing. Each returns `delta_from_base` showing the improvement/degradation vs the user's base case. Scenarios that duplicate base are auto-filtered.
- **`SensitivityRequest`** model extends `SummaryRequest` with `axes`, `heatmap_x`, `heatmap_y`.

## 2026-03-29 (continued, part 2)

### New Features
- **Result caching layer** (`result_cache.py`). Deterministic simulations with the same inputs + data vintage produce the same results. Cache key = SHA-256(canonical_inputs + data_vintage). Each endpoint's result stored in separate column, populated lazily. ~334x speedup on cache hits (1s → 3ms).
- **`cache_key` and `data_vintage` in SummaryResponse** — frontend can use these for client-side caching and to detect stale results.
- **Cache pruning** — entries older than 90 days with no scenario reference are cleaned after data refresh.
- All PRO endpoints (`/sensitivity`, `/trend`, `/zip-compare`, `/llm-summary`) now cached under the same cache_key.

## 2026-03-29 (continued)

### Breaking Changes
- **`breakeven_month` is now sustained, not first-crossing.** Previously reported the first month buyer NW > renter NW. Now reports when buyer **durably** pulls ahead and stays ahead through end of horizon. If buyer briefly leads then falls behind, `breakeven_month` reflects the last durable crossing, not the first. `null` if buyer never durably leads. All modules updated: `simulator.py`, `scoring.py`, `sensitivity.py`, `trend.py`, `llm_summary.py`.
- **`crossing_count` added to `SummaryResponse`.** Number of times buyer/renter lead swaps. 0 = clear winner, 3+ = volatile. Used by scoring to penalize unstable outcomes (-3 points per extra crossing beyond 1).

## 2026-03-29

### Bug Fixes
- **Critical: Buyer initial_cash not credited** — When `buy_delay_months=0` (default), the buyer started with $0 while the renter got `initial_cash`. Both now start equal. This was a systematic bias toward renting in every simulation.
- **Partial-year tax proration** — Final partial year compared partial deductions against full annual standard deduction. Now prorates SALT cap, state tax, other deductions, and standard deduction.
- **Buyer housing cost during delay** — `total_housing_cost` was 0 during `buy_delay` months even though buyer was paying rent. Now correctly reflects rent.
- **Scenario re-run validation** — `POST /scenarios/{id}/run` now calls `_resolve_and_validate()`, so saved scenarios with impossible inputs return proper errors instead of running silently.

### New Features
- **Percentile bands** — P10/P25/P50/P75/P90 for `buyer_net_worth`, `renter_net_worth`, `home_value`, `buyer_equity`, `mortgage_rate` in `SummaryResponse.percentiles`. Enables uncertainty fan charts.
- **`breakeven_month`** in `/summary` response — first month buyer NW > renter NW, or null.
- **`stay_years` parameter** — Separates "how long to own" from "planning horizon". Buyer sells at `buy_delay + stay_years*12`, receives net equity, then rents for the remainder. Three-phase cash flow: rent → own → sell & rent again.
- **`years` validation** — Clamped to 2-15. Scoring thresholds scale with horizon.
- **Median home price fallback** — When no `house_price` is provided, uses Zillow ZHVI median for the ZIP (or national median ~$277K). Replaces the old affordability-based estimate.
- **Mortgage rate forecaster** — Three-regime stochastic model: 9-month momentum with decay → blend to 5y average → mean-revert to 20y average. Used for delayed purchases (each MC sim gets the forecasted rate at purchase month). Returned in `percentiles.mortgage_rate`.
- **Rate forecast overrides (PRO)** — `rate_target` (custom mean-reversion anchor) and `rate_volatility_scale` (noise scaling).
- **Crash recovery model** — Crashes now partially recover (default: housing 50% in 60mo, stocks 70% in 36mo). Configurable via `housing_recovery_pct`, `housing_recovery_months`, `stock_recovery_pct`, `stock_recovery_months`. `recovery_pct=0` gives the old permanent-shift behavior.
- **`savings_only` risk appetite** — New option: surplus cash grows at 4.5% HYSA rate instead of stock market. No MC variance on cash side.
- **Input validation** — Errors (422) for impossible inputs: can't close, mortgage > budget, down < 3%, budget < rent. Warnings (200) for DTI > 43%, price > 5x income, thin reserves.
- **`POST /summary/csv`** — Export simulation results as downloadable CSV with header metadata + 20 columns per month.
- **`GET /data/zip_prices.json`** — Static JSON with median prices + tax rates for 26K ZIPs. Generated by `refresh_data.py --zip-prices`.
- **`warnings[]` in SummaryResponse** — Structured validation warnings alongside results.

### Test Coverage
- **Sanity scenario tests** — 12 real-life scenarios (SF, NYC, Cleveland, etc.) with directional assertions. 121 new tests.
- Total: 271 tests, all passing.

### Documentation
- `API.md` updated with all new fields, validation rules, three-phase timeline, rate forecast model, recovery parameters, CSV endpoint, percentile bands, slider constraints.
- `CLAUDE.md` updated with ownership model, standing orders, known drift.
