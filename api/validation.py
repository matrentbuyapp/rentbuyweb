"""Input validation and sanity checks for rent-vs-buy simulation.

Two categories:
  - Errors: impossible combinations, simulation will produce garbage. Block the request.
  - Warnings: technically runnable but results may be misleading. Return alongside results.

Static rules (no API call needed — frontend can enforce these directly):
  - monthly_rent > 0
  - monthly_budget >= monthly_rent
  - initial_cash >= 0
  - down_payment_pct in [0.03, 1.0]
  - house_price > 0 (when provided)
"""

from dataclasses import dataclass

from mortgage import amortize, credit_rate_adjustment


@dataclass
class ValidationIssue:
    code: str       # machine-readable key for frontend i18n / conditional logic
    severity: str   # "error" or "warning"
    message: str    # human-readable explanation


def validate_inputs(
    monthly_rent: float,
    monthly_budget: float,
    initial_cash: float,
    yearly_income: float,
    house_price: float,
    down_payment_pct: float,
    closing_cost_pct: float,
    move_in_cost: float,
    mortgage_rate: float,
    term_years: int,
    maintenance_rate: float,
    insurance_annual: float,
    property_tax_rate: float,
) -> list[ValidationIssue]:
    """Run all checks against resolved inputs (after house price and rate are known)."""
    issues: list[ValidationIssue] = []

    # --- Hard errors ---

    # Can't even rent
    if monthly_budget < monthly_rent:
        issues.append(ValidationIssue(
            code="budget_below_rent",
            severity="error",
            message=f"Housing budget (${monthly_budget:,.0f}) is less than rent (${monthly_rent:,.0f}). "
                    "You can't afford either option at these numbers.",
        ))

    # Can't close
    closing_cash = house_price * (down_payment_pct + closing_cost_pct) + move_in_cost
    if initial_cash < closing_cash:
        issues.append(ValidationIssue(
            code="insufficient_cash_to_close",
            severity="error",
            message=f"You need ${closing_cash:,.0f} to close "
                    f"(${house_price * down_payment_pct:,.0f} down + "
                    f"${house_price * closing_cost_pct:,.0f} closing + "
                    f"${move_in_cost:,.0f} move-in) "
                    f"but only have ${initial_cash:,.0f} in savings.",
        ))

    # Compute monthly mortgage
    loan = house_price * (1 - down_payment_pct)
    r = mortgage_rate / 12
    n = term_years * 12
    if r > 0 and loan > 0:
        monthly_mortgage = loan * (r * (1 + r) ** n) / ((1 + r) ** n - 1)
    elif loan > 0:
        monthly_mortgage = loan / n
    else:
        monthly_mortgage = 0

    # Estimate total monthly ownership cost
    monthly_prop_tax = property_tax_rate * house_price / 12
    monthly_maint = maintenance_rate * house_price / 12
    monthly_ins = insurance_annual / 12
    total_monthly = monthly_mortgage + monthly_prop_tax + monthly_maint + monthly_ins

    # Mortgage alone exceeds budget
    if monthly_mortgage > monthly_budget:
        issues.append(ValidationIssue(
            code="mortgage_exceeds_budget",
            severity="error",
            message=f"Mortgage payment alone (${monthly_mortgage:,.0f}/mo) exceeds your "
                    f"housing budget (${monthly_budget:,.0f}/mo). This purchase isn't feasible.",
        ))

    # Down payment too low for any lender
    if down_payment_pct < 0.03:
        issues.append(ValidationIssue(
            code="down_payment_too_low",
            severity="error",
            message=f"Down payment of {down_payment_pct:.0%} is below the 3% minimum "
                    "required by conventional lenders.",
        ))

    # --- Warnings ---

    # Total housing cost exceeds budget (mortgage is OK, but taxes/insurance/maint push it over)
    if total_monthly > monthly_budget and monthly_mortgage <= monthly_budget:
        overage = total_monthly - monthly_budget
        issues.append(ValidationIssue(
            code="total_cost_exceeds_budget",
            severity="warning",
            message=f"Total ownership cost (${total_monthly:,.0f}/mo) exceeds your budget "
                    f"by ${overage:,.0f}/mo. The mortgage fits, but taxes, insurance, and "
                    "maintenance push it over.",
        ))

    # DTI check (conventional mortgage qualification)
    if yearly_income > 0:
        monthly_income = yearly_income / 12
        dti = total_monthly / monthly_income
        if dti > 0.43:
            issues.append(ValidationIssue(
                code="dti_too_high",
                severity="warning",
                message=f"Housing costs would be {dti:.0%} of gross income. "
                        "Most lenders cap DTI at 43% for conventional mortgages. "
                        "You may not qualify for this loan.",
            ))

    # House price to income ratio
    if yearly_income > 0 and house_price > 5 * yearly_income:
        ratio = house_price / yearly_income
        issues.append(ValidationIssue(
            code="price_to_income_high",
            severity="warning",
            message=f"House price is {ratio:.1f}× your annual income. "
                    "Lenders typically prefer under 4-5×. Approval may be difficult.",
        ))

    # Thin reserves after closing
    if initial_cash >= closing_cash and total_monthly > 0:
        remaining = initial_cash - closing_cash
        months_reserve = remaining / total_monthly
        if months_reserve < 2:
            issues.append(ValidationIssue(
                code="thin_reserves",
                severity="warning",
                message=f"After closing you'd have ${remaining:,.0f} left — "
                        f"only {months_reserve:.1f} months of housing costs. "
                        "Most advisors recommend 3-6 months in reserve.",
            ))

    return issues
