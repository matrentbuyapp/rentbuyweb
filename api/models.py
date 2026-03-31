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
    risk_appetite: str = "moderate"  # savings_only, conservative, moderate, aggressive


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
    years: int = 10               # total planning horizon
    stay_years: Optional[int] = None  # how long you'd own before selling (None = same as years)
    num_simulations: int = 500
    buy_delay_months: int = 0
    # Refinance — on by default with conservative settings.
    # Free users get silently optimized results. PRO users see details + controls.
    refi_enabled: bool = True
    refi_threshold: float = 1.0   # conservative: need 1.0% drop (not 0.75%)
    refi_closing_cost: float = 5000.0  # conservative: $5K (not $3-4K)
    refi_max_count: int = 1       # conservative: one refi only
    refi_min_months: int = 24     # conservative: wait 2 years before refi eligible
    refi_roll_costs: bool = True  # conservative: roll closing costs into new loan (not out of pocket)


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
    housing_recovery_pct: float = 0.5     # fraction of crash recovered (0=permanent, 1=full V-shape)
    housing_recovery_months: int = 60     # months to reach recovery_pct of the gap (default 5yr)
    stock_crash_prob: float = 0.0
    stock_crash_drop: float = 0.0
    stock_drawdown_months: int = 6
    stock_recovery_pct: float = 0.7       # stocks recover faster than housing
    stock_recovery_months: int = 36       # default 3yr
    crash_horizon_months: int = 36

    # Rate forecast overrides (Pro tier)
    rate_target: Optional[float] = None     # target rate as decimal (0.055 = 5.5%). Replaces 20y avg as mean-reversion anchor
    rate_volatility_scale: float = 1.0      # scale noise on rate path (1.0 = historical, 0.5 = calm, 2.0 = turbulent)

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
                housing_recovery_pct=0.3, housing_recovery_months=84,  # slow recovery in crisis
                stock_crash_prob=0.50, stock_crash_drop=0.35,
                stock_drawdown_months=9,
                stock_recovery_pct=0.5, stock_recovery_months=48,
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
