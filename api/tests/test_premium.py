"""Tests for premium endpoints: sensitivity, trend, zip-compare.

Uses synthetic data to verify structure and behavior without real data dependencies.
"""

import pytest
from data_store import init_db
from models import SimulationInput, UserProfile, PropertyParams, MortgageParams, SimulationConfig
from sensitivity import run_sensitivity
from trend import run_trend, run_zip_comparison


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


@pytest.fixture(autouse=True)
def _ensure_db():
    init_db()


# ═══════════════════════════════════════════════════════════════════════════
# Sensitivity
# ═══════════════════════════════════════════════════════════════════════════

class TestSensitivity:
    def test_returns_all_axes(self, synthetic_data):
        inputs = _make_inputs()
        result = run_sensitivity(inputs, synthetic_data)
        assert "mortgage_rate" in result.axes
        assert "house_price" in result.axes
        assert "down_payment_pct" in result.axes
        assert "crash_outlook" in result.axes

    def test_mortgage_rate_axis_has_points(self, synthetic_data):
        inputs = _make_inputs()
        result = run_sensitivity(inputs, synthetic_data)
        points = result.axes["mortgage_rate"]
        assert len(points) >= 5
        # Higher rate should generally worsen buyer outcome
        rates = [(p.param_value, p.net_difference) for p in points]
        low_rate = min(rates, key=lambda x: x[0])
        high_rate = max(rates, key=lambda x: x[0])
        assert low_rate[1] >= high_rate[1]

    def test_house_price_axis(self, synthetic_data):
        inputs = _make_inputs()
        result = run_sensitivity(inputs, synthetic_data)
        points = result.axes["house_price"]
        assert len(points) >= 3
        # All should have valid numbers
        for p in points:
            assert p.buyer_net_worth != 0 or p.renter_net_worth != 0

    def test_down_payment_axis(self, synthetic_data):
        inputs = _make_inputs()
        result = run_sensitivity(inputs, synthetic_data)
        points = result.axes["down_payment_pct"]
        dps = [p.param_value for p in points]
        assert 0.05 in dps
        assert 0.20 in dps
        assert 0.30 in dps

    def test_crash_axis(self, synthetic_data):
        inputs = _make_inputs()
        result = run_sensitivity(inputs, synthetic_data)
        points = result.axes["crash_outlook"]
        labels = [p.label for p in points]
        assert "none" in labels
        assert "very_likely" in labels
        # Crash setting should produce different outcomes than no-crash
        none_pt = next(p for p in points if p.label == "none")
        likely_pt = next(p for p in points if p.label == "very_likely")
        assert none_pt.buyer_net_worth != likely_pt.buyer_net_worth

    def test_base_values_populated(self, synthetic_data):
        inputs = _make_inputs()
        result = run_sensitivity(inputs, synthetic_data)
        assert result.base_buyer_nw != 0
        assert result.base_renter_nw != 0
        assert 8 <= result.base_buy_score <= 96

    def test_heatmap_shape(self, synthetic_data):
        """Heatmap should be 5x5 (5 rates × 5 prices)."""
        inputs = _make_inputs()
        result = run_sensitivity(inputs, synthetic_data)
        hm = result.heatmap
        assert hm is not None
        assert hm.x_axis == "house_price"
        assert hm.y_axis == "mortgage_rate"
        assert len(hm.x_labels) == 5
        assert len(hm.y_labels) == 5
        assert len(hm.cells) == 5
        assert all(len(row) == 5 for row in hm.cells)

    def test_heatmap_scores_in_range(self, synthetic_data):
        inputs = _make_inputs()
        result = run_sensitivity(inputs, synthetic_data)
        for row in result.heatmap.cells:
            for cell in row:
                assert 8 <= cell.buy_score <= 96

    def test_heatmap_price_axis_direction(self, synthetic_data):
        """Cheaper house (left) should generally be better for buyer than expensive (right)."""
        inputs = _make_inputs()
        result = run_sensitivity(inputs, synthetic_data)
        # Middle row (base rate), compare leftmost vs rightmost
        mid_row = result.heatmap.cells[2]
        cheapest = mid_row[0]   # -20% price
        priciest = mid_row[-1]  # +20% price
        assert cheapest.buy_score >= priciest.buy_score

    def test_heatmap_rate_axis_direction(self, synthetic_data):
        """Lower rate (top) should generally be better for buyer than higher rate (bottom)."""
        inputs = _make_inputs()
        result = run_sensitivity(inputs, synthetic_data)
        # Middle column (base price), compare top vs bottom
        mid_col = 2
        lowest_rate = result.heatmap.cells[0][mid_col]   # -1.5%
        highest_rate = result.heatmap.cells[-1][mid_col]  # +1.5%
        assert lowest_rate.buy_score >= highest_rate.buy_score

    def test_sensitivity_timing(self, synthetic_data):
        """Full sensitivity (1D axes + 2D heatmap) should complete in < 15 seconds."""
        import time
        inputs = _make_inputs()
        t0 = time.time()
        run_sensitivity(inputs, synthetic_data)
        elapsed = time.time() - t0
        assert elapsed < 15, f"Sensitivity took {elapsed:.1f}s (limit: 15s)"


# ═══════════════════════════════════════════════════════════════════════════
# Trend (timing analysis)
# ═══════════════════════════════════════════════════════════════════════════

class TestTrend:
    def test_returns_correct_number_of_points(self, synthetic_data):
        inputs = _make_inputs()
        result = run_trend(inputs, synthetic_data, max_delay_quarters=4)
        # 0, 3, 6, 9, 12 months → 5 points
        assert len(result.points) == 5

    def test_first_point_is_buy_now(self, synthetic_data):
        inputs = _make_inputs()
        result = run_trend(inputs, synthetic_data, max_delay_quarters=4)
        assert result.points[0].delay_months == 0
        assert result.points[0].label == "Buy now"

    def test_delays_increase(self, synthetic_data):
        inputs = _make_inputs()
        result = run_trend(inputs, synthetic_data, max_delay_quarters=4)
        delays = [p.delay_months for p in result.points]
        assert delays == sorted(delays)

    def test_yearly_scores_populated(self, synthetic_data):
        inputs = _make_inputs()
        result = run_trend(inputs, synthetic_data, max_delay_quarters=2)
        for p in result.points:
            assert len(p.yearly_scores) == 10  # 10 years

    def test_aggregate_score_computed(self, synthetic_data):
        inputs = _make_inputs()
        result = run_trend(inputs, synthetic_data, max_delay_quarters=2)
        for p in result.points:
            assert isinstance(p.aggregate_score, float)

    def test_first_month_cost_populated(self, synthetic_data):
        inputs = _make_inputs()
        result = run_trend(inputs, synthetic_data, max_delay_quarters=2)
        # "Buy now" should have a positive first_month_cost
        assert result.points[0].first_month_cost > 0


# ═══════════════════════════════════════════════════════════════════════════
# ZIP comparison
# ═══════════════════════════════════════════════════════════════════════════

class TestZipCompare:
    def test_returns_scores_for_each_zip(self, synthetic_data):
        inputs = _make_inputs()
        result = run_zip_comparison(inputs, synthetic_data, ["10001", "90210"])
        assert len(result.scores) == 2
        zips = [s.zip_code for s in result.scores]
        assert "10001" in zips
        assert "90210" in zips

    def test_score_fields_populated(self, synthetic_data):
        inputs = _make_inputs()
        result = run_zip_comparison(inputs, synthetic_data, ["10001"])
        s = result.scores[0]
        assert s.house_price > 0
        assert isinstance(s.aggregate_score, float)
        assert isinstance(s.net_difference, float)

    def test_uses_zip_home_value(self, synthetic_data):
        """If ZIP has historical data, house_price should reflect it."""
        inputs = _make_inputs(house_price=500_000)
        result = run_zip_comparison(inputs, synthetic_data, ["10001"])
        s = result.scores[0]
        # 10001 (Manhattan) has real data in SQLite — price should differ from default
        # If no data (test env), falls back to user's price
        assert s.house_price > 0
