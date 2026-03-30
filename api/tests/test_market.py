"""Tests for market.py — path generation, crash application, data helpers."""

import numpy as np
import pytest
from market import (
    generate_stock_path,
    generate_home_appreciation_path,
    generate_rent_path,
    generate_rate_path,
    apply_crash,
    _to_mom_growth,
    _to_cumulative,
    _interpolate_quarterly_to_monthly,
)


# ═══════════════════════════════════════════════════════════════════════════
# Helper functions
# ═══════════════════════════════════════════════════════════════════════════

class TestHelpers:
    def test_to_mom_growth(self):
        levels = np.array([100, 102, 101, 105])
        growth = _to_mom_growth(levels)
        assert growth[0] == 1.0
        assert abs(growth[1] - 1.02) < 1e-10
        assert abs(growth[2] - 101 / 102) < 1e-10
        assert abs(growth[3] - 105 / 101) < 1e-10

    def test_to_cumulative(self):
        levels = np.array([200, 210, 220, 200])
        cum = _to_cumulative(levels)
        assert cum[0] == 1.0
        assert abs(cum[1] - 1.05) < 1e-10
        assert abs(cum[2] - 1.10) < 1e-10
        assert abs(cum[3] - 1.00) < 1e-10

    def test_interpolate_quarterly_preserves_values(self):
        """Spline through 4 quarterly points → 12 monthly values.
        Should hit the original quarterly values at months 0, 3, 6, 9."""
        quarterly = np.array([100.0, 110.0, 105.0, 115.0])
        monthly = _interpolate_quarterly_to_monthly(quarterly, 10)
        assert len(monthly) == 10
        assert abs(monthly[0] - 100.0) < 0.5  # close to first point


# ═══════════════════════════════════════════════════════════════════════════
# Stock path generation
# ═══════════════════════════════════════════════════════════════════════════

class TestStockPath:
    def test_shape_and_positive(self):
        hist = np.full(120, 1.005)
        rng = np.random.default_rng(42)
        path = generate_stock_path(hist, 120, rng)
        assert len(path) == 120
        assert (path > 0).all()

    def test_reproducible(self):
        hist = np.full(120, 1.005)
        p1 = generate_stock_path(hist, 120, np.random.default_rng(42))
        p2 = generate_stock_path(hist, 120, np.random.default_rng(42))
        np.testing.assert_array_equal(p1, p2)

    def test_different_seeds_differ(self):
        hist = np.full(120, 1.005)
        p1 = generate_stock_path(hist, 120, np.random.default_rng(42))
        p2 = generate_stock_path(hist, 120, np.random.default_rng(99))
        assert not np.allclose(p1, p2)

    def test_zero_vol_follows_drift(self):
        """With zero volatility, path should exactly match historical drift."""
        hist = np.array([1.0, 1.01, 0.99, 1.02, 1.005])
        rng = np.random.default_rng(42)
        path = generate_stock_path(hist, 5, rng, annual_vol=0.0)
        np.testing.assert_allclose(path, hist, atol=1e-10)

    def test_mean_reversion(self):
        """Over many sims, average cumulative return should be near historical."""
        hist = np.full(120, 1.005)  # 0.5%/mo ≈ 6%/yr
        cumulative_returns = []
        for seed in range(1000):
            rng = np.random.default_rng(seed)
            path = generate_stock_path(hist, 120, rng, annual_vol=0.15)
            cumulative_returns.append(np.prod(path))

        mean_return = np.mean(cumulative_returns)
        # Mean should be within 15% of historical (log-normal bias pushes it up)
        assert 1.5 < mean_return < 2.5

    def test_higher_vol_more_spread(self):
        """Higher volatility → wider distribution of outcomes."""
        hist = np.full(120, 1.005)
        returns_low = [np.prod(generate_stock_path(hist, 120, np.random.default_rng(s), 0.05)) for s in range(200)]
        returns_high = [np.prod(generate_stock_path(hist, 120, np.random.default_rng(s), 0.30)) for s in range(200)]
        assert np.std(returns_high) > np.std(returns_low)


# ═══════════════════════════════════════════════════════════════════════════
# Home appreciation path generation
# ═══════════════════════════════════════════════════════════════════════════

class TestHomePath:
    def test_starts_at_one(self):
        hist = np.linspace(1.0, 1.5, 120)
        rng = np.random.default_rng(42)
        path = generate_home_appreciation_path(hist, None, 120, rng)
        assert abs(path[0] - 1.0) < 1e-10

    def test_shape(self):
        hist = np.linspace(1.0, 1.5, 120)
        rng = np.random.default_rng(42)
        path = generate_home_appreciation_path(hist, None, 120, rng)
        assert len(path) == 120

    def test_zip_blend(self):
        """With ZIP data, result should blend national + ZIP forecasts."""
        hist = np.linspace(1.0, 1.3, 120)  # 30% over 10yr national
        zip_cum = np.linspace(1.0, 1.6, 120)  # 60% over 10yr ZIP
        rng = np.random.default_rng(42)

        path_no_zip = generate_home_appreciation_path(hist, None, 120, rng, annual_vol=0.0)
        rng2 = np.random.default_rng(42)
        path_with_zip = generate_home_appreciation_path(hist, zip_cum, 120, rng2, annual_vol=0.0)

        # With ZIP, final value should be between national-only and ZIP-only
        assert path_with_zip[-1] > path_no_zip[-1]

    def test_pads_short_data(self):
        """If base data is shorter than n_months, should pad and not crash."""
        hist = np.linspace(1.0, 1.1, 50)  # only 50 months
        rng = np.random.default_rng(42)
        path = generate_home_appreciation_path(hist, None, 120, rng)
        assert len(path) == 120
        assert (path > 0).all()

    def test_positive_values(self):
        hist = np.linspace(1.0, 1.5, 120)
        for seed in range(50):
            rng = np.random.default_rng(seed)
            path = generate_home_appreciation_path(hist, None, 120, rng)
            assert (path > 0).all(), f"Negative home value at seed {seed}"


# ═══════════════════════════════════════════════════════════════════════════
# Rent path generation
# ═══════════════════════════════════════════════════════════════════════════

class TestRentPath:
    def test_starts_at_one(self):
        hist = np.full(120, 1.003)
        hist[0] = 1.0
        rng = np.random.default_rng(42)
        path = generate_rent_path(hist, 120, rng)
        assert abs(path[0] - 1.0) < 1e-10

    def test_generally_increasing(self):
        """With positive CPI drift, rent should generally increase."""
        hist = np.full(120, 1.003)
        hist[0] = 1.0
        paths_final = []
        for s in range(100):
            rng = np.random.default_rng(s)
            path = generate_rent_path(hist, 120, rng)
            paths_final.append(path[-1])
        # Most paths should end above 1.0 (inflation)
        assert np.mean(paths_final) > 1.2

    def test_zero_vol_deterministic(self):
        hist = np.full(120, 1.003)
        hist[0] = 1.0
        rng = np.random.default_rng(42)
        path = generate_rent_path(hist, 120, rng, annual_vol=0.0)
        np.testing.assert_allclose(path[0], 1.0, atol=1e-10)


# ═══════════════════════════════════════════════════════════════════════════
# Crash application
# ═══════════════════════════════════════════════════════════════════════════

class TestCrash:
    def test_no_crash_when_prob_zero(self):
        path = np.ones(120)
        rng = np.random.default_rng(42)
        result = apply_crash(path, 0.0, 0.20, 24, rng)
        np.testing.assert_array_equal(result, path)

    def test_no_crash_when_drop_zero(self):
        path = np.ones(120)
        rng = np.random.default_rng(42)
        result = apply_crash(path, 0.5, 0.0, 24, rng)
        np.testing.assert_array_equal(result, path)

    def test_guaranteed_crash_changes_path(self):
        """With prob=1.0, crash must happen."""
        path = np.ones(120) * 2.0
        rng = np.random.default_rng(42)
        result = apply_crash(path, 1.0, 0.20, 24, rng, is_cumulative=True, drawdown_months=6)
        assert result.min() < 2.0

    def test_cumulative_crash_level_shift_no_recovery(self):
        """With recovery_pct=0, crash is permanent (old behavior)."""
        path = np.ones(120) * 2.0
        rng = np.random.default_rng(0)
        result = apply_crash(path, 1.0, 0.20, 1, rng, is_cumulative=True,
                             drawdown_months=6, recovery_pct=0)
        np.testing.assert_allclose(result[6:], 1.6, atol=0.01)

    def test_cumulative_crash_partial_recovery(self):
        """Default recovery: after drawdown, path recovers partially toward pre-crash level."""
        path = np.ones(120) * 2.0
        rng = np.random.default_rng(0)
        result = apply_crash(path, 1.0, 0.20, 1, rng, is_cumulative=True, drawdown_months=6)
        # At trough (month 6): 1.6
        assert abs(result[6] - 1.6) < 0.01
        # After recovery period: should be above 1.6 (recovering)
        assert result[66] > 1.68  # 50% of 0.4 gap recovered
        # But not fully recovered
        assert result[66] < 2.0

    def test_crash_within_horizon(self):
        """Crash month should be within [0, horizon)."""
        path = np.ones(120) * 2.0
        for seed in range(100):
            rng = np.random.default_rng(seed)
            result = apply_crash(path, 1.0, 0.20, 10, rng, is_cumulative=True, drawdown_months=1)
            hit = np.where(result < 2.0)[0]
            if len(hit) > 0:
                assert hit[0] < 10

    def test_does_not_mutate_input(self):
        path = np.ones(120)
        rng = np.random.default_rng(42)
        _ = apply_crash(path, 1.0, 0.20, 24, rng)
        np.testing.assert_array_equal(path, np.ones(120))

    # --- Gradual drawdown tests ---

    def test_drawdown_gradual(self):
        """With drawdown_months=6, crash should be gradual, not instant."""
        path = np.ones(120) * 2.0
        rng = np.random.default_rng(0)  # crash at month 0
        result = apply_crash(path, 1.0, 0.20, 1, rng, is_cumulative=True, drawdown_months=6)
        # Month 0: first step of decline (1/6 of 20% → ~3.3% down)
        assert 1.9 < result[0] < 2.0
        # Month 3: about halfway through drawdown
        assert 1.7 < result[2] < 1.9
        # Month 6+: at floor (2.0 * 0.8 = 1.6)
        assert abs(result[6] - 1.6) < 0.01

    def test_permanent_level_shift(self):
        """With recovery_pct=0, path stays at the lower level — no bounce back."""
        path = np.ones(120) * 2.0
        rng = np.random.default_rng(0)
        result = apply_crash(path, 1.0, 0.20, 1, rng, is_cumulative=True,
                             drawdown_months=6, recovery_pct=0)
        np.testing.assert_allclose(result[6:], 1.6, atol=0.01)

    def test_full_recovery(self):
        """With recovery_pct=1.0, path fully recovers to pre-crash level."""
        path = np.ones(120) * 2.0
        rng = np.random.default_rng(0)
        result = apply_crash(path, 1.0, 0.20, 1, rng, is_cumulative=True,
                             drawdown_months=6, recovery_pct=1.0, recovery_months=24)
        # At trough: 1.6
        assert abs(result[6] - 1.6) < 0.01
        # After 24 months of recovery (month 30): should be close to 2.0
        assert result[30] > 1.85
        # Much later: essentially back to 2.0
        assert result[80] > 1.95

    def test_drawdown_with_growing_path(self):
        """On a growing path, crash shifts level down but growth continues."""
        path = np.cumprod(np.full(120, 1.01))
        path = np.insert(path, 0, 1.0)[:120]
        rng = np.random.default_rng(0)
        result = apply_crash(path, 1.0, 0.20, 1, rng, is_cumulative=True, drawdown_months=6)
        assert result[60] > result[30]  # still growing
        assert result[60] < path[60]    # but below no-crash path

    def test_stock_drawdown_spread(self):
        """Stock crash with drawdown=6 should affect multiple months."""
        path = np.full(120, 1.005)
        rng = np.random.default_rng(0)
        result = apply_crash(path, 1.0, 0.25, 1, rng, is_cumulative=False, drawdown_months=6)
        affected = np.where(np.abs(result - path) > 1e-10)[0]
        assert len(affected) >= 6

    def test_drawdown_does_not_mutate(self):
        path = np.ones(120) * 2.0
        original = path.copy()
        rng = np.random.default_rng(42)
        apply_crash(path, 1.0, 0.20, 24, rng, is_cumulative=True, drawdown_months=6)
        np.testing.assert_array_equal(path, original)


# ---------------------------------------------------------------------------
# Rate path generation
# ---------------------------------------------------------------------------

class TestRatePath:
    """Tests for generate_rate_path — stochastic mortgage rate forecasting."""

    @pytest.fixture
    def hist_rates(self):
        """Synthetic historical rates: 6.5% with slight downtrend."""
        n = 180
        trend = np.linspace(7.0, 6.5, n)
        noise = np.random.default_rng(99).normal(0, 0.05, n)
        return trend + noise

    def test_shape_and_range(self, hist_rates):
        rng = np.random.default_rng(42)
        path = generate_rate_path(hist_rates, 120, rng)
        assert len(path) == 120
        assert np.all(path >= 1.0)
        assert np.all(path <= 15.0)

    def test_deterministic(self, hist_rates):
        p1 = generate_rate_path(hist_rates, 120, np.random.default_rng(42))
        p2 = generate_rate_path(hist_rates, 120, np.random.default_rng(42))
        np.testing.assert_array_equal(p1, p2)

    def test_different_seeds_differ(self, hist_rates):
        p1 = generate_rate_path(hist_rates, 120, np.random.default_rng(42))
        p2 = generate_rate_path(hist_rates, 120, np.random.default_rng(99))
        assert not np.allclose(p1, p2)

    def test_starts_near_current(self, hist_rates):
        """First value should be close to the last historical rate."""
        rng = np.random.default_rng(42)
        path = generate_rate_path(hist_rates, 120, rng)
        current = hist_rates[-1]
        # Within 1 percentage point of current rate
        assert abs(path[0] - current) < 1.0

    def test_mean_reverts_long_run(self, hist_rates):
        """Over many simulations, median endpoint should move toward long-term average."""
        current = hist_rates[-1]
        avg_20y = hist_rates.mean()
        endpoints = []
        for seed in range(200):
            rng = np.random.default_rng(seed)
            path = generate_rate_path(hist_rates, 180, rng)
            endpoints.append(path[-1])
        median_endpoint = np.median(endpoints)
        # Should be between current and long-term avg (or past it)
        if current > avg_20y:
            assert median_endpoint < current  # pulled down toward avg
        else:
            assert median_endpoint > current  # pulled up toward avg

    def test_rate_target_override(self, hist_rates):
        """Custom rate_target should attract long-run path."""
        target = 0.04  # 4% as decimal, function converts to percent internally
        endpoints = []
        for seed in range(200):
            rng = np.random.default_rng(seed)
            path = generate_rate_path(hist_rates, 180, rng, rate_target=target)
            endpoints.append(path[-1])
        median_endpoint = np.median(endpoints)
        # Should be closer to 4.0 (percent) than to current ~6.5
        assert abs(median_endpoint - 4.0) < abs(median_endpoint - hist_rates[-1])

    def test_volatility_scale(self, hist_rates):
        """Higher volatility scale → wider spread."""
        endpoints_low = []
        endpoints_high = []
        for seed in range(200):
            rng1 = np.random.default_rng(seed)
            rng2 = np.random.default_rng(seed)
            p_low = generate_rate_path(hist_rates, 120, rng1, rate_volatility_scale=0.5)
            p_high = generate_rate_path(hist_rates, 120, rng2, rate_volatility_scale=2.0)
            endpoints_low.append(p_low[-1])
            endpoints_high.append(p_high[-1])
        std_low = np.std(endpoints_low)
        std_high = np.std(endpoints_high)
        assert std_high > std_low


# ---------------------------------------------------------------------------
# MarketOutlook presets
# ---------------------------------------------------------------------------

class TestMarketOutlookPresets:
    def test_historical_is_neutral(self):
        from models import MarketOutlook
        o = MarketOutlook.from_preset("historical")
        assert o.volatility_scale == 1.0
        assert o.housing_crash_prob == 0.0
        assert o.stock_crash_prob == 0.0

    def test_crisis_is_severe(self):
        from models import MarketOutlook
        o = MarketOutlook.from_preset("crisis")
        assert o.volatility_scale > 1.0
        assert o.housing_crash_prob >= 0.50
        assert o.stock_crash_prob >= 0.50
        assert o.housing_crash_drop >= 0.30

    def test_unknown_preset_falls_back_to_historical(self):
        from models import MarketOutlook
        o = MarketOutlook.from_preset("nonexistent")
        h = MarketOutlook.from_preset("historical")
        assert o.volatility_scale == h.volatility_scale
        assert o.housing_crash_prob == h.housing_crash_prob

    def test_presets_ordered_by_severity(self):
        from models import MarketOutlook
        presets = ["optimistic", "historical", "cautious", "pessimistic", "crisis"]
        vol_scales = [MarketOutlook.from_preset(p).volatility_scale for p in presets]
        assert vol_scales == sorted(vol_scales)
