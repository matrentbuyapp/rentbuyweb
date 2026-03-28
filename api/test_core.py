"""Smoke tests for the core financial math and simulator."""

import numpy as np
from mortgage import amortize, pmi_schedule, credit_rate_adjustment, monthly_tax_savings


def test_amortize_basic():
    """30-year $300k loan at 6.5% — verify payment and balance."""
    schedule = amortize(300_000, 0.065, 360)
    assert len(schedule) == 360

    # Monthly payment should be ~$1896
    assert 1890 < schedule[0].payment < 1900

    # First month: mostly interest
    assert schedule[0].interest > schedule[0].principal

    # Last month: balance should be ~0
    assert schedule[-1].remaining_balance < 1.0

    # Total paid should exceed principal
    total_paid = sum(r.payment for r in schedule)
    assert total_paid > 300_000

    print(f"  Payment: ${schedule[0].payment:.2f}/mo")
    print(f"  Total paid: ${total_paid:,.0f}")
    print(f"  Total interest: ${total_paid - 300_000:,.0f}")


def test_amortize_zero_rate():
    schedule = amortize(120_000, 0.0, 120)
    assert len(schedule) == 120
    assert abs(schedule[0].payment - 1000) < 0.01
    assert schedule[-1].remaining_balance < 0.01


def test_pmi_cancels():
    """PMI should cancel when LTV drops below 80%."""
    schedule = amortize(270_000, 0.065, 360)  # 10% down on $300k
    pmi = pmi_schedule(300_000, 0.10, "good", schedule)

    assert pmi[0] > 0, "PMI should be charged initially"
    assert pmi[-1] == 0, "PMI should cancel before end of loan"

    # Find cancellation month
    cancel_month = next(i for i, v in enumerate(pmi) if v == 0)
    print(f"  PMI cancels at month {cancel_month}")
    assert cancel_month > 12, "PMI should last more than 1 year"


def test_pmi_not_needed():
    """20% down = no PMI."""
    schedule = amortize(240_000, 0.065, 360)  # 20% down on $300k
    pmi = pmi_schedule(300_000, 0.20, "good", schedule)
    assert pmi.sum() == 0


def test_credit_adjustment():
    """Sanity check credit/dp adjustments."""
    adj_good_20 = credit_rate_adjustment("good", 0.20)
    adj_poor_5 = credit_rate_adjustment("poor", 0.05)

    assert adj_poor_5 > adj_good_20
    assert adj_good_20 > 0
    print(f"  good/20%: +{adj_good_20:.3f}pp, poor/5%: +{adj_poor_5:.3f}pp")


def test_tax_savings():
    """High income + mortgage interest should produce savings."""
    schedule = amortize(400_000, 0.065, 360)
    prop_tax = np.full(360, 500.0)  # $500/mo property tax

    savings = monthly_tax_savings(
        schedule, prop_tax,
        filing_status="single",
        gross_income=150_000,
        state_income_tax_rate=0.06,
        other_deductions=0,
    )

    assert len(savings) == 360
    assert savings[0] > 0, "Should have tax savings with this income"
    # Savings should decrease over time as interest decreases
    assert savings[0] >= savings[-1]
    print(f"  First year monthly savings: ${savings[0]:.0f}")
    print(f"  Last year monthly savings: ${savings[-1]:.0f}")


def test_tax_savings_low_income():
    """Low income — standard deduction beats itemizing, so no savings."""
    schedule = amortize(100_000, 0.04, 360)
    prop_tax = np.full(360, 100.0)

    savings = monthly_tax_savings(
        schedule, prop_tax,
        filing_status="married_joint",
        gross_income=40_000,
        state_income_tax_rate=0.0,  # no state tax
        other_deductions=0,
    )

    assert savings[0] == 0, "Standard deduction should win for low income"
    print("  Correctly returns $0 savings (standard deduction wins)")


if __name__ == "__main__":
    tests = [
        test_amortize_basic,
        test_amortize_zero_rate,
        test_pmi_cancels,
        test_pmi_not_needed,
        test_credit_adjustment,
        test_tax_savings,
        test_tax_savings_low_income,
    ]
    for t in tests:
        print(f"\n{t.__name__}:")
        t()
        print("  PASSED")

    print(f"\n{'='*40}")
    print(f"All {len(tests)} tests passed.")
