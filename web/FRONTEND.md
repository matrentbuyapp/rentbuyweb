# Rent vs Buy — Frontend Architecture

## Stack
- **Next.js 15.4** with static export (`output: "export"` in next.config.ts)
- **React 19.1** with TypeScript 6.0 (strict mode)
- **Recharts 2.15** for all charts
- **Tailwind CSS 4.2** for styling
- **No state management library** — React hooks + prop drilling

## Running

```bash
cd web
npm install
npm run dev          # http://localhost:3000 (requires API at localhost:8000)
npm run build        # static export to web/out/
```

Environment:
- `NEXT_PUBLIC_API_URL` — API base URL (default: `http://localhost:8000`)

**Important**: Do not run `npm run build` while the dev server is active — it breaks CSS output.

## Deployment
Static export (`web/out/`) → S3 bucket + CloudFront. Domain: `rentbuysellapp.com`.

---

## Directory Structure

```
web/src/
├── app/
│   ├── layout.tsx            — Root layout (metadata, fonts)
│   ├── page.tsx              — Main page (assembles form + results)
│   └── globals.css           — Global styles + Tailwind imports
├── lib/                      — Shared utilities (no React)
│   ├── types.ts              — TypeScript interfaces (mirrors api/API.md)
│   ├── api.ts                — Fetch wrappers + formToRequest() conversion
│   ├── defaults.ts           — DEFAULT_FORM_VALUES
│   ├── device.ts             — getDeviceId() — localStorage UUID
│   ├── formatters.ts         — formatCurrency(), formatPercent(), etc.
│   └── premium.ts            — PRO tier feature flags
├── hooks/                    — Custom React hooks
│   ├── useSimulation.ts      — Form state + API call + results caching
│   ├── useScenarios.ts       — PRO: load/save/delete saved scenarios
│   └── usePremium.ts         — PRO tier detection
├── components/
│   ├── form/                 — Input form (4 steps)
│   │   ├── SimulatorForm.tsx — Orchestrates steps
│   │   ├── StepAboutYou.tsx  — Step 1: rent, budget, savings
│   │   ├── StepBuying.tsx    — Step 2: ZIP, price, down %, credit, term
│   │   ├── StepCosts.tsx     — Step 3: closing, insurance, maintenance, sell
│   │   ├── StepAdvanced.tsx  — Step 4: income, deductions, risk, outlook
│   │   ├── SettingsPanel.tsx — Collapsible settings in results view
│   │   └── CrashSlider.tsx   — Market outlook preset selector
│   ├── results/              — Output visualizations
│   │   ├── ResultsDashboard.tsx    — Orchestrates all result panels
│   │   ├── KeyMetrics.tsx          — Score, verdict, breakeven, NW summary
│   │   ├── NetWorthChart.tsx       — Buyer vs Renter NW (with percentile bands)
│   │   ├── HomeValueChart.tsx      — Home value over time
│   │   ├── RentVsBuyChart.tsx      — Monthly cost comparison
│   │   ├── CostBreakdownChart.tsx  — Stacked housing cost components
│   │   ├── EquityGrowthChart.tsx   — Equity accumulation
│   │   ├── CumulativeCostChart.tsx — Total spend comparison
│   │   ├── ProInsights.tsx         — PRO: AI narrative, sensitivity
│   │   └── ChartCard.tsx           — Reusable chart container
│   ├── scenarios/            — PRO: Scenario management
│   │   ├── ScenarioList.tsx  — List + re-run + delete
│   │   ├── SaveButton.tsx    — Save current simulation
│   │   └── AlertToggles.tsx  — Alert type toggles per scenario
│   └── ui/                   — Reusable primitives
│       ├── InputField.tsx    — Labeled text/number input
│       ├── SelectField.tsx   — Labeled dropdown
│       ├── Accordion.tsx     — Collapsible section
│       ├── StepIndicator.tsx — Form progress indicator
│       └── ProBadge.tsx      — PRO feature badge
```

---

## Data Flow

```
FormData (UI state, strings/numbers in display units)
    ↓ formToRequest() in lib/api.ts
SummaryRequest (API contract, decimals)
    ↓ POST /summary
SummaryResponse (API contract)
    ↓ passed as props
ResultsDashboard → individual chart components
```

### Key Conversions in `formToRequest()`
- Percentage fields (down_payment_pct, closing_cost_pct, etc.): divided by 100
- Mortgage rate: divided by 100 (user enters 6.5, API expects 0.065)
- house_price, mortgage_rate: empty string → null (triggers auto-estimation)
- zip_code: empty string → null

---

## Type Contracts

**Source of truth**: `api/API.md` defines the API contract. `web/src/lib/types.ts` must mirror it exactly.

### Core Types (types.ts)

| Interface | Maps to | Notes |
|-----------|---------|-------|
| `SummaryRequest` | POST /summary body | 22+ optional fields |
| `SummaryResponse` | POST /summary response | buy_score, verdict, breakeven_month, monthly[], percentiles |
| `MonthlyData` | Each element of monthly[] | 19 fields per month |
| `PercentileBands` | Each metric's confidence bands | p10, p25, p50, p75, p90 arrays |
| `Percentiles` | percentiles object | buyer_net_worth, renter_net_worth, home_value, buyer_equity |
| `Scenario` | GET/POST /scenarios | id, name, inputs, response, timestamps |
| `Alert` | GET/POST /scenarios/{id}/alerts | id, alert_type, enabled, config |
| `FormData` | Internal form state | String types for numeric inputs (allows empty) |

---

## Component Ownership

| Component | Data Source | API Dependency |
|-----------|-----------|----------------|
| `SimulatorForm` | FormData state | None (local) |
| `ResultsDashboard` | SummaryResponse prop | POST /summary |
| `KeyMetrics` | SummaryResponse | None (derived) |
| `*Chart` components | SummaryResponse.monthly[] | None (derived) |
| `ProInsights` | SummaryResponse + LLM | POST /llm-summary |
| `ScenarioList` | Scenario[] | GET /scenarios, POST /scenarios/{id}/run |
| `SaveButton` | FormData + SummaryResponse | POST /scenarios |
| `AlertToggles` | Alert[] | POST/DELETE /scenarios/{id}/alerts |

---

## State Management

No external state library. State lives in hooks:

- **`useSimulation`** — owns `FormData`, `SummaryResponse | null`, loading/error state. Calls `postSummary()`.
- **`useScenarios`** — owns `Scenario[]`. Calls scenario CRUD endpoints. Depends on device ID.
- **`usePremium`** — derived from scenario count or feature flag. No API call.

---

## Default Form Values (defaults.ts)

```ts
monthly_rent: 1800
monthly_budget: 2500
initial_cash: 60000
yearly_income: 100000
down_payment_pct: 8        // display value (÷100 before API call)
closing_cost_pct: 3
maintenance_rate: 1
sell_cost_pct: 6
years: 10
num_simulations: 500
crash_outlook: "none"      // NOTE: maps to backend's "outlook_preset" field
```
