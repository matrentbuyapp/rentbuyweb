# Rent vs Buy — Frontend Architecture

## Stack
- **Next.js 15.4** with static export (`output: "export"`)
- **React 19.1** with TypeScript 6.0
- **Recharts 2.15** for all charts
- **Tailwind CSS 4.2** (PostCSS plugin, no tailwind.config)
- No state management library — React hooks + prop drilling

## Running

```bash
cd web
npm install
npm run dev          # http://localhost:3000 (requires API at localhost:8000)
npm run build        # static export to web/out/
```

Environment:
- `NEXT_PUBLIC_API_URL` — API base URL (default: `http://localhost:8000`)

**Important**: Do not run `npm run build` while the dev server is active — it overwrites `.next` and breaks CSS.

## Deployment
Static export (`web/out/`) → S3 bucket + CloudFront. Domain: `rentbuysellapp.com`.

---

## Pages

### `/` — Calculator
- Hero: rent, budget, savings + estimated home price (from ZIP lookup or national median)
- Client-side validation hints (budget < rent, insufficient cash, low DP)
- Results: KeyMetrics (4 cards) + 5 charts + warnings banner
- Settings: 5 accordion sections with Pro controls inline via `ProGate`
- "Dig Deeper": 6 Pro feature cards (expandable previews for free, links for Pro)
- Saved Scenarios section (Pro only)
- Sticky bottom bar: quick stats (price @ rate, monthly cost, verdict) + action buttons
- Footer: About + data attribution

### `/insights` — Pro Insights
- Context banner: scenario summary loaded from localStorage (or server via cache_key)
- 6 Pro sections with app screenshots as placeholders (AI Summary, What-If, Trend, ZIP Compare, Scenarios, Buying Memo)
- Free users see grayed previews with upgrade CTA
- Pro users see real content (when built) or "coming soon"

---

## Directory Structure

```
web/src/
├── app/
│   ├── layout.tsx              — Root layout (metadata, Inter font)
│   ├── page.tsx                — Calculator page
│   ├── insights/page.tsx       — Pro Insights page
│   └── globals.css             — Tailwind + custom styles
├── lib/
│   ├── types.ts                — TypeScript interfaces (mirrors api/API.md)
│   ├── api.ts                  — Fetch wrappers, formToRequest(), Pro CRUD
│   ├── defaults.ts             — DEFAULT_FORM_VALUES
│   ├── device.ts               — getDeviceId() — localStorage UUID for X-Device-Id
│   ├── formatters.ts           — formatCurrency, formatPercent, formatCompact, etc.
│   ├── premium.ts              — PRO_FEATURES array (6 features)
│   └── resultStore.ts          — localStorage bridge for cross-page result sharing
├── hooks/
│   ├── useSimulation.ts        — Form state, API call, result storage
│   ├── useScenarios.ts         — Pro: scenario CRUD
│   ├── usePremium.ts           — isPro from localStorage
│   └── useZipPrices.ts         — Lazy-loads ZIP price lookup data
├── components/
│   ├── form/
│   │   ├── SettingsPanel.tsx   — 5 accordions with Pro controls via ProGate
│   │   └── CrashSlider.tsx     — Outlook preset slider (optimistic → crisis)
│   ├── results/
│   │   ├── ResultsDashboard.tsx — KeyMetrics + chart grid + warnings + ProInsights
│   │   ├── KeyMetrics.tsx       — 4 cards (verdict, breakeven with crossing_count, home value, rate)
│   │   ├── NetWorthChart.tsx    — Buyer vs Renter with breakeven + sell lines
│   │   ├── HomeValueChart.tsx   — With percentile confidence bands (p10-p90)
│   │   ├── RentVsBuyChart.tsx   — Monthly cost comparison with sell line
│   │   ├── CostBreakdownChart.tsx — Stacked areas + tax savings dashed line + sell line
│   │   ├── EquityGrowthChart.tsx  — With sell line
│   │   ├── ProInsights.tsx      — 6-card grid, expandable previews (free), links to /insights (Pro)
│   │   └── ChartCard.tsx        — Reusable chart wrapper
│   ├── scenarios/
│   │   ├── SaveButton.tsx       — Inline name input after results
│   │   ├── ScenarioList.tsx     — Expandable cards with re-run, view, delete
│   │   └── AlertToggles.tsx     — Per-scenario alert checkboxes + email prompt
│   └── ui/
│       ├── Accordion.tsx
│       ├── InputField.tsx       — With onFocus support for ZIP lazy-load
│       ├── SelectField.tsx
│       ├── ChartCard.tsx
│       ├── ProBadge.tsx
│       └── ProGate.tsx          — Shows children for Pro, badge+label for free
```

---

## Data Flow

```
FormData (display units: 8%, $2000)
    ↓ formToRequest()
SummaryRequest (API units: 0.08, 2000)
    ↓ POST /summary
SummaryResponse (includes warnings, percentiles, cache_key, data_vintage)
    ↓ storeResult() → localStorage
    ↓ passed as props
ResultsDashboard → charts, metrics, ProInsights
    ↓ link
/insights page → loadResult() from localStorage
```

### Key Conversions in `formToRequest()`
- Percentage fields (down_payment_pct, closing_cost_pct, etc.): ÷ 100
- mortgage_rate, rate_target: string → number ÷ 100, empty → null
- house_price: empty string → null (triggers auto-estimation)
- zip_code: empty string → null
- stay_years: equals years → null (API convention)
- crash overrides: null = use preset defaults
- rate_volatility_scale: "1.0" → null (default)

---

## Pro Tier Architecture

### Pro Controls (inline in settings via ProGate)

| Section | Control | Free users see |
|---------|---------|----------------|
| Where & What | Planning horizon (2-15y) | PRO badge + label |
| Where & What | Buy delay (0-24mo) | PRO badge + label |
| Your Mortgage | Rate target (%) | PRO badge + label |
| Your Mortgage | Rate volatility (0.5-2×) | PRO badge + label |
| Market Outlook | Housing crash (prob, drop, recovery%, time) | PRO badge + label |
| Market Outlook | Stock crash (prob, drop, recovery%, time) | PRO badge + label |

### Pro Functions (separate experiences on /insights)

| Feature | API Endpoint | Entry Point |
|---------|-------------|-------------|
| AI Summary | POST /llm-summary | Dig Deeper card → /insights#ai-summary |
| What-If Analysis | POST /sensitivity | Dig Deeper card → /insights#sensitivity |
| Best Time to Buy | POST /trend | Dig Deeper card → /insights#trend |
| ZIP Comparison | POST /zip-compare | Dig Deeper card → /insights#zip-compare |
| Save & Compare | /scenarios CRUD | My Scenarios section + /insights#scenarios |
| Buying Memo (PDF) | Not yet built | /insights#buying-memo |
| CSV Export | POST /summary/csv | Download button (TBD) |
| Rate Forecast Chart | percentiles.mortgage_rate | TBD |

### Device Identity
- UUID v4 generated on first visit, stored in localStorage as `device_id`
- Sent as `X-Device-Id` header on all Pro requests
- No auth flow yet — device = identity for MVP

---

## Result Caching & Reproducibility (pending API support)

### Problem
Separate API calls for /summary, /sensitivity, /llm-summary run independent MC simulations.
Same inputs can give slightly different results. LLM text could contradict numbers.
Data refresh between calls means results from different data vintages.

### Solution: Content-Addressed Caching + Permanent Scenario Storage

**Two storage layers:**

1. **Result Cache** (transient, server-side, shared across users)
   - Key: SHA-256 of canonical(inputs) + data_vintage
   - Avoids redundant MC runs for identical requests
   - Columns populated lazily (summary first, pro insights on demand)
   - Prunable after 30-90 days

2. **Scenario Storage** (permanent, per-device)
   - Full result snapshot copied from cache when user saves
   - Never pruned — user's data, persists until explicitly deleted
   - Includes all computed results (summary + pro insights + LLM text)
   - Stores data_vintage + cache_key for reference

**API response additions needed:**
```typescript
interface SummaryResponse {
  // ... existing fields ...
  cache_key: string;       // hash of inputs + data_vintage
  data_vintage: string;    // ISO date of market.db last refresh
}
```

**Frontend behavior:**
- Display data_vintage in context banner and bottom bar ("Data: Mar 2026")
- Stale indicator when saved scenario vintage < current
- Viewing saved scenario returns stored results (never re-computes)
- Re-run checks if data changed; if unchanged, returns identical cached results

**Consistency guarantees:**
- Same inputs + same data_vintage = same numeric results (deterministic seed)
- Same cache_key = same LLM text (generated once, stored permanently)
- Cross-device: cache is server-side, same inputs hit same cache regardless of device

---

## Defaults (defaults.ts)

```
monthly_rent: 1800
monthly_budget: 2500
initial_cash: 60000
yearly_income: 100000
down_payment_pct: 8
closing_cost_pct: 3
maintenance_rate: 1
insurance_annual: 2000
sell_cost_pct: 5
years: 10
stay_years: 10
outlook_preset: "historical"
risk_appetite: "moderate"
credit_quality: "good"
term_years: 30
All Pro crash overrides: null (use preset)
rate_target: "" (auto)
rate_volatility_scale: "1.0" (normal)
```
