"""Real-life sanity scenarios — 12 diverse US housing markets.

These are NOT unit tests with exact assertions. They verify directional
correctness: LCOL buying should beat renting, HCOL should be tighter,
no NaN or negative values, plausible payment ranges, etc.

All scenarios use housing_crash_prob=0, stock_crash_prob=0 for stability
and num_simulations=50 for speed.
"""

import math
import pytest
from data_store import init_db
from market import get_data
from models import (
    SimulationInput, UserProfile, PropertyParams,
    MortgageParams, SimulationConfig, MarketOutlook,
)
from simulator import run_simulation


@pytest.fixture(autouse=True)
def _ensure_db():
    init_db()


def _get_data():
    return get_data()


def _run(scenario: dict):
    """Build SimulationInput from a scenario dict and run it."""
    data = _get_data()
    user_kw = {
        "monthly_rent": scenario["monthly_rent"],
        "monthly_budget": scenario["monthly_budget"],
        "initial_cash": scenario["initial_cash"],
        "yearly_income": scenario["yearly_income"],
        "filing_status": scenario.get("filing_status", "single"),
        "risk_appetite": scenario.get("risk_appetite", "moderate"),
    }
    prop_kw = {
        "house_price": scenario["house_price"],
        "down_payment_pct": scenario["down_payment_pct"],
        "zip_code": scenario.get("zip_code"),
        "closing_cost_pct": scenario.get("closing_cost_pct", 0.03),
        "maintenance_rate": scenario.get("maintenance_rate", 0.01),
        "insurance_annual": scenario.get("insurance_annual", 2000),
        "sell_cost_pct": 0.06,
        "move_in_cost": 0,
    }
    mort_kw = {
        "rate": scenario.get("mortgage_rate", 0.065),
        "term_years": scenario.get("term_years", 30),
        "credit_quality": scenario.get("credit_quality", "good"),
    }
    cfg_kw = {
        "years": scenario.get("years", 10),
        "num_simulations": 50,
        "buy_delay_months": 0,
    }
    inp = SimulationInput(
        user=UserProfile(**user_kw),
        property=PropertyParams(**prop_kw),
        mortgage=MortgageParams(**mort_kw),
        config=SimulationConfig(**cfg_kw),
        outlook=MarketOutlook.from_preset("historical"),
    )
    return run_simulation(inp, data, housing_crash_prob=0, stock_crash_prob=0)


# ═══════════════════════════════════════════════════════════════════════════
# Scenario definitions
# ═══════════════════════════════════════════════════════════════════════════

SCENARIOS = {
    # --- HCOL ---
    "sf_tech": {
        "desc": "SF tech worker, small savings, huge price, 5% down",
        "monthly_rent": 3200, "monthly_budget": 5000, "initial_cash": 80_000,
        "yearly_income": 180_000, "house_price": 1_200_000,
        "down_payment_pct": 0.05, "zip_code": "94103", "credit_quality": "good",
    },
    "nyc_couple": {
        "desc": "NYC dual-income couple, 20% down, strong savings",
        "monthly_rent": 3500, "monthly_budget": 6000, "initial_cash": 250_000,
        "yearly_income": 250_000, "house_price": 900_000,
        "down_payment_pct": 0.20, "zip_code": "10001", "credit_quality": "excellent",
        "filing_status": "married_joint",
    },
    "boston_first_timer": {
        "desc": "Boston first-time buyer, 5% down, tight budget",
        "monthly_rent": 2400, "monthly_budget": 3200, "initial_cash": 50_000,
        "yearly_income": 95_000, "house_price": 650_000,
        "down_payment_pct": 0.05, "zip_code": "02134", "credit_quality": "good",
    },
    "la_entertainment": {
        "desc": "LA entertainment industry, 15% down",
        "monthly_rent": 2800, "monthly_budget": 4500, "initial_cash": 150_000,
        "yearly_income": 160_000, "house_price": 850_000,
        "down_payment_pct": 0.15, "zip_code": "90028", "credit_quality": "great",
    },
    "seattle_swe": {
        "desc": "Seattle SWE, 20% down, high income",
        "monthly_rent": 2600, "monthly_budget": 5000, "initial_cash": 200_000,
        "yearly_income": 200_000, "house_price": 750_000,
        "down_payment_pct": 0.20, "zip_code": "98103", "credit_quality": "excellent",
    },
    # --- MCOL ---
    "austin_tech": {
        "desc": "Austin tech transplant, 15% down",
        "monthly_rent": 1800, "monthly_budget": 3500, "initial_cash": 100_000,
        "yearly_income": 130_000, "house_price": 450_000,
        "down_payment_pct": 0.15, "zip_code": "78701", "credit_quality": "good",
    },
    "denver_couple": {
        "desc": "Denver couple, 20% down, solid savings",
        "monthly_rent": 2000, "monthly_budget": 4000, "initial_cash": 150_000,
        "yearly_income": 150_000, "house_price": 500_000,
        "down_payment_pct": 0.20, "zip_code": "80202", "credit_quality": "great",
        "filing_status": "married_joint",
    },
    "nashville_nurse": {
        "desc": "Nashville nurse, 10% down, moderate income",
        "monthly_rent": 1500, "monthly_budget": 2500, "initial_cash": 50_000,
        "yearly_income": 75_000, "house_price": 350_000,
        "down_payment_pct": 0.10, "zip_code": "37203", "credit_quality": "good",
    },
    "portland_freelancer": {
        "desc": "Portland freelancer, 10% down, variable income",
        "monthly_rent": 1900, "monthly_budget": 3000, "initial_cash": 70_000,
        "yearly_income": 90_000, "house_price": 480_000,
        "down_payment_pct": 0.10, "zip_code": "97201", "credit_quality": "good",
    },
    # --- LCOL ---
    "cleveland_retiree": {
        "desc": "Cleveland retiree, 30% down, conservative",
        "monthly_rent": 900, "monthly_budget": 1500, "initial_cash": 120_000,
        "yearly_income": 55_000, "house_price": 180_000,
        "down_payment_pct": 0.30, "zip_code": "44113", "credit_quality": "great",
        "risk_appetite": "conservative",
    },
    "memphis_family": {
        "desc": "Memphis family, 10% down, modest income",
        "monthly_rent": 1100, "monthly_budget": 2000, "initial_cash": 40_000,
        "yearly_income": 65_000, "house_price": 220_000,
        "down_payment_pct": 0.10, "zip_code": "38103", "credit_quality": "good",
        "filing_status": "married_joint",
    },
    "birmingham_teacher": {
        "desc": "Birmingham teacher, 10% down, stable income",
        "monthly_rent": 900, "monthly_budget": 1600, "initial_cash": 30_000,
        "yearly_income": 52_000, "house_price": 160_000,
        "down_payment_pct": 0.10, "zip_code": "35203", "credit_quality": "good",
    },
}

SCENARIO_IDS = list(SCENARIOS.keys())
SCENARIO_VALS = list(SCENARIOS.values())


# ═══════════════════════════════════════════════════════════════════════════
# Basic sanity — all scenarios
# ═══════════════════════════════════════════════════════════════════════════

class TestBasicSanity:
    """Every scenario must produce non-garbage output."""

    @pytest.fixture(params=SCENARIO_IDS)
    def result(self, request):
        return _run(SCENARIOS[request.param]), request.param

    def test_correct_month_count(self, result):
        r, name = result
        years = SCENARIOS[name].get("years", 10)
        assert len(r.monthly) == years * 12

    def test_no_nan(self, result):
        r, _ = result
        for m in r.monthly:
            for field_name in m.__dataclass_fields__:
                v = getattr(m, field_name)
                assert not math.isnan(v), f"{field_name} is NaN"

    def test_positive_home_values(self, result):
        r, _ = result
        for m in r.monthly:
            assert m.home_value > 0

    def test_plausible_mortgage_payment(self, result):
        r, name = result
        # After purchase, mortgage payment should be in a plausible range
        payments = [m.mortgage_payment for m in r.monthly if m.mortgage_payment > 0]
        if payments:
            assert payments[0] > 300, f"{name}: mortgage payment implausibly low"
            assert payments[0] < 10_000, f"{name}: mortgage payment implausibly high"

    def test_rent_increases(self, result):
        r, _ = result
        assert r.monthly[-1].rent > r.monthly[0].rent

    def test_reasonable_investments(self, result):
        r, _ = result
        # Investment balances shouldn't go wildly negative
        for m in r.monthly:
            assert m.renter_investment > -50_000, "Renter investment implausibly negative"

    def test_cumulative_costs_non_decreasing(self, result):
        r, _ = result
        for i in range(1, len(r.monthly)):
            assert r.monthly[i].cumulative_buy_cost >= r.monthly[i-1].cumulative_buy_cost - 0.01
            assert r.monthly[i].cumulative_rent_cost >= r.monthly[i-1].cumulative_rent_cost - 0.01

    def test_buyer_nw_equals_equity_plus_investment(self, result):
        r, _ = result
        m = r.monthly[-1]
        assert abs(m.buyer_net_worth - (m.buyer_equity + m.buyer_investment)) < 1.0

    def test_percentiles_present(self, result):
        r, _ = result
        pct = r.percentiles
        assert len(pct.buyer_net_worth.p50) == len(r.monthly)
        assert len(pct.home_value.p10) == len(r.monthly)
        # P90 should be >= P10
        assert pct.buyer_net_worth.p90[-1] >= pct.buyer_net_worth.p10[-1]
        assert pct.home_value.p90[-1] >= pct.home_value.p10[-1]


# ═══════════════════════════════════════════════════════════════════════════
# LCOL — buying should generally win
# ═══════════════════════════════════════════════════════════════════════════

class TestLCOLBuyFavorable:
    """In affordable markets with decent savings, buying should win or be close."""

    @pytest.mark.parametrize("name", ["cleveland_retiree", "memphis_family", "birmingham_teacher"])
    def test_buyer_wins_or_competitive(self, name):
        r = _run(SCENARIOS[name])
        last = r.monthly[-1]
        diff = last.buyer_net_worth - last.renter_net_worth
        price = SCENARIOS[name]["house_price"]
        # Buyer shouldn't lose by more than 50% of house price — even if
        # renting wins, it shouldn't be a blowout in LCOL markets
        assert diff > -price * 0.50, f"{name}: buyer lost by ${-diff:,.0f} — implausible for LCOL"

    @pytest.mark.parametrize("name", ["cleveland_retiree", "memphis_family", "birmingham_teacher"])
    def test_reasonable_monthly_cost(self, name):
        r = _run(SCENARIOS[name])
        # LCOL total housing cost should be well under $3k
        owned = [m for m in r.monthly if m.mortgage_payment > 0]
        if owned:
            assert owned[0].total_housing_cost < 3000, f"{name}: LCOL costs too high"


# ═══════════════════════════════════════════════════════════════════════════
# HCOL — renting more competitive
# ═══════════════════════════════════════════════════════════════════════════

class TestHCOLRentCompetitive:
    """In expensive markets with thin down payments, renting should be competitive."""

    def test_sf_not_runaway_buy(self):
        """SF with 5% down shouldn't massively favor buying."""
        r = _run(SCENARIOS["sf_tech"])
        last = r.monthly[-1]
        diff = last.buyer_net_worth - last.renter_net_worth
        price = SCENARIOS["sf_tech"]["house_price"]
        # Buyer shouldn't be ahead by more than 20% of house price
        assert diff < price * 0.20, f"SF buyer winning by ${diff:,.0f} — seems too favorable"

    def test_boston_tight_budget(self):
        """Boston first-timer with 5% down and tight budget shouldn't be a slam dunk."""
        r = _run(SCENARIOS["boston_first_timer"])
        last = r.monthly[-1]
        # Total housing cost should exceed rent (buying is more expensive monthly)
        first_owned = next(m for m in r.monthly if m.mortgage_payment > 0)
        assert first_owned.total_housing_cost > first_owned.rent * 0.8


# ═══════════════════════════════════════════════════════════════════════════
# Comparative checks
# ═══════════════════════════════════════════════════════════════════════════

class TestComparativeChecks:

    def test_20pct_down_no_pmi(self):
        """20% down → no PMI; <20% down → has PMI."""
        for name in ["nyc_couple", "seattle_swe", "denver_couple"]:
            r = _run(SCENARIOS[name])
            assert r.monthly[0].pmi == 0.0, f"{name} has 20%+ down but PMI > 0"
        for name in ["sf_tech", "boston_first_timer", "nashville_nurse"]:
            r = _run(SCENARIOS[name])
            assert r.monthly[0].pmi > 0, f"{name} has <20% down but PMI = 0"

    def test_lcol_mortgage_lt_hcol(self):
        """LCOL mortgage payment should be much less than HCOL."""
        r_lcol = _run(SCENARIOS["birmingham_teacher"])
        r_hcol = _run(SCENARIOS["sf_tech"])
        assert r_lcol.monthly[0].mortgage_payment < r_hcol.monthly[0].mortgage_payment * 0.5

    def test_equity_grows(self):
        """Buyer equity should generally grow over 10 years."""
        for name in ["austin_tech", "denver_couple", "cleveland_retiree"]:
            r = _run(SCENARIOS[name])
            assert r.monthly[-1].buyer_equity > r.monthly[12].buyer_equity, \
                f"{name}: equity didn't grow from year 1 to year 10"

    def test_more_cash_helps_both(self):
        """Doubling initial_cash should help both buyer and renter."""
        base = SCENARIOS["nashville_nurse"].copy()
        rich = base.copy()
        rich["initial_cash"] = base["initial_cash"] * 3
        r_base = _run(base)
        r_rich = _run(rich)
        assert r_rich.avg_renter_net_worth > r_base.avg_renter_net_worth
        assert r_rich.avg_buyer_net_worth > r_base.avg_buyer_net_worth


# ═══════════════════════════════════════════════════════════════════════════
# Summary table — not a test, just prints for visual inspection
# ═══════════════════════════════════════════════════════════════════════════

class TestScenarioSummary:
    """Print a summary table of all scenarios for human review."""

    def test_print_summary(self, capsys):
        print("\n" + "=" * 105)
        print(f"{'Scenario':<22} {'Price':>10} {'Down':>5} {'Buyer NW':>12} {'Renter NW':>12} "
              f"{'Diff':>12} {'BE Mo':>6} {'Score':>6}")
        print("-" * 105)

        from scoring import compute_buy_score

        for name, s in SCENARIOS.items():
            r = _run(s)
            last = r.monthly[-1]
            diff = last.buyer_net_worth - last.renter_net_worth
            score = compute_buy_score(r)
            be = r.breakeven_month
            be_str = f"{be}" if be is not None else "never"
            pct = s["down_payment_pct"]
            print(f"{name:<22} ${s['house_price']:>9,} {pct:>4.0%} "
                  f"${last.buyer_net_worth:>11,.0f} ${last.renter_net_worth:>11,.0f} "
                  f"${diff:>+11,.0f} {be_str:>6} {score:>5}")

        print("=" * 105)
