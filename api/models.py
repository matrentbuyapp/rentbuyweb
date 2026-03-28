"""Data models for the rent-vs-buy simulator."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UserProfile:
    monthly_rent: float
    monthly_budget: float
    initial_cash: float
    yearly_income: float = 0.0
    filing_status: str = "single"  # single, married_joint, head_of_household
    other_deductions: float = 0.0
    risk_appetite: str = "moderate"  # conservative, moderate, aggressive


@dataclass
class PropertyParams:
    zip_code: Optional[str] = None
    house_price: Optional[float] = None  # None = auto-estimate from rent/budget
    down_payment_pct: float = 0.10
    closing_cost_pct: float = 0.03
    maintenance_rate: float = 0.01  # annual, as fraction of home value
    insurance_annual: float = 0.0
    sell_cost_pct: float = 0.06
    move_in_cost: float = 0.0


@dataclass
class MortgageParams:
    rate: Optional[float] = None  # None = look up from FRED
    term_years: int = 30
    credit_quality: str = "good"  # excellent, great, good, average, mediocre, poor


@dataclass
class SimulationConfig:
    years: int = 10
    num_simulations: int = 500
    buy_delay_months: int = 0


@dataclass
class MarketOutlook:
    """Controls for the crash/stress overlay on top of base MC paths.

    Free tier: use from_preset() which maps a single label to fixed values.
    Pro tier: set each field independently for fine-grained control.
    """
    # Volatility scaling: 1.0 = historical, <1.0 = optimistic, >1.0 = pessimistic
    volatility_scale: float = 1.0

    # Extra crash shock (on top of base volatility)
    housing_crash_prob: float = 0.0
    housing_crash_drop: float = 0.0
    housing_drawdown_months: int = 12
    stock_crash_prob: float = 0.0
    stock_crash_drop: float = 0.0
    stock_drawdown_months: int = 6
    crash_horizon_months: int = 36

    @staticmethod
    def from_preset(name: str) -> "MarketOutlook":
        """Map a slider label to fixed parameters.

        'historical' is the honest default — no modifications to base MC.
        """
        presets = {
            "optimistic": MarketOutlook(
                volatility_scale=0.7,
            ),
            "historical": MarketOutlook(
                volatility_scale=1.0,
            ),
            "cautious": MarketOutlook(
                volatility_scale=1.2,
                housing_crash_prob=0.10, housing_crash_drop=0.10,
                stock_crash_prob=0.10, stock_crash_drop=0.15,
            ),
            "pessimistic": MarketOutlook(
                volatility_scale=1.4,
                housing_crash_prob=0.25, housing_crash_drop=0.20,
                stock_crash_prob=0.25, stock_crash_drop=0.25,
            ),
            "crisis": MarketOutlook(
                volatility_scale=1.6,
                housing_crash_prob=0.50, housing_crash_drop=0.30,
                housing_drawdown_months=18,
                stock_crash_prob=0.50, stock_crash_drop=0.35,
                stock_drawdown_months=9,
            ),
        }
        return presets.get(name, presets["historical"])


@dataclass
class SimulationInput:
    user: UserProfile
    property: PropertyParams
    mortgage: MortgageParams
    config: SimulationConfig = field(default_factory=SimulationConfig)
    outlook: MarketOutlook = field(default_factory=MarketOutlook)
