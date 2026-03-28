# Rent vs Buy API — Endpoint Reference

Base URL: `https://api.rentbuysellapp.com` (production) or `http://localhost:8000` (dev)

## `POST /summary`

Main endpoint. Runs the Monte Carlo simulation and returns a month-by-month comparison of buying vs renting.

### Request Body

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
  "risk_appetite": "moderate",   // "conservative" (0.5x) | "moderate" (1x) | "aggressive" (1.5x). Default: "moderate"

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
  "years": 10,                   // Simulation horizon in years. Default: 10
  "num_simulations": 500,        // Number of MC runs. Default: 500
  "buy_delay_months": 0,         // Months to wait before purchasing. Default: 0

  // === CRASH OUTLOOK (slider) ===
  "crash_outlook": "possible"    // "none" | "unlikely" | "possible" | "likely" | "very_likely". Default: "possible"
}
```

#### Crash Outlook Presets

| Value | Probability | Housing Drop | Stock Drop |
|-------|------------|-------------|------------|
| `none` | 0% | 0% | 0% |
| `unlikely` | 5% | 15% | 20% |
| `possible` | 15% | 20% | 25% |
| `likely` | 30% | 25% | 30% |
| `very_likely` | 50% | 30% | 35% |

#### Credit Quality Impact on Mortgage Rate

| Quality | Rate Premium | With 20% Down | With 5% Down |
|---------|-------------|---------------|-------------|
| `excellent` | +0.00% | -0.125% | +0.25% |
| `great` | +0.125% | +0.125% | +0.375% |
| `good` | +0.375% | +0.375% | +0.625% |
| `average` | +0.75% | +0.75% | +1.00% |
| `mediocre` | +1.25% | +1.25% | +1.50% |
| `poor` | +2.00% | +2.00% | +2.25% |

### Response

```json
{
  "house_price": 650000,          // Actual house price used (may be auto-estimated)
  "mortgage_rate": 0.06875,       // Effective annual rate (base + credit adj)
  "property_tax_rate": 0.0142,    // Annual property tax rate for this ZIP
  "avg_buyer_net_worth": 620000,  // Buyer NW at end of simulation (averaged across MC runs)
  "avg_renter_net_worth": 580000, // Renter NW at end of simulation

  "monthly": [                    // Array of 120 objects (10 years × 12 months)
    {
      "home_value": 650000,       // Current estimated home value ($)
      "mortgage_payment": 3740,   // Monthly mortgage payment ($)
      "interest_payment": 3500,   // Interest portion of mortgage ($)
      "principal_payment": 240,   // Principal portion of mortgage ($)
      "remaining_balance": 584760,// Remaining loan balance ($)
      "maintenance": 541,         // Monthly maintenance cost ($)
      "property_tax": 769,        // Monthly property tax ($)
      "insurance": 200,           // Monthly insurance ($)
      "pmi": 197,                 // Monthly PMI ($, 0 after 80% LTV)
      "tax_savings": 502,         // Monthly tax savings from itemizing ($)
      "total_housing_cost": 4945, // Sum: mortgage + maint + tax + ins + pmi - tax_savings
      "rent": 3500,               // What rent would be this month ($)
      "budget": 5000,             // Inflation-adjusted budget ($)
      "buyer_investment": 12000,  // Buyer's investment portfolio value ($)
      "renter_investment": 152000,// Renter's investment portfolio value ($)
      "buyer_equity": 45000,      // Home equity: home_value × (1 - sell_cost) - balance
      "buyer_net_worth": 57000,   // buyer_equity + buyer_investment
      "renter_net_worth": 152000, // renter_investment (renter has no equity)
      "cumulative_buy_cost": 4945,// Total spent on housing (buying) so far
      "cumulative_rent_cost": 3500// Total spent on rent so far
    }
    // ... 119 more months
  ]
}
```

### Key Relationships

```
total_housing_cost = mortgage_payment + maintenance + property_tax + insurance + pmi - tax_savings
buyer_net_worth = buyer_equity + buyer_investment
buyer_equity = home_value × (1 - sell_cost_pct) - remaining_balance
renter_net_worth = renter_investment
```

The renter invests `budget - rent` each month. The buyer invests `budget - total_housing_cost`.
Both earn stock market returns on their investment portfolios.

---

## `GET /health`

Returns `{"status": "ok"}`. Use for load balancer health checks.

---

## Frontend Integration Guide

### Minimal Request (2 required fields)

```js
const res = await fetch('/summary', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    monthly_rent: 3500,
    monthly_budget: 5000
  })
});
const data = await res.json();
```

This will auto-estimate a house price, look up current mortgage rates, and use defaults for everything else.

### Multi-Step Form Mapping

| Form Step | Fields |
|-----------|--------|
| **1. About You** | `monthly_rent`, `monthly_budget`, `initial_cash` |
| **2. Buying** | `zip_code`, `house_price`, `down_payment_pct`, `credit_quality`, `term_years`, `buy_delay_months` |
| **3. Costs** | `closing_cost_pct`, `move_in_cost`, `insurance_annual`, `maintenance_rate`, `sell_cost_pct` |
| **4. Advanced** | `risk_appetite`, `yearly_income`, `filing_status`, `other_deductions`, `crash_outlook` |

### Charts to Build

1. **Net Worth Comparison** (primary) — line chart
   - X: months (0–120)
   - Y: `buyer_net_worth` vs `renter_net_worth`
   - Highlight crossover point (buyer overtakes renter)

2. **Home Value** — line chart
   - X: months
   - Y: `home_value`

3. **Buyer Cost Breakdown** — stacked area or bar
   - `mortgage_payment`, `maintenance`, `property_tax`, `insurance`, `pmi`
   - Subtract `tax_savings` (show as negative/offset)

4. **Rent vs Buy Monthly Cost** — line chart
   - `rent` vs `total_housing_cost`

5. **Equity Growth** — area chart
   - `buyer_equity` over time

6. **Cumulative Cost** — line chart
   - `cumulative_buy_cost` vs `cumulative_rent_cost`

### Crash Slider

Map a 5-position slider to `crash_outlook`:
```
1 ── 2 ── 3 ── 4 ── 5
none  unlikely  possible  likely  very_likely
```

When the user moves the slider, re-call `/summary` with the new `crash_outlook`.
The backend caches market paths, so subsequent calls with different crash settings
are fast (~0.2s for 500 simulations).

### Key Metrics to Highlight

From `monthly[119]` (year 10):
- Net worth difference: `buyer_net_worth - renter_net_worth`
- Final home value: `home_value`
- Total equity built: `buyer_equity`
- Total housing cost paid: `cumulative_buy_cost`

From `monthly[59]` (year 5):
- Same metrics for mid-horizon view

Breakeven month:
```js
const breakeven = data.monthly.findIndex(m => m.buyer_net_worth > m.renter_net_worth);
```
