"""FastAPI application — thin layer over the simulator."""

import json
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from models import SimulationInput, UserProfile, PropertyParams, MortgageParams, SimulationConfig, MarketOutlook
from market import get_data
from simulator import run_simulation, estimate_house_price, MonthlySnapshot
from scoring import compute_buy_score, compute_verdict
from sensitivity import run_sensitivity, SensitivityPoint
from trend import run_trend, run_zip_comparison, TrendPoint, ZipScore
from llm_summary import generate_summary

app = FastAPI(title="Rent vs Buy API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Zip neighbors (loaded once) ---
_ZIP_NEIGHBORS: dict[str, list[str]] = {}
_neighbors_path = os.path.join(os.path.dirname(__file__), "..", "rent-buy-api", "zip_neighbors.json")
if os.path.exists(_neighbors_path):
    with open(_neighbors_path) as f:
        _ZIP_NEIGHBORS = json.load(f)


# ═══════════════════════════════════════════════════════════════════════════
# Shared request/response models
# ═══════════════════════════════════════════════════════════════════════════

class SummaryRequest(BaseModel):
    # User
    monthly_rent: float
    monthly_budget: float
    initial_cash: float = 150_000
    yearly_income: float = 0
    filing_status: str = "single"
    other_deductions: float = 0
    risk_appetite: str = "moderate"

    # Property
    zip_code: Optional[str] = None
    house_price: Optional[float] = None
    down_payment_pct: float = 0.10
    closing_cost_pct: float = 0.03
    maintenance_rate: float = 0.01
    insurance_annual: float = 0
    sell_cost_pct: float = 0.06
    move_in_cost: float = 0

    # Mortgage
    mortgage_rate: Optional[float] = None
    term_years: int = 30
    credit_quality: str = "good"

    # Simulation
    years: int = 10
    num_simulations: int = 500
    buy_delay_months: int = 0

    # Market outlook — free tier: preset name, pro tier: individual controls
    outlook_preset: str = "historical"  # "optimistic" | "historical" | "cautious" | "pessimistic" | "crisis"

    # Pro tier: override individual outlook params (ignored if None)
    volatility_scale: Optional[float] = None
    housing_crash_prob: Optional[float] = None
    housing_crash_drop: Optional[float] = None
    housing_drawdown_months: Optional[int] = None
    stock_crash_prob: Optional[float] = None
    stock_crash_drop: Optional[float] = None
    stock_drawdown_months: Optional[int] = None


class MonthlyData(BaseModel):
    home_value: float
    mortgage_payment: float
    interest_payment: float
    principal_payment: float
    remaining_balance: float
    maintenance: float
    property_tax: float
    insurance: float
    pmi: float
    tax_savings: float
    total_housing_cost: float
    rent: float
    budget: float
    buyer_investment: float
    renter_investment: float
    buyer_equity: float
    buyer_net_worth: float
    renter_net_worth: float
    cumulative_buy_cost: float
    cumulative_rent_cost: float


class SummaryResponse(BaseModel):
    house_price: float
    mortgage_rate: float
    property_tax_rate: float
    avg_buyer_net_worth: float
    avg_renter_net_worth: float
    buy_score: int            # 0-100, deterministic
    verdict: str              # deterministic text from score
    monthly: list[MonthlyData]


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _build_outlook(req: SummaryRequest) -> MarketOutlook:
    """Build MarketOutlook from request — preset with optional pro overrides."""
    outlook = MarketOutlook.from_preset(req.outlook_preset)

    # Pro tier overrides (any non-None value replaces the preset)
    if req.volatility_scale is not None:
        outlook.volatility_scale = req.volatility_scale
    if req.housing_crash_prob is not None:
        outlook.housing_crash_prob = req.housing_crash_prob
    if req.housing_crash_drop is not None:
        outlook.housing_crash_drop = req.housing_crash_drop
    if req.housing_drawdown_months is not None:
        outlook.housing_drawdown_months = req.housing_drawdown_months
    if req.stock_crash_prob is not None:
        outlook.stock_crash_prob = req.stock_crash_prob
    if req.stock_crash_drop is not None:
        outlook.stock_crash_drop = req.stock_crash_drop
    if req.stock_drawdown_months is not None:
        outlook.stock_drawdown_months = req.stock_drawdown_months

    return outlook


def _request_to_input(req: SummaryRequest) -> SimulationInput:
    return SimulationInput(
        user=UserProfile(
            monthly_rent=req.monthly_rent,
            monthly_budget=req.monthly_budget,
            initial_cash=req.initial_cash,
            yearly_income=req.yearly_income,
            filing_status=req.filing_status,
            other_deductions=req.other_deductions,
            risk_appetite=req.risk_appetite,
        ),
        property=PropertyParams(
            zip_code=req.zip_code,
            house_price=req.house_price,
            down_payment_pct=req.down_payment_pct,
            closing_cost_pct=req.closing_cost_pct,
            maintenance_rate=req.maintenance_rate,
            insurance_annual=req.insurance_annual,
            sell_cost_pct=req.sell_cost_pct,
            move_in_cost=req.move_in_cost,
        ),
        mortgage=MortgageParams(
            rate=req.mortgage_rate,
            term_years=req.term_years,
            credit_quality=req.credit_quality,
        ),
        config=SimulationConfig(
            years=req.years,
            num_simulations=req.num_simulations,
            buy_delay_months=req.buy_delay_months,
        ),
        outlook=_build_outlook(req),
    )


def _snapshot_to_dict(s: MonthlySnapshot) -> dict:
    return {f: getattr(s, f) for f in s.__dataclass_fields__}


# ═══════════════════════════════════════════════════════════════════════════
# POST /summary — core simulation (free tier)
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/summary", response_model=SummaryResponse)
def summary(req: SummaryRequest):
    data = get_data()
    inputs = _request_to_input(req)
    result = run_simulation(inputs, data)

    score = compute_buy_score(result)

    return SummaryResponse(
        house_price=result.house_price_used,
        mortgage_rate=result.mortgage_rate_used,
        property_tax_rate=result.property_tax_rate,
        avg_buyer_net_worth=result.avg_buyer_net_worth,
        avg_renter_net_worth=result.avg_renter_net_worth,
        buy_score=score,
        verdict=compute_verdict(score),
        monthly=[MonthlyData(**_snapshot_to_dict(s)) for s in result.monthly],
    )


# ═══════════════════════════════════════════════════════════════════════════
# POST /sensitivity — "what if" analysis (pro tier)
# ═══════════════════════════════════════════════════════════════════════════

class SensitivityPointOut(BaseModel):
    label: str
    param_name: str
    param_value: float
    buyer_net_worth: float
    renter_net_worth: float
    net_difference: float
    breakeven_month: int | None


class HeatmapCellOut(BaseModel):
    x_label: str
    y_label: str
    x_value: float
    y_value: float
    net_difference: float
    breakeven_month: int | None
    buy_score: int


class HeatmapOut(BaseModel):
    x_axis: str
    y_axis: str
    x_labels: list[str]
    y_labels: list[str]
    cells: list[list[HeatmapCellOut]]


class SensitivityResponse(BaseModel):
    base_buyer_nw: float
    base_renter_nw: float
    base_net_diff: float
    base_buy_score: int
    axes: dict[str, list[SensitivityPointOut]]
    heatmap: HeatmapOut


@app.post("/sensitivity", response_model=SensitivityResponse)
def sensitivity(req: SummaryRequest):
    data = get_data()
    inputs = _request_to_input(req)
    result = run_sensitivity(inputs, data)

    axes_out = {}
    for name, points in result.axes.items():
        axes_out[name] = [
            SensitivityPointOut(
                label=p.label, param_name=p.param_name, param_value=p.param_value,
                buyer_net_worth=p.buyer_net_worth, renter_net_worth=p.renter_net_worth,
                net_difference=p.net_difference, breakeven_month=p.breakeven_month,
            )
            for p in points
        ]

    hm = result.heatmap
    heatmap_out = HeatmapOut(
        x_axis=hm.x_axis,
        y_axis=hm.y_axis,
        x_labels=hm.x_labels,
        y_labels=hm.y_labels,
        cells=[
            [HeatmapCellOut(
                x_label=c.x_label, y_label=c.y_label,
                x_value=c.x_value, y_value=c.y_value,
                net_difference=c.net_difference,
                breakeven_month=c.breakeven_month,
                buy_score=c.buy_score,
            ) for c in row]
            for row in hm.cells
        ],
    )

    return SensitivityResponse(
        base_buyer_nw=result.base_buyer_nw,
        base_renter_nw=result.base_renter_nw,
        base_net_diff=result.base_net_diff,
        base_buy_score=result.base_buy_score,
        axes=axes_out,
        heatmap=heatmap_out,
    )


# ═══════════════════════════════════════════════════════════════════════════
# POST /trend — timing analysis (pro tier)
# ═══════════════════════════════════════════════════════════════════════════

class TrendRequest(SummaryRequest):
    max_delay_quarters: int = 8


class TrendPointOut(BaseModel):
    delay_months: int
    label: str
    buyer_net_worth: float
    renter_net_worth: float
    net_difference: float
    breakeven_month: int | None
    yearly_scores: list[float]
    aggregate_score: float
    mortgage_rate_used: float
    house_price_used: float
    first_month_cost: float


class TrendResponse(BaseModel):
    points: list[TrendPointOut]


@app.post("/trend", response_model=TrendResponse)
def trend(req: TrendRequest):
    data = get_data()
    inputs = _request_to_input(req)
    result = run_trend(inputs, data, max_delay_quarters=req.max_delay_quarters)

    return TrendResponse(
        points=[
            TrendPointOut(
                delay_months=p.delay_months, label=p.label,
                buyer_net_worth=p.buyer_net_worth, renter_net_worth=p.renter_net_worth,
                net_difference=p.net_difference, breakeven_month=p.breakeven_month,
                yearly_scores=p.yearly_scores, aggregate_score=p.aggregate_score,
                mortgage_rate_used=p.mortgage_rate_used, house_price_used=p.house_price_used,
                first_month_cost=p.first_month_cost,
            )
            for p in result.points
        ],
    )


# ═══════════════════════════════════════════════════════════════════════════
# POST /zip-compare — neighborhood comparison (pro tier)
# ═══════════════════════════════════════════════════════════════════════════

class ZipCompareRequest(SummaryRequest):
    zip_codes: list[str] = []  # if empty, uses neighbors of zip_code


class ZipScoreOut(BaseModel):
    zip_code: str
    city: str | None
    state: str | None
    house_price: float
    buyer_net_worth: float
    renter_net_worth: float
    net_difference: float
    aggregate_score: float
    breakeven_month: int | None


class ZipCompareResponse(BaseModel):
    scores: list[ZipScoreOut]


@app.post("/zip-compare", response_model=ZipCompareResponse)
def zip_compare(req: ZipCompareRequest):
    zip_codes = req.zip_codes

    # If no explicit list, use neighbors of the primary ZIP
    if not zip_codes and req.zip_code:
        neighbors = _ZIP_NEIGHBORS.get(req.zip_code, [])
        zip_codes = [req.zip_code] + neighbors[:15]  # cap at 16 total

    if not zip_codes:
        raise HTTPException(400, "Provide zip_codes or zip_code for neighbor lookup")

    data = get_data()
    inputs = _request_to_input(req)
    result = run_zip_comparison(inputs, data, zip_codes)

    return ZipCompareResponse(
        scores=[
            ZipScoreOut(
                zip_code=s.zip_code, city=s.city, state=s.state,
                house_price=s.house_price,
                buyer_net_worth=s.buyer_net_worth, renter_net_worth=s.renter_net_worth,
                net_difference=s.net_difference, aggregate_score=s.aggregate_score,
                breakeven_month=s.breakeven_month,
            )
            for s in result.scores
        ],
    )


# ═══════════════════════════════════════════════════════════════════════════
# GET /zip-neighbors/{zip_code} — neighboring ZIP codes
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/zip-neighbors/{zip_code}")
def zip_neighbors(zip_code: str):
    neighbors = _ZIP_NEIGHBORS.get(zip_code, [])
    return {"zip_code": zip_code, "neighbors": neighbors}


# ═══════════════════════════════════════════════════════════════════════════
# POST /llm-summary — AI narrative (pro tier)
# ═══════════════════════════════════════════════════════════════════════════

class LLMSummaryResponse(BaseModel):
    summary: str
    buy_costs_summary: str
    buy_pros: list[str]
    rent_pros: list[str]
    buy_costs: list[str]
    rent_costs: list[str]
    verdict: str
    score: int


@app.post("/llm-summary", response_model=LLMSummaryResponse)
async def llm_summary(req: SummaryRequest):
    data = get_data()
    inputs = _request_to_input(req)
    result = run_simulation(inputs, data)
    llm_result = await generate_summary(result, sell_cost_pct=req.sell_cost_pct)

    return LLMSummaryResponse(
        summary=llm_result.summary,
        buy_costs_summary=llm_result.buy_costs_summary,
        buy_pros=llm_result.buy_pros,
        rent_pros=llm_result.rent_pros,
        buy_costs=llm_result.buy_costs,
        rent_costs=llm_result.rent_costs,
        verdict=llm_result.verdict,
        score=llm_result.score,
    )


# ═══════════════════════════════════════════════════════════════════════════
# GET /health
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/health")
def health():
    return {"status": "ok"}
