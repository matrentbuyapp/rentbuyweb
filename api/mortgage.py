"""Mortgage amortization, PMI, and tax benefit calculations."""

from dataclasses import dataclass
import numpy as np


# ---------------------------------------------------------------------------
# Amortization
# ---------------------------------------------------------------------------

@dataclass
class AmortizationRow:
    month: int
    payment: float
    interest: float
    principal: float
    remaining_balance: float


def amortize(principal: float, annual_rate: float, term_months: int) -> list[AmortizationRow]:
    """Compute a full monthly amortization schedule.

    Args:
        principal: Loan amount.
        annual_rate: Annual interest rate as a decimal (e.g. 0.065 for 6.5%).
        term_months: Loan term in months.

    Returns:
        List of AmortizationRow, one per month.
    """
    if term_months <= 0:
        raise ValueError("term_months must be positive")
    if principal <= 0:
        return []

    monthly_rate = annual_rate / 12

    if monthly_rate == 0:
        payment = principal / term_months
    else:
        payment = principal * (monthly_rate * (1 + monthly_rate) ** term_months) / (
            (1 + monthly_rate) ** term_months - 1
        )

    balance = principal
    schedule: list[AmortizationRow] = []

    for m in range(term_months):
        interest = balance * monthly_rate
        princ = payment - interest
        balance -= princ
        schedule.append(AmortizationRow(
            month=m,
            payment=payment,
            interest=interest,
            principal=princ,
            remaining_balance=max(balance, 0.0),
        ))

    return schedule


# ---------------------------------------------------------------------------
# PMI
# ---------------------------------------------------------------------------

# Annual PMI rate by initial LTV bracket, plus credit quality adjustment.
_PMI_BASE_RATES = [
    (0.80, 0.0000),
    (0.85, 0.0030),
    (0.90, 0.0050),
    (0.95, 0.0075),
    (0.97, 0.0100),
    (1.00, 0.0125),
]

_CREDIT_PMI_ADJ = {
    "excellent": 0.0000,
    "great": 0.00125,
    "good": 0.00375,
    "average": 0.0075,
    "mediocre": 0.0125,
    "poor": 0.0200,
}


def pmi_schedule(
    home_price: float,
    down_payment_pct: float,
    credit_quality: str,
    amort: list[AmortizationRow],
    cancel_ltv: float = 0.80,
) -> np.ndarray:
    """Monthly PMI amounts. Returns ndarray of length len(amort).

    PMI is charged until loan-to-value drops below cancel_ltv.
    """
    loan = home_price * (1 - down_payment_pct)
    initial_ltv = loan / home_price

    base_rate = next(
        (rate for max_ltv, rate in _PMI_BASE_RATES if initial_ltv <= max_ltv),
        0.0150,
    )
    credit_adj = _CREDIT_PMI_ADJ.get(credit_quality, 0.0125)
    monthly_pmi = loan * (base_rate + credit_adj) / 12

    result = np.zeros(len(amort))
    for i, row in enumerate(amort):
        if row.remaining_balance / home_price > cancel_ltv:
            result[i] = monthly_pmi
        else:
            break  # once cancelled, stays cancelled

    return result


# ---------------------------------------------------------------------------
# Mortgage rate estimation
# ---------------------------------------------------------------------------

_CREDIT_RATE_ADJ = {
    "excellent": 0.00,
    "great": 0.125,
    "good": 0.375,
    "average": 0.75,
    "mediocre": 1.25,
    "poor": 2.00,
}


def credit_rate_adjustment(credit_quality: str, down_payment_pct: float) -> float:
    """Extra rate (in percentage points) added to base mortgage rate
    for credit risk and down payment size."""
    credit_adj = _CREDIT_RATE_ADJ.get(credit_quality, 1.25)

    if down_payment_pct >= 0.30:
        dp_adj = -0.125
    elif down_payment_pct >= 0.20:
        dp_adj = 0.0
    elif down_payment_pct >= 0.10:
        dp_adj = 0.125
    elif down_payment_pct >= 0.05:
        dp_adj = 0.25
    else:
        dp_adj = 0.375

    return credit_adj + dp_adj


# ---------------------------------------------------------------------------
# Tax savings
# ---------------------------------------------------------------------------

_STANDARD_DEDUCTION = {
    "single": 15750,
    "married_joint": 31500,
    "head_of_household": 23625,
}

_TAX_BRACKETS = {
    "single": [
        (0, 0.10), (11600, 0.12), (47150, 0.22),
        (100525, 0.24), (191950, 0.32), (243725, 0.35), (609350, 0.37),
    ],
    "married_joint": [
        (0, 0.10), (23200, 0.12), (94300, 0.22),
        (201050, 0.24), (383900, 0.32), (487450, 0.35), (731200, 0.37),
    ],
    "head_of_household": [
        (0, 0.10), (16550, 0.12), (63100, 0.22),
        (100500, 0.24), (191950, 0.32), (243700, 0.35), (609350, 0.37),
    ],
}

SALT_CAP = 40_000.0


def _marginal_rate(filing_status: str, gross_income: float) -> float:
    brackets = _TAX_BRACKETS.get(filing_status, _TAX_BRACKETS["single"])
    for threshold, rate in reversed(brackets):
        if gross_income >= threshold:
            return rate
    return 0.10


def monthly_tax_savings(
    amort: list[AmortizationRow],
    monthly_property_tax: np.ndarray,
    filing_status: str,
    gross_income: float,
    state_income_tax_rate: float = 0.0,
    other_deductions: float = 0.0,
) -> np.ndarray:
    """Estimate monthly federal tax savings from itemizing mortgage interest,
    property tax, and state income tax vs taking the standard deduction.

    Processes in 12-month blocks to mirror annual tax filing.
    """
    filing_status = filing_status.lower()
    std_deduction = _STANDARD_DEDUCTION.get(filing_status, 15750)
    rate = _marginal_rate(filing_status, gross_income)
    annual_state_tax = gross_income * state_income_tax_rate

    n = min(len(amort), len(monthly_property_tax))
    result = np.zeros(n)

    for block_start in range(0, n, 12):
        block_end = min(block_start + 12, n)
        block_len = block_end - block_start

        yearly_interest = sum(amort[i].interest for i in range(block_start, block_end))
        yearly_prop_tax = float(monthly_property_tax[block_start:block_end].sum())

        salt = min(SALT_CAP, annual_state_tax + yearly_prop_tax)
        total_itemized = yearly_interest + salt + other_deductions
        excess = max(0.0, total_itemized - std_deduction)
        monthly_saving = (excess * rate) / block_len

        result[block_start:block_end] = monthly_saving

    return result
