# How We Calculate Your Results

A plain-English guide to how Rent vs Buy works, what the numbers mean, and what assumptions go into them.

---

## The Core Question

We answer: **"If you have $X to spend on housing each month, are you better off buying a home or renting and investing the difference?"**

Both options use the same monthly budget. The buyer spends it on mortgage, taxes, insurance, and maintenance. The renter spends less on rent and invests the surplus. After your chosen time horizon, we compare total wealth.

---

## How the Simulation Works

We don't use a single prediction. We run **hundreds of simulations**, each with slightly different market conditions — some where home values rise fast, some where they're flat, some where there's a downturn. This gives you a range of outcomes, not just one number.

**What varies across simulations:**
- How much your home appreciates (or doesn't)
- How the stock market performs (for invested savings)
- How rent and general costs inflate
- Whether a market correction happens (if you selected a cautious or pessimistic outlook)
- What mortgage rates look like in the future (relevant if you delay buying or refinance)

**What stays the same:**
- Your inputs (rent, budget, savings, income)
- The mortgage terms you selected
- The rules of how mortgages, taxes, and investments work

---

## Key Concepts

### Net Worth Comparison

Your **net worth** in each scenario:

- **Buyer**: Home equity (what the home is worth minus what you owe, after selling costs) + investment portfolio
- **Renter**: Investment portfolio only (but it grows faster because rent is cheaper than owning)

We compare these at the end of your time horizon. The winner is whoever has more total wealth.

### Breakeven Point

The month where buying **durably** pulls ahead of renting and stays ahead through the end of the horizon. If the lead changes back and forth, we report when buying takes the lead for good — not the first time it briefly edges ahead.

### Buy Score (0-100)

A composite rating combining:
- How much wealthier buying makes you (40%)
- How quickly buying pulls ahead (25%)
- Whether monthly costs fit your budget (15%)
- How much equity you've built (20%)

Higher = buying is more favorable. Below 40 = renting is clearly better. Above 70 = buying is clearly better. 40-70 = it depends on personal factors.

### Confidence Level

Based on how stable the result is across our simulations:
- **High**: The winner is clear and doesn't change much across different market scenarios
- **Moderate**: The result holds in most scenarios but is sensitive to market conditions
- **Low**: The lead changes multiple times — the outcome depends heavily on timing and luck

---

## What Goes Into the Monthly Cost of Buying

| Component | What it is |
|---|---|
| **Mortgage payment** | Principal + interest. Fixed for the life of the loan (unless you refinance). |
| **Property tax** | Based on your area's tax rate, scales with home value. |
| **Home insurance** | Annual premium, scales modestly with home value. |
| **Maintenance** | Estimated at 1% of home value per year (industry standard). |
| **PMI** | Private mortgage insurance — required if you put less than 20% down. Cancels once you reach 20% equity. |
| **Tax savings** | Mortgage interest and property taxes may be tax-deductible if you itemize. We compare itemized vs. standard deduction and apply the larger benefit. |

Your **total housing cost** = mortgage + tax + insurance + maintenance + PMI - tax savings.

---

## How We Model the Future

### Home Values

We use the **long-term national average of ~3.5% per year** as the expected appreciation rate. If you provide a ZIP code, we incorporate Zillow's short-term local forecast for the first year, then blend toward the national average.

Individual simulations vary around this average — some see 7% years, others see flat or slightly negative years. This is how real housing markets behave.

### Rent Growth

Rent grows with inflation (CPI), plus small random variation. Historically, rent has grown about 3-4% per year on average.

### Investment Returns

Surplus cash (what you don't spend on housing) is invested. How it grows depends on your risk setting:

| Setting | What happens | Typical return |
|---|---|---|
| **Savings only** | Cash in a high-yield savings account | ~4.5% per year, guaranteed |
| **Conservative** | Half-exposure to the stock market | Lower returns, lower risk |
| **Moderate** (default) | Full stock market exposure | ~7-10% per year historically, with volatility |
| **Aggressive** | 1.5x leveraged stock exposure | Higher potential returns, much more volatility |

### Mortgage Rates

We use the current rate from federal data (FRED) as your starting rate. For future projections (relevant if you delay buying or for refinance opportunities), we forecast rates using:

- **Near-term**: Recent momentum (are rates trending up or down?)
- **Medium-term**: Blending toward the 5-year historical average
- **Long-term**: Settling toward the 20-year historical average (~5.2%)

Rates can go up or down in each simulation — there's no single prediction.

### Market Corrections

If you select a cautious, pessimistic, or crisis outlook, we model the possibility of a housing and/or stock market downturn:

- **How likely**: Ranges from 10% (cautious) to 50% (crisis)
- **How deep**: Ranges from 10% (cautious) to 30% (crisis) decline
- **Recovery**: Markets partially recover after a downturn — housing recovers about 50% of the drop over 5 years by default, stocks recover 70% over 3 years

A correction doesn't mean permanent loss. It means a temporary dip followed by a partial or full recovery, similar to what happened after 2008 or 2020.

---

## Refinancing

By default, we model the possibility of refinancing your mortgage if rates drop significantly. This is realistic — most homeowners refinance at least once during a 30-year mortgage.

**How it works in our model:**
- We check each month whether market rates have dropped at least **1 percentage point** below your locked rate
- You must have owned for at least **2 years** before refinancing
- Refinancing costs **$5,000** in closing fees
- You can refinance **once** during the simulation

By default, the closing costs are **rolled into the new loan** (added to your balance), so you don't need cash on hand. This slightly increases your loan amount but avoids depleting savings. PRO users can change this to pay out of pocket instead.

These are conservative assumptions. In practice, many people refinance with a 0.5-0.75% rate drop and lower closing costs.

**What you'll see**: If refinancing happens, your monthly mortgage payment drops partway through the simulation. The `refi_summary` in your results shows when it's likely to happen and how much you'd save.

---

## Selling Your Home

If you set a "plan to stay" duration shorter than your planning horizon, we model selling:

1. **During ownership**: You build equity (home value minus what you owe)
2. **At sale**: You pay selling costs (typically 6% of home value — agent fees, closing costs, etc.) and receive the remaining equity as cash
3. **After sale**: You become a renter again and invest the proceeds

Note: **selling costs are already factored into your net worth every month**, not just at the sale date. We always show "what you'd walk away with if you sold today," so there's no sudden cliff when you sell.

---

## What We Don't Model

For transparency, here's what our simulation **does not** account for:

- **Emotional value of homeownership** — stability, customization, community roots
- **Exact local conditions** — school districts, neighborhood trends, zoning changes
- **Your specific tax situation** — we estimate based on income bracket and filing status, but a tax advisor knows your full picture
- **Rental market disruptions** — landlord selling, rent control changes, lease uncertainty
- **Home improvement ROI** — renovations that increase home value
- **Inflation on non-housing expenses** — we focus on the housing decision in isolation

---

## Glossary

| Term | Definition |
|---|---|
| **Amortization** | The schedule of mortgage payments over time. Early payments are mostly interest; later payments are mostly principal. |
| **DTI (Debt-to-Income)** | Your total monthly debt payments divided by gross monthly income. Lenders typically cap this at 43%. |
| **Equity** | The portion of your home you actually own: home value minus remaining mortgage balance minus selling costs. |
| **LTV (Loan-to-Value)** | Your mortgage balance divided by home value. PMI is required when LTV exceeds 80%. |
| **Monte Carlo simulation** | A technique that runs hundreds of scenarios with random variation to show a range of possible outcomes instead of a single prediction. |
| **PMI** | Private mortgage insurance. A monthly fee charged when your down payment is less than 20%. It protects the lender, not you. Cancels when you reach 20% equity. |
| **SALT cap** | State and local tax deduction cap ($40,000). Limits how much of your property taxes and state income taxes you can deduct on federal returns. |
| **Refinancing** | Replacing your current mortgage with a new one at a lower rate. Involves closing costs but can significantly reduce monthly payments. |
| **Breakeven** | The point in time when buying becomes financially better than renting (and stays that way). |
| **Planning horizon** | How far into the future the simulation runs. Default: 10 years. |
| **Stay duration** | How long you plan to own before selling. Can be shorter than the planning horizon. |
