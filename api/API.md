# Rent vs Buy API — Endpoint Reference

Base URL: `https://api.rentbuysellapp.com` (production) or `http://localhost:8000` (dev)

---

## Free Tier Endpoints

### `POST /summary`

Main endpoint. Runs the Monte Carlo simulation and returns a month-by-month comparison of buying vs renting.

#### Request Body

```json
{
  // === REQUIRED ===
  "monthly_rent": 3500,          // Current monthly rent ($)
  "monthly_budget": 5000,        // Total monthly housing budget ($)

  // === USER PROFILE (optional) ===
  "initial_cash": 150000,        // Savings available ($). Default: 150000
  "yearly_income": 120000,       // Gross annual income for tax calc ($). Default: 0
  "filing_status": "single",     // "single" | "married_joint" | "head_of_household". Default: "single"
  "other_deductions": 0,         // Annual itemized deductions beyond mortgage/SALT ($). Default: 0
  "risk_appetite": "moderate",   // "savings_only" | "conservative" (0.5x) | "moderate" (1x) | "aggressive" (1.5x). Default: "moderate"

  // === PROPERTY (optional) ===
  "zip_code": "10001",           // ZIP code for local market data + tax rates. Default: null (national avg)
  "house_price": 650000,         // Specific home price ($). Default: null (auto-estimated from rent/budget)
  "down_payment_pct": 0.10,      // Down payment as decimal. Default: 0.10 (10%)
  "closing_cost_pct": 0.03,      // Closing costs as fraction of price. Default: 0.03 (3%)
  "maintenance_rate": 0.01,      // Annual maintenance as fraction of home value. Default: 0.01 (1%)
  "insurance_annual": 2400,      // Annual home insurance ($). Default: 0
  "sell_cost_pct": 0.06,         // Selling costs as fraction of home value. Default: 0.06 (6%)
  "move_in_cost": 0,             // One-time move-in cost ($). Default: 0

  // === MORTGAGE (optional) ===
  "mortgage_rate": null,         // Annual rate as decimal (0.065 = 6.5%). Default: null (looked up from FRED)
  "term_years": 30,              // Loan term in years. Default: 30
  "credit_quality": "good",      // "excellent" | "great" | "good" | "average" | "mediocre" | "poor". Default: "good"

  // === SIMULATION (optional) ===
  "years": 10,                   // Planning horizon in years (2-15). Default: 10
  "stay_years": null,            // How long to own before selling (1-15, null = same as years). Default: null
  "num_simulations": 500,        // Number of MC runs. Default: 500
  "buy_delay_months": 0,         // Months to wait before purchasing. Default: 0

  // === MARKET OUTLOOK ===
  "outlook_preset": "historical", // "optimistic" | "historical" | "cautious" | "pessimistic" | "crisis". Default: "historical"

  // Pro tier: override individual outlook params (ignored if null)
  "volatility_scale": null,
  "housing_crash_prob": null,
  "housing_crash_drop": null,
  "housing_drawdown_months": null,
  "stock_crash_prob": null,
  "stock_crash_drop": null,
  "stock_drawdown_months": null,
  "housing_recovery_pct": null,       // 0=permanent crash, 1=full V-shape. Default: 0.5
  "housing_recovery_months": null,    // Months to recover. Default: 60
  "stock_recovery_pct": null,         // Default: 0.7
  "stock_recovery_months": null,      // Default: 36

  // Pro tier: rate forecast overrides
  "rate_target": null,                // Target rate as decimal (0.055 = 5.5%). Replaces 20y avg as mean-reversion anchor
  "rate_volatility_scale": null       // Scale rate noise (1.0 = historical, 0.5 = calm, 2.0 = turbulent)
}
```

#### Validation Rules
- `years` must be 2–15
- `stay_years` (if set) must be 1–15
- `buy_delay_months + stay_years × 12` must not exceed `years × 12`

#### Market Outlook Presets

| Value | Volatility | Housing Crash Prob | Housing Drop | Stock Crash Prob | Stock Drop |
|-------|:---:|:---:|:---:|:---:|:---:|
| `optimistic` | 0.7× | 0% | 0% | 0% | 0% |
| `historical` | 1.0× | 0% | 0% | 0% | 0% |
| `cautious` | 1.2× | 10% | 10% | 10% | 15% |
| `pessimistic` | 1.4× | 25% | 20% | 25% | 25% |
| `crisis` | 1.6× | 50% | 30% | 50% | 35% |

#### Crash Recovery Model

Crashes are no longer permanent level shifts. After the drawdown phase, prices partially recover via exponential mean-reversion. Configurable per asset class:

| Parameter | Housing Default | Stock Default | Crisis Preset |
|-----------|:---:|:---:|:---:|
| `recovery_pct` | 0.5 (50%) | 0.7 (70%) | 0.3 / 0.5 |
| `recovery_months` | 60 (5yr) | 36 (3yr) | 84 / 48 |

- `recovery_pct=0`: permanent crash (old behavior, most pessimistic)
- `recovery_pct=0.5`: half the drop recovers (middle-of-the-road default)
- `recovery_pct=1.0`: full V-shaped recovery

Example: 20% housing crash with 50% recovery over 60 months
- Trough: -20% from pre-crash level
- After 60 months: -10% (half the gap recovered)
- Permanent damage: -10% (the other half never recovers)

#### Credit Quality Impact on Mortgage Rate

| Quality | Rate Premium | With 20% Down | With 5% Down |
|---------|:---:|:---:|:---:|
| `excellent` | +0.00% | -0.125% | +0.25% |
| `great` | +0.125% | +0.125% | +0.375% |
| `good` | +0.375% | +0.375% | +0.625% |
| `average` | +0.75% | +0.75% | +1.00% |
| `mediocre` | +1.25% | +1.25% | +1.50% |
| `poor` | +2.00% | +2.00% | +2.25% |

#### Risk Appetite — How Surplus Cash is Invested

| Value | Investment Strategy | Return Source | MC Variance on Cash |
|-------|:---|:---|:---:|
| `savings_only` | High-yield savings account (4.5% APY) | Fixed monthly rate, deterministic | None |
| `conservative` | 50% stock market exposure | 0.5× historical stock returns | Low |
| `moderate` | 100% stock market exposure | 1× historical stock returns | Medium |
| `aggressive` | 150% leveraged stock exposure | 1.5× historical stock returns | High |

`savings_only` is for fully risk-averse users who would not invest in the market at all. With this setting, both buyer and renter surplus cash grows at a fixed 4.5% APY. The only MC variance comes from home value appreciation (still stochastic). This makes buying look relatively better because the renter's alternative (savings account) compounds much more slowly than stocks.

#### Validation & Warnings

The response includes a `warnings` array. If inputs are impossible (e.g., can't afford to close), the API returns 422 with structured errors.

**Errors (422):**
| Code | Trigger |
|------|---------|
| `budget_below_rent` | Budget < rent |
| `insufficient_cash_to_close` | Savings < down payment + closing + move-in |
| `mortgage_exceeds_budget` | Monthly P&I > budget |
| `down_payment_too_low` | Down payment < 3% |

**Warnings (200, in `warnings[]`):**
| Code | Trigger |
|------|---------|
| `total_cost_exceeds_budget` | Mortgage fits but total ownership cost > budget |
| `dti_too_high` | Housing cost > 43% of gross income |
| `price_to_income_high` | Price > 5× annual income |
| `thin_reserves` | < 2 months housing costs left after closing |

**Static rules (frontend can enforce without API):**
- `monthly_rent > 0`, `monthly_budget >= monthly_rent`, `initial_cash >= 0`
- `down_payment_pct` in `[0.03, 1.0]`, `house_price > 0` when provided

#### Response

```json
{
  "house_price": 650000,
  "mortgage_rate": 0.06875,
  "property_tax_rate": 0.0142,
  "avg_buyer_net_worth": 620000,
  "avg_renter_net_worth": 580000,
  "buy_score": 72,                   // 0-100 composite score
  "verdict": "Lean Buy",            // text verdict from score
  "breakeven_month": 54,            // sustained: when buyer durably pulls ahead (null if never)
  "crossing_count": 1,              // how many times buyer/renter lead swaps (0 = clear winner)

  "warnings": [                      // validation warnings (empty if inputs are clean)
    { "code": "dti_too_high", "severity": "warning", "message": "Housing costs would be 48%..." }
  ],

  "monthly": [                       // Array of N objects (years × 12 months)
    {
      "home_value": 650000,
      "mortgage_payment": 3740,
      "interest_payment": 3500,
      "principal_payment": 240,
      "remaining_balance": 584760,
      "maintenance": 541,
      "property_tax": 769,
      "insurance": 200,
      "pmi": 197,
      "tax_savings": 502,
      "total_housing_cost": 4945,
      "rent": 3500,
      "budget": 5000,
      "buyer_investment": 12000,
      "renter_investment": 152000,
      "buyer_equity": 45000,
      "buyer_net_worth": 57000,
      "renter_net_worth": 152000,
      "cumulative_buy_cost": 4945,
      "cumulative_rent_cost": 3500
    }
  ],

  "percentiles": {
    "buyer_net_worth": { "p10": [...], "p25": [...], "p50": [...], "p75": [...], "p90": [...] },
    "renter_net_worth": { "p10": [...], "p25": [...], "p50": [...], "p75": [...], "p90": [...] },
    "home_value": { "p10": [...], "p25": [...], "p50": [...], "p75": [...], "p90": [...] },
    "buyer_equity": { "p10": [...], "p25": [...], "p50": [...], "p75": [...], "p90": [...] },
    "mortgage_rate": { "p10": [...], "p25": [...], "p50": [...], "p75": [...], "p90": [...] }
  }
}
```

#### Key Relationships

```
total_housing_cost = mortgage_payment + maintenance + property_tax + insurance + pmi - tax_savings
buyer_net_worth = buyer_equity + buyer_investment
buyer_equity = home_value × (1 - sell_cost_pct) - remaining_balance
renter_net_worth = renter_investment
```

The renter invests `budget - rent` each month. The buyer invests `budget - total_housing_cost`. Both earn stock market returns.

#### House Price Resolution

When `house_price` is not provided:
1. If `zip_code` is given → uses Zillow ZHVI (median home value for that ZIP)
2. If no ZIP → uses national median home price (~$277K from 26K Zillow ZIPs)

#### Three-Phase Simulation Timeline

The buyer's cash flow has up to three phases depending on `buy_delay_months` and `stay_years`:

```
|--- Phase 1: Renting ---|--- Phase 2: Owning ---|--- Phase 3: Post-sell (renting again) ---|
0              buy_delay   buy_delay+stay_years*12                                    years*12
```

- **Phase 1** (month 0 to `buy_delay`): Buyer mirrors renter — both pay rent, invest surplus
- **Phase 2** (`buy_delay` to `buy_delay + stay_years × 12`): Buyer owns — pays mortgage/tax/insurance/PMI, builds equity
- **Phase 3** (`buy_delay + stay_years × 12` to end): Buyer sold — net equity added to investment account, pays rent again

If `stay_years` is null or equals `years`, Phase 3 never occurs (buyer owns for the full horizon).

**At the sell event**, the buyer receives:
```
sale_proceeds = home_value × (1 - sell_cost_pct) - remaining_mortgage_balance
```
This is added to `buyer_investment`. After selling, `buyer_equity = 0`, `mortgage_payment = 0`, and `total_housing_cost = rent`.

**Monthly data behavior across phases:**

| Field | Phase 1 | Phase 2 | Phase 3 |
|-------|---------|---------|---------|
| `mortgage_payment` | 0 | payment amount | 0 |
| `buyer_equity` | 0 | home equity | 0 |
| `total_housing_cost` | rent | ownership costs | rent |
| `buyer_investment` | same as renter | liquid portfolio | portfolio + sale proceeds |
| `home_value` | tracked (not owned) | owned | tracked (not owned) |

**Frontend chart implications:**
- Net Worth chart: buyer line may jump at sell month (equity → cash)
- Cost Breakdown: stacked areas drop to zero at sell month
- Suggested: draw a vertical dashed line at `buy_delay_months + stay_years × 12` labeled "Sell"

#### Slider Dependency Constraints (enforce in UI)

```
max_stay = years - Math.ceil(buy_delay_months / 12)
stay_years = Math.min(stay_years, max_stay)
```

| Setting | Tier | Range | Default | Clamped by |
|---------|------|-------|---------|------------|
| `stay_years` | Free | 1 to `max_stay` | = `years` | `years` and `buy_delay_months` |
| `years` | PRO | 2 to 15 | 10 | — |
| `buy_delay_months` | PRO | 0 to 24 | 0 | Reduces max `stay_years` |

When user changes `years` down, clamp `stay_years`. When user increases `buy_delay_months`, reduce max `stay_years`. The API returns **422** if the constraint is violated.

#### Percentile Bands

Each band array has one value per month (`years × 12` entries). Use for uncertainty fan charts:
- Light shading between P10–P90
- Medium shading between P25–P75
- Solid line at P50 (median)

Available for: `buyer_net_worth`, `renter_net_worth`, `home_value`, `buyer_equity`, `mortgage_rate`.

#### Mortgage Rate Forecast

The API generates a stochastic mortgage rate path for each MC simulation using a three-regime model:

1. **Short-term (months 0-24)**: Extrapolates the 2-year momentum with exponential decay (half-life 12 months)
2. **Medium-term (months 24-60)**: Blends from decayed trend toward the 5-year historical average
3. **Long-term (months 60+)**: Ornstein-Uhlenbeck mean reversion to the 20-year average (half-life 5 years)

Calibrated noise is added at every month (from historical month-to-month volatility). Rates are floored at 1% and capped at 15%.

**Impact on simulation:**
- If `mortgage_rate` is explicitly provided → locked for all simulations, forecast ignored
- If `mortgage_rate` is null and `buy_delay_months = 0` → uses latest FRED rate
- If `mortgage_rate` is null and `buy_delay_months > 0` → each MC simulation uses the forecasted rate at the purchase month. The `mortgage_rate` in the response reports the median forecasted rate.

**`percentiles.mortgage_rate`** values are in percent (e.g., 6.5 = 6.5%). Useful for a "Rate Forecast" chart showing where rates might go. The frontend can display this as a PRO feature.

---

### `GET /health`

Returns `{"status": "ok"}`. Use for load balancer health checks.

---

## Pro Tier Endpoints

### `POST /summary/csv`

Export simulation results as a downloadable CSV. Same request body as `/summary`.

Returns `text/csv` with:
- Header rows prefixed with `#` (house price, rate, score, verdict, breakeven, warnings)
- Column headers: `month, year, home_value, mortgage_payment, interest_payment, principal_payment, remaining_balance, maintenance, property_tax, insurance, pmi, tax_savings, total_housing_cost, rent, budget, buyer_investment, renter_investment, buyer_equity, buyer_net_worth, renter_net_worth, cumulative_buy_cost, cumulative_rent_cost`
- One row per month (120 rows for 10-year simulation)

Frontend: trigger via download button, open in new tab or use `<a download>`.

### `POST /sensitivity`

What-if analysis. Varies each input parameter, measures impact on buyer/renter NW. Includes 2D heatmap.

Request: same body as `/summary`.
Response: `{ base_buyer_nw, base_renter_nw, base_net_diff, base_buy_score, axes: {param: [SensitivityPoint]}, heatmap: HeatmapOut }`.

### `POST /trend`

Timing analysis. Simulates buying now vs delaying 1–8 quarters.

Request: same body as `/summary` + `max_delay_quarters` (default 8).
Response: `{ points: [TrendPoint] }` with delay_months, aggregate_score, mortgage_rate_used, etc.

### `POST /zip-compare`

Compare up to 16 ZIP codes. If `zip_codes` list is empty, uses neighbors of `zip_code`.

Request: same body as `/summary` + `zip_codes: string[]`.
Response: `{ scores: [ZipScore] }` with per-ZIP buyer/renter NW, aggregate_score, breakeven.

### `POST /llm-summary`

AI-generated narrative analysis. Requires `ANTHROPIC_API_KEY`.

Request: same body as `/summary`.
Response: `{ summary, buy_costs_summary, buy_pros: [], rent_pros: [], buy_costs: [], rent_costs: [], verdict, score }`.

---

## Pro Tier: Saved Scenarios & Alerts

All PRO endpoints require `X-Device-Id` header (UUID v4 from localStorage).

### Device Identity

#### `POST /devices/email`
Register or update email address for a device. Required for receiving alert emails.

```json
// Request
{ "email": "user@example.com" }

// Response 200
{ "status": "ok", "email": "user@example.com" }
```

### Scenarios CRUD

#### `POST /scenarios` → 201

Save a new scenario.

```json
// Request
{
  "name": "My downtown scenario",
  "inputs": { /* full SummaryRequest fields */ },
  "response": { /* optional: cached SummaryResponse */ }
}

// Response 201
{
  "id": "uuid",
  "name": "My downtown scenario",
  "inputs": { ... },
  "response": { ... } | null,
  "created_at": 1711670400.0,
  "updated_at": 1711670400.0
}
```

#### `GET /scenarios`

List all scenarios for this device, ordered by `updated_at` DESC.

```json
// Response 200
{
  "scenarios": [
    { "id": "uuid", "name": "...", "inputs": {...}, "response": {...}, "created_at": ..., "updated_at": ... }
  ]
}
```

#### `GET /scenarios/{id}`

Get a single scenario. Returns 404 if not found or belongs to different device.

#### `POST /scenarios/{id}/run`

Re-run a saved scenario with current market data. Returns a fresh `SummaryResponse` (same shape as `POST /summary`). Also updates the scenario's cached `response_json`.

#### `DELETE /scenarios/{id}` → 204

Delete a scenario and all its alerts. Returns 404 if not found or wrong device.

### Alert Configuration

#### `POST /scenarios/{id}/alerts` → 201

Add an alert to a saved scenario. One alert per type per scenario.

```json
// Request
{
  "alert_type": "threshold" | "shift" | "digest",
  "config": { "shift_months": 6 } | null    // optional, type-specific
}

// Response 201
{
  "id": "uuid",
  "scenario_id": "...",
  "alert_type": "threshold",
  "enabled": true,
  "config": null,
  "last_triggered_at": null,
  "created_at": 1711670400.0
}
```

Alert types:
- **`threshold`** — fires when verdict flips (e.g. "Lean Buy" → "Lean Rent")
- **`shift`** — fires when breakeven moves by ≥3 months (configurable via `config.shift_months`)
- **`digest`** — fires on every data refresh (monthly summary email)

**Error 409**: alert type already exists for this scenario.

#### `GET /scenarios/{id}/alerts`

```json
// Response 200
{ "alerts": [ { "id": "...", "scenario_id": "...", "alert_type": "...", ... } ] }
```

#### `DELETE /scenarios/{id}/alerts` → 204

Delete all alerts for a scenario.

#### `DELETE /scenarios/{id}/alerts/{alert_id}` → 204

Delete a single alert.

### Error Codes (PRO endpoints)

| Code | Meaning |
|------|---------|
| 401 | Missing `X-Device-Id` header |
| 404 | Scenario or alert not found (or belongs to different device) |
| 409 | Duplicate alert type on same scenario |

---

## Frontend Integration Guide

### Minimal Request (2 required fields)

```js
const res = await fetch('/summary', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ monthly_rent: 3500, monthly_budget: 5000 })
});
```

### Multi-Step Form Mapping

| Form Step | Fields |
|-----------|--------|
| **1. About You** | `monthly_rent`, `monthly_budget`, `initial_cash`, `stay_years` |
| **2. Buying** | `zip_code`, `house_price`, `down_payment_pct`, `credit_quality`, `term_years` |
| **3. Costs** | `closing_cost_pct`, `move_in_cost`, `insurance_annual`, `maintenance_rate`, `sell_cost_pct` |
| **4. Advanced** | `risk_appetite`, `yearly_income`, `filing_status`, `other_deductions`, `outlook_preset` |
| **PRO** | `years` (horizon slider), `buy_delay_months`, outlook overrides |

### Device Identity Flow

```js
// On first visit
const deviceId = localStorage.getItem('device_id') || crypto.randomUUID();
localStorage.setItem('device_id', deviceId);

// On all PRO requests
headers: { 'X-Device-Id': deviceId, 'Content-Type': 'application/json' }
```

### Charts to Build

1. **Net Worth Comparison** — `buyer_net_worth` vs `renter_net_worth` lines. Add P25-P75 shaded bands from `percentiles`. Add legends.
2. **Home Value** — `home_value` line with `percentiles.home_value` P25-P75 band. Label as "Median" or "Average".
3. **Cost Breakdown** — stacked areas: `mortgage_payment`, `maintenance`, `property_tax`, `insurance`, `pmi`. Show `tax_savings` as negative offset or separate line. **Add legend** (currently missing). Drops to zero at sell month.
4. **Rent vs Buy Monthly Cost** — `rent` vs `total_housing_cost`. **Add legend**. After sell, both lines show rent.
5. **Equity Growth** — `buyer_equity` line with `percentiles.buyer_equity` band. Drops to zero at sell month.
6. **Cumulative Cost** — `cumulative_buy_cost` vs `cumulative_rent_cost`. **Add legend**.

When `stay_years < years`: draw a vertical dashed line at month `buy_delay_months + stay_years × 12` labeled "Sell" on charts 1, 3, 4, 5.

### Key Metrics

From response root:
- `buy_score` (0–100), `verdict` — the headline recommendation
- `breakeven_month` — **sustained** breakeven: when buyer durably pulls ahead and stays ahead through end of horizon. `null` if buyer never durably leads. This is NOT the first crossing — if buyer briefly leads at month 20 then falls behind until month 90, `breakeven_month = 90`.
- `crossing_count` — how many times the buyer/renter lead swaps. Helps communicate confidence:
  - `0`: one side always wins (clear signal)
  - `1`: clean crossover (standard breakeven story)
  - `2-3`: volatile — timing matters, result is sensitive to assumptions
  - `4+`: essentially a toss-up, non-financial factors should drive the decision

**Frontend display suggestions:**
| `crossing_count` | Breakeven display |
|:-:|---|
| 0-1 | "Buying pulls ahead at Year X" or "Renting wins throughout" |
| 2-3 | "Buying pulls ahead for good at Year X, but the lead changes N times" |
| 4+ | "It's a toss-up — the lead changes N times over the horizon" |

From `monthly[last]`:
- Net worth difference: `buyer_net_worth - renter_net_worth`
- Final home value, total equity built, total housing costs

### Scenario Save/Load Flow

1. User runs simulation → sees results
2. Clicks "Save" → `POST /scenarios` with form inputs + cached response
3. "My Scenarios" panel → `GET /scenarios` → list with "Re-run" and "Delete" buttons
4. "Re-run" → `POST /scenarios/{id}/run` → display fresh results (same response shape as `/summary`)
5. Alert toggles → `POST /scenarios/{id}/alerts` per type. Prompt for email if not set.
