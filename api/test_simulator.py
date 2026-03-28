"""End-to-end smoke test for the simulator using real data files."""

from models import SimulationInput, UserProfile, PropertyParams, MortgageParams, SimulationConfig
from market import load_historical_data
from simulator import run_simulation


def test_full_simulation():
    print("Loading historical data...")
    data = load_historical_data(n_months=180)
    print(f"  CPI: {len(data.cpi_monthly_growth)} months")
    print(f"  Stocks: {len(data.stock_monthly_growth)} months")
    print(f"  HPI: {len(data.hpi_cumulative)} months")
    print(f"  Mortgage rates: {len(data.mortgage_rates)} months")

    inputs = SimulationInput(
        user=UserProfile(
            monthly_rent=3500,
            monthly_budget=5000,
            initial_cash=150_000,
            yearly_income=150_000,
            filing_status="single",
            risk_appetite="moderate",
        ),
        property=PropertyParams(
            house_price=650_000,
            down_payment_pct=0.10,
            maintenance_rate=0.01,
            insurance_annual=2400,
            sell_cost_pct=0.06,
        ),
        mortgage=MortgageParams(
            term_years=30,
            credit_quality="good",
        ),
        config=SimulationConfig(
            years=10,
            num_simulations=100,  # fewer for speed
        ),
    )

    print("\nRunning 100 simulations over 10 years...")
    result = run_simulation(inputs, data)

    print(f"\n--- Results ---")
    print(f"House price: ${result.house_price_used:,.0f}")
    print(f"Mortgage rate: {result.mortgage_rate_used:.3%}")
    print(f"Property tax rate: {result.property_tax_rate:.3%}")

    m0 = result.monthly[0]
    m60 = result.monthly[59]   # year 5
    m119 = result.monthly[119]  # year 10

    print(f"\nMonth 1:")
    print(f"  Rent: ${m0.rent:,.0f}")
    print(f"  Mortgage: ${m0.mortgage_payment:,.0f}")
    print(f"  Total housing cost: ${m0.total_housing_cost:,.0f}")
    print(f"  Buyer NW: ${m0.buyer_net_worth:,.0f}")
    print(f"  Renter NW: ${m0.renter_net_worth:,.0f}")

    print(f"\nYear 5 (month 60):")
    print(f"  Rent: ${m60.rent:,.0f}")
    print(f"  Home value: ${m60.home_value:,.0f}")
    print(f"  Buyer equity: ${m60.buyer_equity:,.0f}")
    print(f"  Buyer NW: ${m60.buyer_net_worth:,.0f}")
    print(f"  Renter NW: ${m60.renter_net_worth:,.0f}")
    print(f"  Difference: ${m60.buyer_net_worth - m60.renter_net_worth:+,.0f}")

    print(f"\nYear 10 (month 120):")
    print(f"  Rent: ${m119.rent:,.0f}")
    print(f"  Home value: ${m119.home_value:,.0f}")
    print(f"  Buyer equity: ${m119.buyer_equity:,.0f}")
    print(f"  Buyer NW: ${m119.buyer_net_worth:,.0f}")
    print(f"  Renter NW: ${m119.renter_net_worth:,.0f}")
    print(f"  Difference: ${m119.buyer_net_worth - m119.renter_net_worth:+,.0f}")

    # Sanity checks
    assert m119.home_value > 0, "Home value should be positive"
    assert m119.buyer_net_worth != m119.renter_net_worth, "MC should produce different outcomes"
    assert m0.mortgage_payment > 0, "Should have mortgage payment"
    assert m60.rent > m0.rent, "Rent should increase over time (inflation)"
    assert m0.renter_net_worth > 0, "Renter should have positive NW (initial cash)"

    print("\nPASSED")


if __name__ == "__main__":
    test_full_simulation()
