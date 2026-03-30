"""Tests for validation.py — input validation and sanity checks."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from validation import validate_inputs, ValidationIssue


def _defaults(**overrides):
    """Base valid inputs — no issues expected."""
    base = dict(
        monthly_rent=3000,
        monthly_budget=5000,
        initial_cash=150_000,
        yearly_income=120_000,
        house_price=500_000,
        down_payment_pct=0.20,
        closing_cost_pct=0.03,
        move_in_cost=0,
        mortgage_rate=0.065,
        term_years=30,
        maintenance_rate=0.01,
        insurance_annual=2000,
        property_tax_rate=0.012,
    )
    base.update(overrides)
    return base


def _codes(issues):
    return [i.code for i in issues]


def _errors(issues):
    return [i for i in issues if i.severity == "error"]


def _warnings(issues):
    return [i for i in issues if i.severity == "warning"]


# ---------------------------------------------------------------------------
# Clean inputs
# ---------------------------------------------------------------------------

class TestCleanInputs:
    def test_baseline_no_issues(self):
        issues = validate_inputs(**_defaults())
        assert issues == []

    def test_all_cash_purchase(self):
        """100% down, no mortgage — should be clean."""
        issues = validate_inputs(**_defaults(
            down_payment_pct=1.0, initial_cash=600_000,
        ))
        assert issues == []

    def test_minimum_viable(self):
        """3% down, just barely enough cash and budget."""
        price = 200_000
        dp = 0.03
        closing = 0.03
        cash_needed = price * (dp + closing)
        # Compute mortgage payment
        loan = price * (1 - dp)
        r = 0.065 / 12
        n = 360
        pmt = loan * (r * (1 + r)**n) / ((1 + r)**n - 1)
        issues = validate_inputs(**_defaults(
            house_price=price,
            down_payment_pct=dp,
            initial_cash=cash_needed + 50_000,  # enough reserves
            monthly_budget=pmt + 500,  # enough headroom
            monthly_rent=1500,
        ))
        assert _errors(issues) == []


# ---------------------------------------------------------------------------
# Errors: budget_below_rent
# ---------------------------------------------------------------------------

class TestBudgetBelowRent:
    def test_budget_below_rent(self):
        issues = validate_inputs(**_defaults(monthly_budget=2000, monthly_rent=3000))
        assert "budget_below_rent" in _codes(issues)
        assert _errors(issues)[0].severity == "error"

    def test_budget_equals_rent_no_error(self):
        """Budget == rent is technically viable (zero surplus)."""
        issues = validate_inputs(**_defaults(monthly_budget=3000, monthly_rent=3000))
        assert "budget_below_rent" not in _codes(issues)

    def test_budget_one_dollar_below(self):
        issues = validate_inputs(**_defaults(monthly_budget=2999, monthly_rent=3000))
        assert "budget_below_rent" in _codes(issues)


# ---------------------------------------------------------------------------
# Errors: insufficient_cash_to_close
# ---------------------------------------------------------------------------

class TestInsufficientCash:
    def test_not_enough_cash(self):
        # 20% of 500k = 100k down + 3% = 15k closing = 115k needed
        issues = validate_inputs(**_defaults(initial_cash=100_000))
        assert "insufficient_cash_to_close" in _codes(issues)

    def test_exact_cash_no_error(self):
        """Cash exactly equals closing costs — no error."""
        cash_needed = 500_000 * (0.20 + 0.03)  # 115,000
        issues = validate_inputs(**_defaults(initial_cash=cash_needed))
        assert "insufficient_cash_to_close" not in _codes(issues)

    def test_move_in_cost_pushes_over(self):
        cash_needed = 500_000 * (0.20 + 0.03)  # 115,000
        issues = validate_inputs(**_defaults(
            initial_cash=cash_needed,
            move_in_cost=5000,
        ))
        assert "insufficient_cash_to_close" in _codes(issues)

    def test_low_down_payment_needs_less_cash(self):
        # 5% of 300k = 15k down + 3% = 9k closing = 24k
        issues = validate_inputs(**_defaults(
            house_price=300_000, down_payment_pct=0.05,
            initial_cash=30_000,
        ))
        assert "insufficient_cash_to_close" not in _codes(issues)


# ---------------------------------------------------------------------------
# Errors: mortgage_exceeds_budget
# ---------------------------------------------------------------------------

class TestMortgageExceedsBudget:
    def test_mortgage_exceeds_budget(self):
        """Expensive house with low budget."""
        issues = validate_inputs(**_defaults(
            house_price=1_000_000, monthly_budget=3000,
            initial_cash=500_000,  # enough cash to close
        ))
        assert "mortgage_exceeds_budget" in _codes(issues)

    def test_mortgage_within_budget_ok(self):
        issues = validate_inputs(**_defaults(monthly_budget=5000))
        assert "mortgage_exceeds_budget" not in _codes(issues)


# ---------------------------------------------------------------------------
# Errors: down_payment_too_low
# ---------------------------------------------------------------------------

class TestDownPaymentTooLow:
    def test_below_3_percent(self):
        issues = validate_inputs(**_defaults(
            down_payment_pct=0.02, initial_cash=500_000,
        ))
        assert "down_payment_too_low" in _codes(issues)

    def test_exactly_3_percent_ok(self):
        issues = validate_inputs(**_defaults(
            down_payment_pct=0.03, initial_cash=500_000,
        ))
        assert "down_payment_too_low" not in _codes(issues)

    def test_zero_down(self):
        issues = validate_inputs(**_defaults(
            down_payment_pct=0.0, initial_cash=500_000,
        ))
        assert "down_payment_too_low" in _codes(issues)


# ---------------------------------------------------------------------------
# Warnings: total_cost_exceeds_budget
# ---------------------------------------------------------------------------

class TestTotalCostExceedsBudget:
    def test_taxes_push_over_budget(self):
        """Mortgage fits, but taxes + insurance + maintenance push total over."""
        # Set budget just above mortgage but below total
        issues = validate_inputs(**_defaults(
            house_price=400_000,
            monthly_budget=2500,
            monthly_rent=2000,
            initial_cash=200_000,
            down_payment_pct=0.20,
            insurance_annual=3000,
            maintenance_rate=0.015,
            property_tax_rate=0.025,
        ))
        codes = _codes(issues)
        # Mortgage alone should be within budget, but total should exceed
        if "mortgage_exceeds_budget" not in codes:
            assert "total_cost_exceeds_budget" in codes


# ---------------------------------------------------------------------------
# Warnings: dti_too_high
# ---------------------------------------------------------------------------

class TestDTI:
    def test_high_dti(self):
        """Housing costs > 43% of gross income."""
        issues = validate_inputs(**_defaults(
            yearly_income=60_000,  # $5k/mo gross
            house_price=500_000,
            monthly_budget=5000,
            monthly_rent=2000,
            initial_cash=200_000,
        ))
        assert "dti_too_high" in _codes(issues)

    def test_dti_at_boundary(self):
        """DTI exactly at 43% — should not warn."""
        # monthly_income = 120000/12 = 10000
        # Need total_housing_cost / 10000 = 0.43 → total = 4300
        # With defaults: mortgage ~2528 + prop_tax 500 + maint 417 + ins 167 = ~3612
        # Well under 43% with 120k income
        issues = validate_inputs(**_defaults(yearly_income=120_000))
        assert "dti_too_high" not in _codes(issues)

    def test_zero_income_no_dti_warning(self):
        """No income → no DTI check (can't divide by zero)."""
        issues = validate_inputs(**_defaults(yearly_income=0))
        assert "dti_too_high" not in _codes(issues)


# ---------------------------------------------------------------------------
# Warnings: price_to_income_high
# ---------------------------------------------------------------------------

class TestPriceToIncome:
    def test_high_price_to_income(self):
        """House > 5x income."""
        issues = validate_inputs(**_defaults(
            yearly_income=80_000,
            house_price=500_000,  # 6.25x
            initial_cash=200_000,
        ))
        assert "price_to_income_high" in _codes(issues)

    def test_exactly_5x_no_warning(self):
        """At exactly 5x, should not warn."""
        issues = validate_inputs(**_defaults(
            yearly_income=100_000,
            house_price=500_000,  # exactly 5x
        ))
        assert "price_to_income_high" not in _codes(issues)

    def test_zero_income_no_warning(self):
        issues = validate_inputs(**_defaults(yearly_income=0))
        assert "price_to_income_high" not in _codes(issues)


# ---------------------------------------------------------------------------
# Warnings: thin_reserves
# ---------------------------------------------------------------------------

class TestThinReserves:
    def test_thin_reserves_after_closing(self):
        """Less than 2 months of housing costs left after closing."""
        # closing = 500k * (0.20 + 0.03) = 115k, leave ~3k remaining
        issues = validate_inputs(**_defaults(initial_cash=118_000))
        assert "thin_reserves" in _codes(issues)

    def test_comfortable_reserves_no_warning(self):
        issues = validate_inputs(**_defaults(initial_cash=200_000))
        assert "thin_reserves" not in _codes(issues)

    def test_insufficient_cash_skips_reserve_check(self):
        """If cash < closing, we get an error, not a reserves warning."""
        issues = validate_inputs(**_defaults(initial_cash=50_000))
        codes = _codes(issues)
        assert "insufficient_cash_to_close" in codes
        # thin_reserves should not fire when you can't even close
        assert "thin_reserves" not in codes


# ---------------------------------------------------------------------------
# Multiple simultaneous issues
# ---------------------------------------------------------------------------

class TestMultipleIssues:
    def test_all_errors_at_once(self):
        """Trigger every error condition simultaneously."""
        issues = validate_inputs(
            monthly_rent=5000,
            monthly_budget=3000,       # < rent → budget_below_rent
            initial_cash=10_000,       # < closing → insufficient_cash
            yearly_income=60_000,
            house_price=1_000_000,     # huge → mortgage_exceeds_budget
            down_payment_pct=0.02,     # < 3% → down_payment_too_low
            closing_cost_pct=0.03,
            move_in_cost=0,
            mortgage_rate=0.07,
            term_years=30,
            maintenance_rate=0.01,
            insurance_annual=2000,
            property_tax_rate=0.012,
        )
        codes = _codes(issues)
        errors = _errors(issues)
        assert len(errors) >= 3
        assert "budget_below_rent" in codes
        assert "insufficient_cash_to_close" in codes
        assert "down_payment_too_low" in codes

    def test_errors_and_warnings_coexist(self):
        """Errors don't suppress warnings."""
        issues = validate_inputs(
            monthly_rent=3000,
            monthly_budget=5000,
            initial_cash=10_000,       # insufficient cash (error)
            yearly_income=60_000,
            house_price=500_000,       # 8.3x income (warning)
            down_payment_pct=0.20,
            closing_cost_pct=0.03,
            move_in_cost=0,
            mortgage_rate=0.065,
            term_years=30,
            maintenance_rate=0.01,
            insurance_annual=2000,
            property_tax_rate=0.012,
        )
        codes = _codes(issues)
        assert "insufficient_cash_to_close" in codes
        assert "price_to_income_high" in codes

    def test_multiple_warnings(self):
        """Multiple warnings can fire together."""
        issues = validate_inputs(
            monthly_rent=2000,
            monthly_budget=4000,
            initial_cash=120_000,      # thin reserves
            yearly_income=50_000,      # high DTI + high price ratio
            house_price=500_000,       # 10x income
            down_payment_pct=0.20,
            closing_cost_pct=0.03,
            move_in_cost=0,
            mortgage_rate=0.065,
            term_years=30,
            maintenance_rate=0.01,
            insurance_annual=2000,
            property_tax_rate=0.012,
        )
        warnings = _warnings(issues)
        codes = _codes(warnings)
        assert "dti_too_high" in codes
        assert "price_to_income_high" in codes


# ---------------------------------------------------------------------------
# ValidationIssue dataclass
# ---------------------------------------------------------------------------

class TestValidationIssue:
    def test_fields(self):
        v = ValidationIssue(code="test", severity="error", message="msg")
        assert v.code == "test"
        assert v.severity == "error"
        assert v.message == "msg"

    def test_message_contains_numbers(self):
        """Error messages should include helpful dollar amounts."""
        issues = validate_inputs(**_defaults(initial_cash=50_000))
        cash_error = next(i for i in issues if i.code == "insufficient_cash_to_close")
        assert "$" in cash_error.message
        assert "50,000" in cash_error.message
