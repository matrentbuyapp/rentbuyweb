"""Tests for scoring.py — deterministic buy score and verdict."""

import pytest
from models import SimulationInput, UserProfile, PropertyParams, MortgageParams, SimulationConfig
from simulator import run_simulation
from scoring import compute_buy_score, compute_verdict


def _make_inputs(**overrides) -> SimulationInput:
    user_kw = {
        "monthly_rent": 3000, "monthly_budget": 4500, "initial_cash": 100_000,
        "yearly_income": 120_000, "filing_status": "single", "risk_appetite": "moderate",
    }
    prop_kw = {
        "house_price": 500_000, "down_payment_pct": 0.20, "closing_cost_pct": 0.03,
        "maintenance_rate": 0.01, "insurance_annual": 2000, "sell_cost_pct": 0.06,
        "move_in_cost": 0,
    }
    mort_kw = {"rate": 0.065, "term_years": 30, "credit_quality": "good"}
    cfg_kw = {"years": 10, "num_simulations": 50, "buy_delay_months": 0}
    for k, v in overrides.items():
        for d in [user_kw, prop_kw, mort_kw, cfg_kw]:
            if k in d:
                d[k] = v
    return SimulationInput(
        user=UserProfile(**user_kw), property=PropertyParams(**prop_kw),
        mortgage=MortgageParams(**mort_kw), config=SimulationConfig(**cfg_kw),
    )


class TestBuyScore:
    def test_score_range(self, synthetic_data):
        inputs = _make_inputs()
        result = run_simulation(inputs, synthetic_data, housing_crash_prob=0, stock_crash_prob=0)
        score = compute_buy_score(result)
        assert 8 <= score <= 96

    def test_deterministic(self, synthetic_data):
        """Same inputs → same score every time."""
        inputs = _make_inputs()
        r1 = run_simulation(inputs, synthetic_data, housing_crash_prob=0, stock_crash_prob=0)
        r2 = run_simulation(inputs, synthetic_data, housing_crash_prob=0, stock_crash_prob=0)
        assert compute_buy_score(r1) == compute_buy_score(r2)

    def test_crash_lowers_score(self, synthetic_data):
        inputs = _make_inputs()
        r_safe = run_simulation(inputs, synthetic_data, housing_crash_prob=0, stock_crash_prob=0)
        r_crash = run_simulation(inputs, synthetic_data, housing_crash_prob=0.5, housing_crash_drop=0.30,
                                 stock_crash_prob=0.5, stock_crash_drop=0.30)
        assert compute_buy_score(r_safe) >= compute_buy_score(r_crash)

    def test_over_budget_lowers_score(self, synthetic_data):
        """Very tight budget → worse affordability → lower score."""
        r_easy = run_simulation(_make_inputs(monthly_budget=6000), synthetic_data,
                                housing_crash_prob=0, stock_crash_prob=0)
        r_tight = run_simulation(_make_inputs(monthly_budget=3500), synthetic_data,
                                 housing_crash_prob=0, stock_crash_prob=0)
        assert compute_buy_score(r_easy) >= compute_buy_score(r_tight)


class TestVerdict:
    def test_high_score(self):
        assert "strong" in compute_verdict(85).lower()

    def test_low_score(self):
        assert "rent" in compute_verdict(25).lower()

    def test_mid_score(self):
        v = compute_verdict(50)
        assert "toss" in v.lower() or "weigh" in v.lower()

    def test_deterministic(self):
        assert compute_verdict(72) == compute_verdict(72)

    def test_boundary_values(self):
        """Verify all boundary transitions produce valid strings."""
        for score in [8, 34, 35, 49, 50, 64, 65, 79, 80, 96]:
            v = compute_verdict(score)
            assert isinstance(v, str)
            assert len(v) > 10
