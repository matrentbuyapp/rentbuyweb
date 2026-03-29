"""AI-powered narrative summary using Claude API.

Takes simulation results and generates a plain-English analysis
with pros/cons, cost breakdown, verdict, and a buy score (0-100).
"""

import os
import json
from dataclasses import dataclass
from simulator import SimulationResult, MonthlySnapshot


@dataclass
class LLMSummaryResult:
    summary: str
    buy_costs_summary: str
    buy_pros: list[str]
    rent_pros: list[str]
    buy_costs: list[str]
    rent_costs: list[str]
    verdict: str
    score: int  # 0-100, higher = buying more recommended


def _extract_summary_stats(result: SimulationResult) -> dict:
    """Pull key metrics from simulation result for the LLM prompt."""
    m = result.monthly
    months = len(m)
    final = m[-1]
    first_own = next((s for s in m if s.mortgage_payment > 0), m[0])

    # Sustained breakeven: when buyer durably pulls ahead
    breakeven = None
    n = len(m)
    if n > 0 and m[-1].buyer_net_worth > m[-1].renter_net_worth:
        for i in range(n - 1, -1, -1):
            if m[i].buyer_net_worth <= m[i].renter_net_worth:
                breakeven = i + 1 if i + 1 < n else None
                break
        else:
            breakeven = 0

    # Max renter advantage
    max_renter_lead = max(
        (s.renter_net_worth - s.buyer_net_worth for s in m),
        default=0,
    )

    # Yearly home values
    yearly_home = [m[min(y * 12 + 11, months - 1)].home_value for y in range(months // 12)]

    # Months where buyer cost exceeds budget
    months_over_budget = sum(1 for s in m if s.total_housing_cost > s.budget and s.mortgage_payment > 0)

    return {
        "home_price": result.house_price_used,
        "mortgage_rate": result.mortgage_rate_used,
        "property_tax_rate": result.property_tax_rate,
        "down_payment": first_own.home_value * 0.1,  # approximate from context
        "monthly_mortgage": first_own.mortgage_payment,
        "first_month": {
            "mortgage": first_own.mortgage_payment,
            "maintenance": first_own.maintenance,
            "property_tax": first_own.property_tax,
            "insurance": first_own.insurance,
            "pmi": first_own.pmi,
            "tax_savings": first_own.tax_savings,
            "total_housing_cost": first_own.total_housing_cost,
            "rent": first_own.rent,
        },
        "last_month": {
            "mortgage": final.mortgage_payment,
            "maintenance": final.maintenance,
            "property_tax": final.property_tax,
            "insurance": final.insurance,
            "pmi": final.pmi,
            "tax_savings": final.tax_savings,
            "total_housing_cost": final.total_housing_cost,
            "rent": final.rent,
        },
        "starting_rent": m[0].rent,
        "ending_rent": final.rent,
        "buyer_net_worth": final.buyer_net_worth,
        "renter_net_worth": final.renter_net_worth,
        "net_diff": final.buyer_net_worth - final.renter_net_worth,
        "buyer_equity": final.buyer_equity,
        "breakeven_month": breakeven,
        "max_renter_lead": max_renter_lead,
        "yearly_home_values": yearly_home,
        "total_tax_savings": sum(s.tax_savings for s in m),
        "total_pmi": sum(s.pmi for s in m),
        "pmi_months": sum(1 for s in m if s.pmi > 0),
        "avg_maintenance": sum(s.maintenance for s in m) / months if months > 0 else 0,
        "total_insurance": sum(s.insurance for s in m),
        "months_over_budget": months_over_budget,
        "cumulative_buy_cost": final.cumulative_buy_cost,
        "cumulative_rent_cost": final.cumulative_rent_cost,
    }


def build_prompt(result: SimulationResult, sell_cost_pct: float) -> str:
    """Build the LLM prompt from simulation results."""
    s = _extract_summary_stats(result)

    breakeven_text = (
        "Buying never surpasses renting in the simulation period."
        if s["breakeven_month"] is None
        else f"Buying overtakes renting at month {s['breakeven_month']} (year {s['breakeven_month'] // 12 + 1})."
    )

    tax_text = (
        "Tax savings are zero — itemizing doesn't beat the standard deduction here."
        if s["total_tax_savings"] == 0
        else f"Tax savings over the period total ${s['total_tax_savings']:,.0f}."
    )

    pmi_text = (
        f"PMI is paid for {s['pmi_months']} months (${s['total_pmi']:,.0f} total)."
        if s["total_pmi"] > 0
        else "No PMI — down payment is sufficient."
    )

    return f"""You are a straightforward financial advisor helping someone decide whether to buy a home or keep renting.
Be honest, specific, and empathetic. The user is probably interested in buying — don't push either way, but use the actual numbers.

Keep it under 800 words. Talk directly to the user ("you", "your").

### Key Numbers
- House price: ${s['home_price']:,.0f}
- Mortgage rate: {s['mortgage_rate']:.2%}
- Monthly mortgage: ${s['monthly_mortgage']:,.0f}
- Rent now: ${s['starting_rent']:,.0f} → ${s['ending_rent']:,.0f} at end of period
- {breakeven_text}
- Net worth at end: buyer ${s['buyer_net_worth']:,.0f}, renter ${s['renter_net_worth']:,.0f} — difference ${s['net_diff']:+,.0f}
- Max renter lead during the period: ${s['max_renter_lead']:,.0f}
- Buyer equity at end: ${s['buyer_equity']:,.0f}
- {tax_text}
- {pmi_text}
- Insurance total: ${s['total_insurance']:,.0f}
- Avg maintenance: ${s['avg_maintenance']:,.0f}/mo
- {s['months_over_budget']} months had costs exceeding budget
- Yearly home values: {[f'${v:,.0f}' for v in s['yearly_home_values']]}
- Likelihood to sell within 10 years implied by sell cost: {sell_cost_pct:.0%}

### First month cost breakdown (buying)
{json.dumps(s['first_month'], indent=2)}

### Last month cost breakdown (buying)
{json.dumps(s['last_month'], indent=2)}

### Instructions
Don't restate raw numbers the user can see — interpret them. Focus on:
- What the difference means in practical terms (extra cash on hand, not abstract NW)
- Whether the timing matters (early years favor renter or buyer?)
- Whether the home value trajectory helps or hurts
- Whether the costs are reasonable or strained

Avoid generic advice ("owning provides stability"). Be concrete and specific.
When discussing equity, say "build equity" not "gain equity."
Address the user as someone with basic financial knowledge.

Respond in JSON:
{{
  "summary": "2-3 paragraph analysis",
  "buy_costs_summary": "1-2 sentences about whether the costs look normal or have outliers",
  "buy_pros": ["specific pro 1", "specific pro 2", "specific pro 3"],
  "rent_pros": ["specific pro 1", "specific pro 2", "specific pro 3"],
  "buy_costs": ["payment description", "principal description", "maintenance description", "insurance description", "property tax vs tax savings description", "PMI description"],
  "rent_costs": ["starting rent description", "ending rent with % change", "monthly surplus/investment description", "investment growth description"]
}}

Do NOT include a verdict or score — those are computed separately.
Focus your summary on explaining WHY the numbers are what they are, not on making a recommendation."""


async def generate_summary(
    result: SimulationResult,
    sell_cost_pct: float = 0.06,
    api_key: str | None = None,
) -> LLMSummaryResult:
    """Generate a narrative summary with deterministic score + LLM narrative.

    The score and verdict are computed deterministically (scoring.py) —
    same inputs will always produce the same score. Only the prose
    (summary, pros/cons, cost descriptions) comes from the LLM.

    Args:
        result: Simulation output to summarize.
        sell_cost_pct: User's sell cost (proxy for likelihood to move).
        api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
    """
    from scoring import compute_buy_score, compute_verdict

    # Deterministic score and verdict — always stable
    score = compute_buy_score(result)
    verdict = compute_verdict(score)

    # LLM for narrative only
    import anthropic

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("ANTHROPIC_API_KEY not set")

    client = anthropic.AsyncAnthropic(api_key=key)
    prompt = build_prompt(result, sell_cost_pct)

    message = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,  # minimize variation
    )

    raw = message.content[0].text.strip()

    # Strip markdown code fence if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    if raw.startswith("json"):
        raw = raw[4:]

    parsed = json.loads(raw.strip())

    return LLMSummaryResult(
        summary=parsed.get("summary", ""),
        buy_costs_summary=parsed.get("buy_costs_summary", ""),
        buy_pros=parsed.get("buy_pros", []),
        rent_pros=parsed.get("rent_pros", []),
        buy_costs=parsed.get("buy_costs", []),
        rent_costs=parsed.get("rent_costs", []),
        verdict=verdict,   # deterministic, not from LLM
        score=score,        # deterministic, not from LLM
    )
