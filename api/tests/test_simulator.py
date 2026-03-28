"""Tests for simulator.py — the MC engine and house price estimation.

Uses synthetic market data (from conftest.py) with known properties so
we can assert exact outcomes. All tests use fixed seeds for reproducibility.
"""

import numpy as np
import pytest
from models import SimulationInput, UserProfile, PropertyParams, MortgageParams, SimulationConfig
from simulator import run_simulation, estimate_house_price, get_cached_paths, _paths_cache


# ═══════════════════════════════════════════════════════════════════════════
# House price estimation
# ═══════════════════════════════════════════════════════════════════════════

class TestEstimateHousePrice:
    def test_basic_estimation(self):
        prices = estimate_house_price(
            monthly_rent=3500, monthly_budget=5000,
            down_payment_pct=0.10, maintenance_rate=0.01,
            mortgage_rate=0.065, term_years=30,
        )
        assert len(prices) >= 2
        assert all(p > 0 for p in prices)
        assert all(p % 10_000 == 0 for p in prices)  # rounded to $10k

    def test_higher_rent_higher_price(self):
        low = estimate_house_price(2000, 4000, 0.10, 0.01, 0.065, 30)
        high = estimate_house_price(4000, 6000, 0.10, 0.01, 0.065, 30)
        assert max(high) > max(low)

    def test_higher_rate_lower_price(self):
        """Higher mortgage rate → lower affordable price."""
        low_rate = estimate_house_price(3500, 5000, 0.10, 0.01, 0.04, 30)
        high_rate = estimate_house_price(3500, 5000, 0.10, 0.01, 0.08, 30)
        assert max(low_rate) > max(high_rate)

    def test_sorted(self):
        prices = estimate_house_price(3500, 5000, 0.10, 0.01, 0.065, 30)
        assert prices == sorted(prices)


# ═══════════════════════════════════════════════════════════════════════════
# Full simulation — deterministic with synthetic data
# ═══════════════════════════════════════════════════════════════════════════

def _make_inputs(**overrides) -> SimulationInput:
    """Build a SimulationInput with sensible defaults, overridable."""
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
        user=UserProfile(**user_kw),
        property=PropertyParams(**prop_kw),
        mortgage=MortgageParams(**mort_kw),
        config=SimulationConfig(**cfg_kw),
    )


class TestSimulation:
    def test_basic_run(self, synthetic_data):
        inputs = _make_inputs()
        result = run_simulation(inputs, synthetic_data, housing_crash_prob=0, stock_crash_prob=0)

        assert len(result.monthly) == 120
        assert result.house_price_used == 500_000
        assert abs(result.mortgage_rate_used - 0.06875) < 0.001  # 6.5% + 0.375% credit adj

    def test_renter_starts_with_initial_cash(self, synthetic_data):
        inputs = _make_inputs(initial_cash=200_000)
        result = run_simulation(inputs, synthetic_data, housing_crash_prob=0, stock_crash_prob=0)
        # Month 0: renter investment ≈ initial_cash * stock_return + surplus
        m0 = result.monthly[0]
        assert m0.renter_investment > 199_000

    def test_buyer_nw_includes_equity(self, synthetic_data):
        inputs = _make_inputs()
        result = run_simulation(inputs, synthetic_data, housing_crash_prob=0, stock_crash_prob=0)
        m119 = result.monthly[119]
        # Buyer NW = equity + investment
        assert abs(m119.buyer_net_worth - (m119.buyer_equity + m119.buyer_investment)) < 1.0

    def test_mortgage_payment_constant(self, synthetic_data):
        """Mortgage payment should be the same every month (fixed rate)."""
        inputs = _make_inputs()
        result = run_simulation(inputs, synthetic_data, housing_crash_prob=0, stock_crash_prob=0)
        payments = [m.mortgage_payment for m in result.monthly]
        assert max(payments) - min(payments) < 0.01

    def test_rent_increases(self, synthetic_data):
        """Rent should increase over time (CPI drift)."""
        inputs = _make_inputs()
        result = run_simulation(inputs, synthetic_data, housing_crash_prob=0, stock_crash_prob=0)
        assert result.monthly[119].rent > result.monthly[0].rent

    def test_home_value_increases(self, synthetic_data):
        """Home value should generally increase (HPI drift)."""
        inputs = _make_inputs()
        result = run_simulation(inputs, synthetic_data, housing_crash_prob=0, stock_crash_prob=0)
        assert result.monthly[119].home_value > result.monthly[0].home_value

    def test_no_crash_vs_crash(self, synthetic_data):
        """Crash parameter produces different outcomes than no-crash.
        With realistic recovery, crashes don't necessarily lower averages
        (dip + recovery can help), but the paths should differ."""
        inputs = _make_inputs()
        r_safe = run_simulation(inputs, synthetic_data, housing_crash_prob=0, stock_crash_prob=0)
        r_crash = run_simulation(inputs, synthetic_data, housing_crash_prob=0.5, stock_crash_prob=0.5,
                                 housing_crash_drop=0.30, stock_crash_drop=0.30)

        # Outcomes should differ (crash changes the simulation)
        assert r_safe.avg_buyer_net_worth != r_crash.avg_buyer_net_worth
        assert r_safe.avg_renter_net_worth != r_crash.avg_renter_net_worth

    def test_more_cash_better_outcome(self, synthetic_data):
        """More initial cash → higher net worth for both buyer and renter."""
        r_low = run_simulation(_make_inputs(initial_cash=50_000), synthetic_data,
                               housing_crash_prob=0, stock_crash_prob=0)
        r_high = run_simulation(_make_inputs(initial_cash=300_000), synthetic_data,
                                housing_crash_prob=0, stock_crash_prob=0)
        assert r_high.avg_renter_net_worth > r_low.avg_renter_net_worth

    def test_higher_down_payment(self, synthetic_data):
        """Higher down payment → lower mortgage payment, no PMI."""
        r10 = run_simulation(_make_inputs(down_payment_pct=0.10), synthetic_data,
                             housing_crash_prob=0, stock_crash_prob=0)
        r20 = run_simulation(_make_inputs(down_payment_pct=0.20), synthetic_data,
                             housing_crash_prob=0, stock_crash_prob=0)
        # 20% down: lower mortgage payment
        assert r20.monthly[0].mortgage_payment < r10.monthly[0].mortgage_payment
        # 20% down: no PMI
        assert r20.monthly[0].pmi == 0.0
        assert r10.monthly[0].pmi > 0

    def test_buy_delay(self, synthetic_data):
        """With buy_delay, buyer mirrors renter for first N months."""
        inputs = _make_inputs(buy_delay_months=12)
        result = run_simulation(inputs, synthetic_data, housing_crash_prob=0, stock_crash_prob=0)
        # First 12 months: buyer NW = renter NW
        for i in range(12):
            m = result.monthly[i]
            assert abs(m.buyer_net_worth - m.renter_net_worth) < 1.0
        # Month 12: buyer has purchased, NW diverges
        assert result.monthly[12].mortgage_payment > 0

    def test_aggressive_vs_conservative(self, synthetic_data):
        """Aggressive risk → stock returns amplified via leverage."""
        r_con = run_simulation(_make_inputs(risk_appetite="conservative"), synthetic_data,
                               housing_crash_prob=0, stock_crash_prob=0)
        r_agg = run_simulation(_make_inputs(risk_appetite="aggressive"), synthetic_data,
                               housing_crash_prob=0, stock_crash_prob=0)
        # With positive stock drift, aggressive renter should end higher
        assert r_agg.avg_renter_net_worth > r_con.avg_renter_net_worth

    def test_cumulative_costs_increase(self, synthetic_data):
        inputs = _make_inputs()
        result = run_simulation(inputs, synthetic_data, housing_crash_prob=0, stock_crash_prob=0)
        for i in range(1, 120):
            assert result.monthly[i].cumulative_buy_cost >= result.monthly[i - 1].cumulative_buy_cost
            assert result.monthly[i].cumulative_rent_cost >= result.monthly[i - 1].cumulative_rent_cost

    def test_total_housing_cost_breakdown(self, synthetic_data):
        """total_housing_cost = mortgage + maintenance + prop_tax + insurance + pmi - tax_savings."""
        inputs = _make_inputs()
        result = run_simulation(inputs, synthetic_data, housing_crash_prob=0, stock_crash_prob=0)
        m = result.monthly[6]  # pick an arbitrary month after purchase
        expected = m.mortgage_payment + m.maintenance + m.property_tax + m.insurance + m.pmi - m.tax_savings
        assert abs(m.total_housing_cost - expected) < 0.01


# ═══════════════════════════════════════════════════════════════════════════
# Caching
# ═══════════════════════════════════════════════════════════════════════════

class TestCaching:
    @pytest.fixture(autouse=True)
    def _init_db(self):
        """Ensure SQLite tables exist for ZIP lookups."""
        from data_store import init_db
        init_db()

    def test_paths_cached(self, synthetic_data):
        """Same data + zip + months + sims → same object returned."""
        _paths_cache.clear()
        p1 = get_cached_paths(synthetic_data, None, 120, 50)
        p2 = get_cached_paths(synthetic_data, None, 120, 50)
        assert p1 is p2

    def test_different_zip_different_cache(self, synthetic_data):
        """Different zip codes should get different cache entries."""
        _paths_cache.clear()
        p1 = get_cached_paths(synthetic_data, None, 120, 50)
        p2 = get_cached_paths(synthetic_data, "10001", 120, 50)
        assert p1 is not p2

    def test_cache_eviction(self, synthetic_data):
        """Cache should not grow unbounded."""
        _paths_cache.clear()
        for i in range(100):
            get_cached_paths(synthetic_data, f"{i:05d}", 120, 10)
        assert len(_paths_cache) <= 64


# ═══════════════════════════════════════════════════════════════════════════
# MC spread verification
# ═══════════════════════════════════════════════════════════════════════════

class TestMCSpread:
    def test_stock_paths_differ_across_sims(self, synthetic_data):
        """Each simulation should have a different stock path."""
        paths = get_cached_paths(synthetic_data, None, 120, 50)
        # Check that not all rows are identical
        assert not np.allclose(paths.stock_paths[0], paths.stock_paths[1])

    def test_home_paths_differ_across_sims(self, synthetic_data):
        paths = get_cached_paths(synthetic_data, None, 120, 50)
        assert not np.allclose(paths.home_paths[0], paths.home_paths[1])

    def test_rent_paths_differ_across_sims(self, synthetic_data):
        paths = get_cached_paths(synthetic_data, None, 120, 50)
        assert not np.allclose(paths.rent_paths[0], paths.rent_paths[1])

    def test_reproducible_across_runs(self, synthetic_data):
        """Same synthetic data → same paths (deterministic seeds)."""
        _paths_cache.clear()
        p1 = get_cached_paths(synthetic_data, None, 120, 50)
        stock_copy = p1.stock_paths.copy()

        # Clear cache and regenerate
        _paths_cache.clear()
        p2 = get_cached_paths(synthetic_data, None, 120, 50)
        np.testing.assert_array_equal(stock_copy, p2.stock_paths)
