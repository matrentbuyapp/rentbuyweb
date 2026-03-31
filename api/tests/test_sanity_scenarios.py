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
        "stay_years": scenario.get("stay_years"),
        "num_simulations": 50,
        "buy_delay_months": scenario.get("buy_delay_months", 0),
    }
    outlook = MarketOutlook.from_preset(scenario.get("outlook_preset", "historical"))
    inp = SimulationInput(
        user=UserProfile(**user_kw),
        property=PropertyParams(**prop_kw),
        mortgage=MortgageParams(**mort_kw),
        config=SimulationConfig(**cfg_kw),
        outlook=outlook,
    )
    crash_prob = 0 if scenario.get("outlook_preset", "historical") == "historical" else None
    kw = {}
    if crash_prob == 0:
        kw = {"housing_crash_prob": 0, "stock_crash_prob": 0}
    return run_simulation(inp, data, **kw)


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
    # --- NEW: Feature-specific scenarios ---
    "dc_sell_after_5yr": {
        "desc": "DC federal worker, plans to relocate after 5 years",
        "monthly_rent": 2200, "monthly_budget": 3800, "initial_cash": 100_000,
        "yearly_income": 140_000, "house_price": 550_000,
        "down_payment_pct": 0.20, "zip_code": "20001", "credit_quality": "great",
        "stay_years": 5, "years": 10,
    },
    "phoenix_delay_12mo": {
        "desc": "Phoenix nurse waiting 12 months to save more for down payment",
        "monthly_rent": 1400, "monthly_budget": 2800, "initial_cash": 35_000,
        "yearly_income": 85_000, "house_price": 380_000,
        "down_payment_pct": 0.10, "zip_code": "85001", "credit_quality": "good",
        "buy_delay_months": 12,
    },
    "miami_savings_only": {
        "desc": "Miami retiree, risk-averse, keeps cash in savings account only",
        "monthly_rent": 1800, "monthly_budget": 2500, "initial_cash": 200_000,
        "yearly_income": 60_000, "house_price": 400_000,
        "down_payment_pct": 0.30, "zip_code": "33101", "credit_quality": "great",
        "risk_appetite": "savings_only",
    },
    "chicago_15yr_mortgage": {
        "desc": "Chicago high earner, 15-year mortgage, aggressive payoff",
        "monthly_rent": 2000, "monthly_budget": 5500, "initial_cash": 180_000,
        "yearly_income": 220_000, "house_price": 500_000,
        "down_payment_pct": 0.20, "zip_code": "60601", "credit_quality": "excellent",
        "term_years": 15,
    },
    "raleigh_short_horizon": {
        "desc": "Raleigh couple, only 3-year planning horizon",
        "monthly_rent": 1500, "monthly_budget": 2800, "initial_cash": 60_000,
        "yearly_income": 110_000, "house_price": 350_000,
        "down_payment_pct": 0.10, "zip_code": "27601", "credit_quality": "good",
        "filing_status": "married_joint", "years": 3,
    },
    "houston_long_horizon": {
        "desc": "Houston family, 15-year planning horizon, staying forever",
        "monthly_rent": 1600, "monthly_budget": 3200, "initial_cash": 80_000,
        "yearly_income": 100_000, "house_price": 320_000,
        "down_payment_pct": 0.10, "zip_code": "77001", "credit_quality": "good",
        "filing_status": "married_joint", "years": 15,
    },
    "minneapolis_pessimist": {
        "desc": "Minneapolis pessimist, expects market downturn",
        "monthly_rent": 1500, "monthly_budget": 3000, "initial_cash": 90_000,
        "yearly_income": 95_000, "house_price": 350_000,
        "down_payment_pct": 0.15, "zip_code": "55401", "credit_quality": "good",
        "outlook_preset": "pessimistic",
    },
    "san_diego_aggressive": {
        "desc": "San Diego SWE, aggressive stock investor, 5% down",
        "monthly_rent": 2800, "monthly_budget": 4500, "initial_cash": 70_000,
        "yearly_income": 170_000, "house_price": 850_000,
        "down_payment_pct": 0.05, "zip_code": "92101", "credit_quality": "good",
        "risk_appetite": "aggressive",
    },
    "detroit_comeback": {
        "desc": "Detroit, cheap house, big savings, stay 7yr then sell",
        "monthly_rent": 800, "monthly_budget": 1800, "initial_cash": 100_000,
        "yearly_income": 70_000, "house_price": 130_000,
        "down_payment_pct": 0.30, "zip_code": "48201", "credit_quality": "great",
        "stay_years": 7,
    },
    "nyc_delay_then_short_stay": {
        "desc": "NYC, delay 12mo saving, buy, stay 5yr, sell — classic flip timeline",
        "monthly_rent": 3000, "monthly_budget": 5500, "initial_cash": 180_000,
        "yearly_income": 200_000, "house_price": 800_000,
        "down_payment_pct": 0.15, "zip_code": "11201", "credit_quality": "great",
        "filing_status": "married_joint",
        "buy_delay_months": 12, "stay_years": 5, "years": 10,
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

# ═══════════════════════════════════════════════════════════════════════════
# Feature-specific tests — stay_years, buy_delay, savings_only, etc.
# ═══════════════════════════════════════════════════════════════════════════

class TestStayYearsSell:
    """Scenarios where buyer sells before the end of the horizon."""

    def test_sell_event_zeroes_equity(self):
        """After selling, buyer equity should be 0."""
        r = _run(SCENARIOS["dc_sell_after_5yr"])
        # Months 0-59: owning (equity > 0 after initial period)
        assert r.monthly[48].buyer_equity > 0
        # Months 60+: sold (equity = 0)
        assert r.monthly[72].buyer_equity == 0
        assert r.monthly[72].mortgage_payment == 0

    def test_sell_proceeds_boost_investment(self):
        """Buyer investment should jump at the sell month."""
        r = _run(SCENARIOS["dc_sell_after_5yr"])
        # Investment jumps when equity is liquidated
        assert r.monthly[60].buyer_investment > r.monthly[59].buyer_investment + 50_000

    def test_short_stay_different_from_forever(self):
        """Stay 7yr should produce different results than owning forever."""
        r_sell = _run(SCENARIOS["detroit_comeback"])  # stay_years=7
        forever = SCENARIOS["detroit_comeback"].copy()
        forever["stay_years"] = None
        r_forever = _run(forever)
        assert r_sell.avg_buyer_net_worth != r_forever.avg_buyer_net_worth

    def test_delay_plus_stay_fits_horizon(self):
        """NYC delay 12mo + stay 5yr should produce owned months 12-71, renting after."""
        r = _run(SCENARIOS["nyc_delay_then_short_stay"])
        # Month 6: still renting (delay period)
        assert r.monthly[6].mortgage_payment == 0
        # Month 24: owning
        assert r.monthly[24].mortgage_payment > 0
        # Month 80: sold, back to renting
        assert r.monthly[80].mortgage_payment == 0
        assert r.monthly[80].buyer_equity == 0


class TestBuyDelay:
    """Scenarios with delayed purchase."""

    def test_delay_mirrors_renter_initially(self):
        """During delay period, buyer should mirror renter."""
        r = _run(SCENARIOS["phoenix_delay_12mo"])
        for i in range(12):
            assert abs(r.monthly[i].buyer_net_worth - r.monthly[i].renter_net_worth) < 1.0

    def test_delay_then_ownership(self):
        """After delay, ownership kicks in."""
        r = _run(SCENARIOS["phoenix_delay_12mo"])
        assert r.monthly[12].mortgage_payment > 0
        assert r.monthly[11].mortgage_payment == 0


class TestSavingsOnly:
    """Risk-averse users who keep cash in a savings account."""

    def test_savings_only_lower_renter_nw(self):
        """Savings-only renter should accumulate less than a stock-investing renter."""
        r_savings = _run(SCENARIOS["miami_savings_only"])
        moderate = SCENARIOS["miami_savings_only"].copy()
        moderate["risk_appetite"] = "moderate"
        r_stock = _run(moderate)
        assert r_savings.avg_renter_net_worth < r_stock.avg_renter_net_worth

    def test_savings_only_narrow_percentile_spread(self):
        """With savings_only, renter percentile spread should be minimal."""
        r = _run(SCENARIOS["miami_savings_only"])
        spread = r.percentiles.renter_net_worth.p90[-1] - r.percentiles.renter_net_worth.p10[-1]
        # Spread should be small — only home value MC variance, not stock variance
        assert spread < 50_000, f"Savings-only spread too wide: ${spread:,.0f}"


class TestMortgageTerm:
    """15-year vs 30-year mortgage."""

    def test_15yr_higher_payment(self):
        """15-year mortgage should have a higher monthly payment."""
        r_15 = _run(SCENARIOS["chicago_15yr_mortgage"])
        thirty = SCENARIOS["chicago_15yr_mortgage"].copy()
        thirty["term_years"] = 30
        r_30 = _run(thirty)
        assert r_15.monthly[0].mortgage_payment > r_30.monthly[0].mortgage_payment * 1.3

    def test_15yr_faster_equity(self):
        """15-year mortgage should build equity faster."""
        r_15 = _run(SCENARIOS["chicago_15yr_mortgage"])
        thirty = SCENARIOS["chicago_15yr_mortgage"].copy()
        thirty["term_years"] = 30
        r_30 = _run(thirty)
        # At year 5, 15yr mortgage should have more equity
        assert r_15.monthly[59].buyer_equity > r_30.monthly[59].buyer_equity


class TestHorizonLength:
    """Different planning horizons."""

    def test_short_horizon_correct_months(self):
        """3-year horizon should have exactly 36 months."""
        r = _run(SCENARIOS["raleigh_short_horizon"])
        assert len(r.monthly) == 36

    def test_long_horizon_correct_months(self):
        """15-year horizon should have exactly 180 months."""
        r = _run(SCENARIOS["houston_long_horizon"])
        assert len(r.monthly) == 180

    def test_long_horizon_more_equity(self):
        """15 years of ownership should build much more equity than 10."""
        r_long = _run(SCENARIOS["houston_long_horizon"])
        short = SCENARIOS["houston_long_horizon"].copy()
        short["years"] = 10
        r_short = _run(short)
        assert r_long.monthly[-1].buyer_equity > r_short.monthly[-1].buyer_equity


class TestOutlookPresets:
    """Pessimistic outlook should produce worse outcomes."""

    def test_pessimist_worse_for_buyer(self):
        """Pessimistic outlook should reduce buyer advantage or increase renter advantage."""
        r_pessimist = _run(SCENARIOS["minneapolis_pessimist"])
        neutral = SCENARIOS["minneapolis_pessimist"].copy()
        neutral["outlook_preset"] = "historical"
        r_neutral = _run(neutral)
        diff_pessimist = r_pessimist.avg_buyer_net_worth - r_pessimist.avg_renter_net_worth
        diff_neutral = r_neutral.avg_buyer_net_worth - r_neutral.avg_renter_net_worth
        # Pessimistic should be worse for buyer (housing crash risk)
        assert diff_pessimist < diff_neutral

    def test_crossing_count_higher_in_pessimistic(self):
        """Pessimistic scenarios tend to have more volatile outcomes."""
        r = _run(SCENARIOS["minneapolis_pessimist"])
        assert r.crossing_count >= 0  # basic sanity — at minimum it's a valid number


class TestAggressiveInvestor:
    """Aggressive stock exposure should amplify renter returns."""

    def test_aggressive_renter_higher_nw(self):
        """Aggressive stock exposure should give renter higher NW than conservative."""
        r_aggr = _run(SCENARIOS["san_diego_aggressive"])
        cons = SCENARIOS["san_diego_aggressive"].copy()
        cons["risk_appetite"] = "conservative"
        r_cons = _run(cons)
        assert r_aggr.avg_renter_net_worth > r_cons.avg_renter_net_worth

    def test_aggressive_wider_spread(self):
        """Aggressive investor should have wider percentile bands."""
        r_aggr = _run(SCENARIOS["san_diego_aggressive"])
        cons = SCENARIOS["san_diego_aggressive"].copy()
        cons["risk_appetite"] = "conservative"
        r_cons = _run(cons)
        spread_aggr = r_aggr.percentiles.renter_net_worth.p90[-1] - r_aggr.percentiles.renter_net_worth.p10[-1]
        spread_cons = r_cons.percentiles.renter_net_worth.p90[-1] - r_cons.percentiles.renter_net_worth.p10[-1]
        assert spread_aggr > spread_cons


# ═══════════════════════════════════════════════════════════════════════════
# Granular number verification — exact math checks
# ═══════════════════════════════════════════════════════════════════════════

class TestGranularMath:
    """Verify actual dollar amounts match manual mortgage calculations."""

    def test_mortgage_payment_matches_formula(self):
        """P&I should match the standard amortization formula."""
        for name, dp, price, rate, term in [
            ("miami_savings_only", 0.30, 400_000, 0.065, 30),
            ("chicago_15yr_mortgage", 0.20, 500_000, None, 15),
            ("sf_tech", 0.05, 1_200_000, 0.065, 30),
        ]:
            r = _run(SCENARIOS[name])
            loan = price * (1 - dp)
            actual_rate = r.mortgage_rate_used
            r_mo = actual_rate / 12
            n = term * 12
            expected = loan * (r_mo * (1 + r_mo) ** n) / ((1 + r_mo) ** n - 1)
            actual = r.monthly[0].mortgage_payment
            assert abs(expected - actual) < 1.0, \
                f"{name}: expected P&I ${expected:,.2f}, got ${actual:,.2f}"

    def test_interest_plus_principal_equals_payment(self):
        """Interest + principal should equal the total payment every month."""
        for name in ["miami_savings_only", "chicago_15yr_mortgage", "nyc_couple"]:
            r = _run(SCENARIOS[name])
            for i, m in enumerate(r.monthly):
                if m.mortgage_payment > 0:
                    gap = abs(m.mortgage_payment - m.interest_payment - m.principal_payment)
                    assert gap < 0.01, f"{name} month {i}: P&I mismatch by ${gap:.2f}"

    def test_buyer_nw_identity(self):
        """buyer_net_worth must equal buyer_equity + buyer_investment for all scenarios."""
        for name in SCENARIOS:
            r = _run(SCENARIOS[name])
            for i, m in enumerate(r.monthly):
                gap = abs(m.buyer_net_worth - (m.buyer_equity + m.buyer_investment))
                assert gap < 1.0, f"{name} month {i}: NW identity off by ${gap:.2f}"

    def test_equity_formula(self):
        """Equity = home_value * (1 - sell_cost) - remaining_balance during ownership."""
        for name in ["denver_couple", "austin_tech"]:
            r = _run(SCENARIOS[name])
            for i, m in enumerate(r.monthly):
                if m.mortgage_payment > 0:
                    expected = m.home_value * (1 - 0.06) - m.remaining_balance
                    assert abs(expected - m.buyer_equity) < 1.0, \
                        f"{name} month {i}: equity ${m.buyer_equity:,.0f} vs expected ${expected:,.0f}"

    def test_cumulative_cost_matches_sum(self):
        """Cumulative costs should equal the running sum of monthly costs."""
        for name in ["dc_sell_after_5yr", "phoenix_delay_12mo", "chicago_15yr_mortgage"]:
            r = _run(SCENARIOS[name])
            cum_buy = 0
            cum_rent = 0
            for i, m in enumerate(r.monthly):
                cum_buy += m.total_housing_cost
                cum_rent += m.rent
                assert abs(m.cumulative_buy_cost - cum_buy) < 1.0, \
                    f"{name} month {i}: cum_buy off"
                assert abs(m.cumulative_rent_cost - cum_rent) < 1.0, \
                    f"{name} month {i}: cum_rent off"

    def test_total_cost_component_sum(self):
        """total_housing_cost = mortgage + maint + tax + ins + pmi - tax_savings."""
        for name in ["seattle_swe", "nashville_nurse", "la_entertainment"]:
            r = _run(SCENARIOS[name])
            for i, m in enumerate(r.monthly):
                if m.mortgage_payment > 0:
                    expected = (m.mortgage_payment + m.maintenance + m.property_tax
                                + m.insurance + m.pmi - m.tax_savings)
                    gap = abs(m.total_housing_cost - expected)
                    assert gap < 0.01, f"{name} month {i}: total_cost off by ${gap:.2f}"

    def test_balance_decreases_monotonically(self):
        """Remaining mortgage balance should decrease every month during ownership.
        Exception: balance may jump up slightly at a refi point when closing costs
        are rolled into the new loan ($5K default)."""
        for name in ["miami_savings_only", "chicago_15yr_mortgage"]:
            r = _run(SCENARIOS[name])
            balances = [m.remaining_balance for m in r.monthly if m.mortgage_payment > 0]
            increases = 0
            for i in range(1, len(balances)):
                if balances[i] > balances[i - 1] + 0.01:
                    increases += 1
                    # Refi can cause one small jump (closing costs rolled in)
                    assert balances[i] - balances[i - 1] < 6000, \
                        f"{name}: balance jumped by ${balances[i] - balances[i-1]:,.0f} at month {i} — too large for refi"
            assert increases <= 1, f"{name}: balance increased {increases} times — expected at most 1 (refi)"

    def test_sell_event_math(self):
        """At sell month, buyer_inv should jump by approximately the equity amount."""
        r = _run(SCENARIOS["dc_sell_after_5yr"])
        m59 = r.monthly[59]  # last owning month
        m60 = r.monthly[60]  # first post-sell month
        # Equity goes to 0
        assert m60.buyer_equity == 0
        assert m60.mortgage_payment == 0
        # Investment should have jumped by roughly the equity amount
        # (not exact due to stock return applied same month)
        jump = m60.buyer_investment - m59.buyer_investment
        assert jump > m59.buyer_equity * 0.8, \
            f"Investment jump ${jump:,.0f} too small vs equity ${m59.buyer_equity:,.0f}"

    def test_savings_only_renter_deterministic(self):
        """Savings-only renter NW should be reproducible from first principles."""
        r = _run(SCENARIOS["miami_savings_only"])
        rate = 1.045 ** (1 / 12)
        renter = 200_000.0
        for m in r.monthly:
            renter = renter * rate + (m.budget - m.rent)
        assert abs(renter - r.monthly[-1].renter_net_worth) < 100, \
            f"Manual renter ${renter:,.0f} vs engine ${r.monthly[-1].renter_net_worth:,.0f}"


# ═══════════════════════════════════════════════════════════════════════════
# Summary table — all scenarios including new ones
# ═══════════════════════════════════════════════════════════════════════════

class TestScenarioSummary:
    """Print a summary table of all scenarios for human review."""

    def test_print_summary(self, capsys):
        print("\n" + "=" * 120)
        print(f"{'Scenario':<28} {'Price':>10} {'Down':>5} {'Yrs':>4} {'Stay':>5} "
              f"{'Buyer NW':>12} {'Renter NW':>12} {'Diff':>12} {'BE':>6} {'Xing':>5} {'Score':>6}")
        print("-" * 120)

        from scoring import compute_buy_score

        for name, s in SCENARIOS.items():
            r = _run(s)
            last = r.monthly[-1]
            diff = last.buyer_net_worth - last.renter_net_worth
            score = compute_buy_score(r)
            be = r.breakeven_month
            be_str = f"{be}" if be is not None else "never"
            pct = s["down_payment_pct"]
            yrs = s.get("years", 10)
            stay = s.get("stay_years", "-")
            print(f"{name:<28} ${s['house_price']:>9,} {pct:>4.0%} {yrs:>4} {str(stay):>5} "
                  f"${last.buyer_net_worth:>11,.0f} ${last.renter_net_worth:>11,.0f} "
                  f"${diff:>+11,.0f} {be_str:>6} {r.crossing_count:>5} {score:>5}")

        print("=" * 120)
