"""Tests for mortgage.py — amortization, PMI, credit adjustment, tax savings.

All tests use fixed inputs and assert exact (or tightly bounded) numeric outcomes.
If these break after an optimization, something changed in the financial math.
"""

import numpy as np
import pytest
from mortgage import (
    amortize,
    AmortizationRow,
    pmi_schedule,
    credit_rate_adjustment,
    monthly_tax_savings,
    _marginal_rate,
    SALT_CAP,
)


# ═══════════════════════════════════════════════════════════════════════════
# Amortization
# ═══════════════════════════════════════════════════════════════════════════

class TestAmortize:
    def test_30yr_300k_at_6_5_pct(self):
        """Canonical case: 30Y $300k at 6.5%. Verified against bankrate.com."""
        s = amortize(300_000, 0.065, 360)
        assert len(s) == 360
        # Payment should be $1896.20 ± $0.01
        assert abs(s[0].payment - 1896.20) < 0.01
        # First month interest = 300000 * 0.065/12 = 1625.00
        assert abs(s[0].interest - 1625.00) < 0.01
        # First month principal = 1896.20 - 1625.00 = 271.20
        assert abs(s[0].principal - 271.20) < 0.01
        # Balance after first month
        assert abs(s[0].remaining_balance - 299_728.80) < 0.01

    def test_balance_reaches_zero(self):
        s = amortize(300_000, 0.065, 360)
        assert s[-1].remaining_balance < 0.01

    def test_total_interest_over_life(self):
        """Total interest on $300k/6.5%/30Y should be ~$382,633."""
        s = amortize(300_000, 0.065, 360)
        total_interest = sum(r.interest for r in s)
        assert abs(total_interest - 382_633) < 50

    def test_total_paid_equals_principal_plus_interest(self):
        s = amortize(300_000, 0.065, 360)
        total_paid = sum(r.payment for r in s)
        total_interest = sum(r.interest for r in s)
        total_principal = sum(r.principal for r in s)
        assert abs(total_paid - (total_interest + total_principal)) < 0.01
        assert abs(total_principal - 300_000) < 1.0

    def test_15yr_200k_at_5_pct(self):
        """15Y $200k at 5%. Payment should be ~$1581.59."""
        s = amortize(200_000, 0.05, 180)
        assert len(s) == 180
        assert abs(s[0].payment - 1581.59) < 0.01
        assert s[-1].remaining_balance < 0.01

    def test_zero_rate(self):
        """0% rate: payment = principal / months."""
        s = amortize(120_000, 0.0, 120)
        assert len(s) == 120
        assert abs(s[0].payment - 1000.00) < 0.01
        assert abs(s[0].interest - 0.0) < 0.001
        assert s[-1].remaining_balance < 0.01

    def test_zero_principal(self):
        s = amortize(0, 0.065, 360)
        assert len(s) == 0

    def test_short_term(self):
        """1-month loan."""
        s = amortize(10_000, 0.06, 1)
        assert len(s) == 1
        assert abs(s[0].payment - 10_050.00) < 0.01  # principal + 1 month interest
        assert s[0].remaining_balance < 0.01

    def test_interest_decreases_over_time(self):
        s = amortize(300_000, 0.065, 360)
        assert s[0].interest > s[179].interest > s[359].interest

    def test_principal_increases_over_time(self):
        s = amortize(300_000, 0.065, 360)
        assert s[0].principal < s[179].principal < s[359].principal

    def test_payment_constant(self):
        """Fixed-rate mortgage: payment should be identical every month."""
        s = amortize(300_000, 0.065, 360)
        payments = [r.payment for r in s]
        assert max(payments) - min(payments) < 0.001

    def test_invalid_term(self):
        with pytest.raises(ValueError, match="positive"):
            amortize(100_000, 0.05, 0)


# ═══════════════════════════════════════════════════════════════════════════
# PMI
# ═══════════════════════════════════════════════════════════════════════════

class TestPMI:
    def test_20pct_down_no_pmi(self):
        """20% down → LTV = 80% → no PMI."""
        s = amortize(240_000, 0.065, 360)
        pmi = pmi_schedule(300_000, 0.20, "good", s)
        assert pmi.sum() == 0.0

    def test_10pct_down_has_pmi(self):
        """10% down → LTV = 90% → PMI until ~80%."""
        s = amortize(270_000, 0.065, 360)
        pmi = pmi_schedule(300_000, 0.10, "good", s)
        assert pmi[0] > 0
        assert pmi[-1] == 0

    def test_pmi_cancellation_month(self):
        """10% down on $300k at 6.5%: PMI should cancel around month 94."""
        s = amortize(270_000, 0.065, 360)
        pmi = pmi_schedule(300_000, 0.10, "good", s)
        cancel_month = next(i for i, v in enumerate(pmi) if v == 0)
        assert 85 <= cancel_month <= 105

    def test_pmi_amount_10pct_down_good_credit(self):
        """10% down, good credit: annual rate = 0.50% base + 0.375% credit = 0.875%.
        Monthly PMI = $270k * 0.00875 / 12 ≈ $196.88."""
        s = amortize(270_000, 0.065, 360)
        pmi = pmi_schedule(300_000, 0.10, "good", s)
        assert abs(pmi[0] - 196.88) < 1.0

    def test_5pct_down_higher_pmi(self):
        """5% down should have higher PMI than 10% down."""
        s10 = amortize(270_000, 0.065, 360)
        s5 = amortize(285_000, 0.065, 360)
        pmi10 = pmi_schedule(300_000, 0.10, "good", s10)
        pmi5 = pmi_schedule(300_000, 0.05, "good", s5)
        assert pmi5[0] > pmi10[0]

    def test_poor_credit_higher_pmi(self):
        """Poor credit should cost more PMI than excellent."""
        s = amortize(270_000, 0.065, 360)
        pmi_excellent = pmi_schedule(300_000, 0.10, "excellent", s)
        pmi_poor = pmi_schedule(300_000, 0.10, "poor", s)
        assert pmi_poor[0] > pmi_excellent[0]

    def test_pmi_stays_cancelled(self):
        """Once PMI cancels, it should never come back."""
        s = amortize(270_000, 0.065, 360)
        pmi = pmi_schedule(300_000, 0.10, "good", s)
        first_zero = next(i for i, v in enumerate(pmi) if v == 0)
        assert all(pmi[first_zero:] == 0)


# ═══════════════════════════════════════════════════════════════════════════
# Credit rate adjustment
# ═══════════════════════════════════════════════════════════════════════════

class TestCreditRateAdjustment:
    def test_excellent_20pct(self):
        """Excellent credit, 20% down: 0.0 + 0.0 = 0.0."""
        assert credit_rate_adjustment("excellent", 0.20) == 0.0

    def test_good_20pct(self):
        """Good credit, 20% down: 0.375 + 0.0 = 0.375."""
        assert credit_rate_adjustment("good", 0.20) == 0.375

    def test_poor_3pct(self):
        """Poor credit, 3% down: 2.0 + 0.375 = 2.375."""
        assert credit_rate_adjustment("poor", 0.03) == 2.375

    def test_average_10pct(self):
        """Average credit, 10% down: 0.75 + 0.125 = 0.875."""
        assert credit_rate_adjustment("average", 0.10) == 0.875

    def test_excellent_30pct(self):
        """Excellent, 30%+ down: 0.0 + (-0.125) = -0.125."""
        assert credit_rate_adjustment("excellent", 0.35) == -0.125

    def test_ordering(self):
        """Worse credit + lower down payment → higher adjustment."""
        adj_best = credit_rate_adjustment("excellent", 0.30)
        adj_mid = credit_rate_adjustment("good", 0.15)
        adj_worst = credit_rate_adjustment("poor", 0.03)
        assert adj_best < adj_mid < adj_worst

    def test_5pct_threshold_fixed(self):
        """The old code had dp >= 0.5 (50%) instead of 0.05 (5%).
        Verify 5% down gets dp_adj=0.25, not 0.375."""
        adj_5 = credit_rate_adjustment("excellent", 0.05)
        adj_4 = credit_rate_adjustment("excellent", 0.04)
        assert adj_5 == 0.25   # 0.0 credit + 0.25 dp
        assert adj_4 == 0.375  # 0.0 credit + 0.375 dp


# ═══════════════════════════════════════════════════════════════════════════
# Marginal tax rate
# ═══════════════════════════════════════════════════════════════════════════

class TestMarginalRate:
    def test_single_25k(self):
        assert _marginal_rate("single", 25_000) == 0.12

    def test_single_60k(self):
        assert _marginal_rate("single", 60_000) == 0.22

    def test_single_150k(self):
        assert _marginal_rate("single", 150_000) == 0.24

    def test_single_250k(self):
        assert _marginal_rate("single", 250_000) == 0.35

    def test_married_100k(self):
        assert _marginal_rate("married_joint", 100_000) == 0.22

    def test_married_500k(self):
        assert _marginal_rate("married_joint", 500_000) == 0.35

    def test_hoh_70k(self):
        assert _marginal_rate("head_of_household", 70_000) == 0.22

    def test_zero_income(self):
        assert _marginal_rate("single", 0) == 0.10


# ═══════════════════════════════════════════════════════════════════════════
# Tax savings
# ═══════════════════════════════════════════════════════════════════════════

class TestTaxSavings:
    def test_high_income_has_savings(self):
        """$400k loan at 6.5%, income $150k single, CA (6% state tax).
        First-year interest ≈ $25,864. Property tax ≈ $6,000.
        State tax = $9,000. SALT = min(40k, 9000+6000) = $15,000.
        Itemized = 25864 + 15000 = $40,864.
        Standard deduction = $15,750. Excess = $25,114.
        Marginal rate = 24%. Annual saving = $6,027. Monthly ≈ $502."""
        s = amortize(400_000, 0.065, 360)
        ptax = np.full(360, 500.0)  # $500/mo = $6k/yr
        savings = monthly_tax_savings(s, ptax, "single", 150_000, 0.06, 0.0)
        assert len(savings) == 360
        assert abs(savings[0] - 502) < 10

    def test_low_income_no_savings(self):
        """$100k loan, 4%, married $40k income, no state tax.
        First-year interest ≈ $3,968. Property tax ≈ $1,200.
        Itemized ≈ $5,168 < standard deduction $31,500. No savings."""
        s = amortize(100_000, 0.04, 360)
        ptax = np.full(360, 100.0)
        savings = monthly_tax_savings(s, ptax, "married_joint", 40_000, 0.0, 0.0)
        assert savings[0] == 0.0

    def test_savings_decrease_over_time(self):
        """Interest decreases → savings should decrease."""
        s = amortize(400_000, 0.065, 360)
        ptax = np.full(360, 500.0)
        savings = monthly_tax_savings(s, ptax, "single", 150_000, 0.06, 0.0)
        # Compare first year vs last year
        first_year = savings[0]
        last_year = savings[-1]
        assert first_year > last_year

    def test_salt_cap_applied(self):
        """With very high state tax, SALT should cap at $40k.
        Income $500k, CA 6% → state tax $30k. Prop tax $20k/yr.
        Uncapped SALT would be $50k, but caps at $40k."""
        s = amortize(500_000, 0.065, 360)
        ptax = np.full(360, 1666.67)  # ~$20k/yr
        savings_ca = monthly_tax_savings(s, ptax, "single", 500_000, 0.06, 0.0)

        # Now same but with huge state tax (shouldn't change result much due to cap)
        savings_hightax = monthly_tax_savings(s, ptax, "single", 500_000, 0.15, 0.0)

        # Both hit the SALT cap, so savings should be similar
        # (the difference is only that marginal rate might differ slightly)
        assert abs(savings_ca[0] - savings_hightax[0]) < 5

    def test_no_state_tax_state(self):
        """TX/FL: 0% state income tax → lower SALT → lower savings."""
        s = amortize(400_000, 0.065, 360)
        ptax = np.full(360, 500.0)
        savings_ca = monthly_tax_savings(s, ptax, "single", 150_000, 0.06, 0.0)
        savings_tx = monthly_tax_savings(s, ptax, "single", 150_000, 0.0, 0.0)
        assert savings_ca[0] > savings_tx[0]

    def test_other_deductions_increase_savings(self):
        """Adding $5k other deductions should increase savings."""
        s = amortize(400_000, 0.065, 360)
        ptax = np.full(360, 500.0)
        savings_base = monthly_tax_savings(s, ptax, "single", 150_000, 0.06, 0.0)
        savings_more = monthly_tax_savings(s, ptax, "single", 150_000, 0.06, 5_000)
        assert savings_more[0] > savings_base[0]

    def test_length_matches_shorter_input(self):
        """Output length = min(amort, property_tax)."""
        s = amortize(100_000, 0.05, 360)
        ptax = np.full(120, 100.0)  # only 10 years of prop tax
        savings = monthly_tax_savings(s, ptax, "single", 100_000, 0.0, 0.0)
        assert len(savings) == 120
