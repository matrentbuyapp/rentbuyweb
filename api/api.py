"""FastAPI application — thin layer over the simulator."""

import json
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator
from typing import Optional

from models import SimulationInput, UserProfile, PropertyParams, MortgageParams, SimulationConfig, MarketOutlook
from market import get_data
from simulator import run_simulation, estimate_house_price, MonthlySnapshot
from scoring import compute_buy_score, compute_verdict
from sensitivity import run_sensitivity, run_whatif_scenarios, SensitivityPoint, AVAILABLE_AXES
from trend import run_trend, run_zip_comparison, TrendPoint, ZipScore
from llm_summary import generate_summary
from scenarios import router as scenarios_router
from notifications import router as notifications_router
from data_store import init_db, get_median_home_price, get_national_median_home_price
from validation import validate_inputs, ValidationIssue
from market import get_property_tax_rate
from starlette.staticfiles import StaticFiles
from result_cache import (
    get_data_vintage, compute_cache_key, canonical_inputs,
    get_cache_entry, create_cache_entry, update_cache_column,
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

app = FastAPI(title="Rent vs Buy API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static data files (zip_prices.json, etc.)
if os.path.isdir(DATA_DIR):
    app.mount("/data", StaticFiles(directory=DATA_DIR), name="static-data")

# Mount PRO feature routers
app.include_router(scenarios_router)
app.include_router(notifications_router)


@app.on_event("startup")
def startup():
    init_db()

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
    years: int = Field(default=10, ge=2, le=15)       # planning horizon
    stay_years: Optional[int] = None                    # how long to own (None = same as years)
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
    housing_recovery_pct: Optional[float] = None     # 0=permanent crash, 1=full V-shape. Default: 0.5
    housing_recovery_months: Optional[int] = None     # months to recover. Default: 60
    stock_recovery_pct: Optional[float] = None        # Default: 0.7
    stock_recovery_months: Optional[int] = None       # Default: 36

    # Pro tier: rate forecast overrides
    rate_target: Optional[float] = None           # target rate as decimal (0.055 = 5.5%)
    rate_volatility_scale: Optional[float] = None  # scale rate noise (1.0 = historical)

    @model_validator(mode="after")
    def _validate_timeline(self):
        horizon_months = self.years * 12
        stay = self.stay_years
        delay = self.buy_delay_months
        if stay is not None:
            if stay < 1:
                raise ValueError("stay_years must be at least 1")
            if stay > 15:
                raise ValueError("stay_years cannot exceed 15")
            if delay + stay * 12 > horizon_months:
                raise ValueError(
                    f"buy_delay_months ({delay}) + stay_years ({stay}) "
                    f"exceeds planning horizon ({self.years} years). "
                    f"The full buy-own-sell cycle must fit within the horizon."
                )
        return self


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


class PercentileBandsData(BaseModel):
    p10: list[float]
    p25: list[float]
    p50: list[float]
    p75: list[float]
    p90: list[float]


class PercentilesData(BaseModel):
    buyer_net_worth: PercentileBandsData
    renter_net_worth: PercentileBandsData
    home_value: PercentileBandsData
    buyer_equity: PercentileBandsData
    mortgage_rate: PercentileBandsData   # forecasted rate path (in percent, e.g. 6.5 = 6.5%)


class InputWarning(BaseModel):
    code: str         # machine-readable key for frontend logic / i18n
    severity: str     # "warning" (run anyway) or "error" (should not have run)
    message: str      # human-readable explanation


class SummaryResponse(BaseModel):
    cache_key: str            # SHA-256 hash of canonical inputs + data_vintage
    data_vintage: str         # ISO date of underlying market data (e.g. "2026-03-29")
    house_price: float
    mortgage_rate: float
    property_tax_rate: float
    avg_buyer_net_worth: float
    avg_renter_net_worth: float
    buy_score: int            # 0-100, deterministic
    verdict: str              # deterministic text from score
    breakeven_month: int | None  # sustained: when buyer durably pulls ahead (or None)
    crossing_count: int          # how many times buyer/renter lead swaps (0 = clear winner)
    warnings: list[InputWarning]  # validation warnings (empty if inputs are clean)
    monthly: list[MonthlyData]
    percentiles: PercentilesData


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
    if req.housing_recovery_pct is not None:
        outlook.housing_recovery_pct = req.housing_recovery_pct
    if req.housing_recovery_months is not None:
        outlook.housing_recovery_months = req.housing_recovery_months
    if req.stock_recovery_pct is not None:
        outlook.stock_recovery_pct = req.stock_recovery_pct
    if req.stock_recovery_months is not None:
        outlook.stock_recovery_months = req.stock_recovery_months
    if req.rate_target is not None:
        outlook.rate_target = req.rate_target
    if req.rate_volatility_scale is not None:
        outlook.rate_volatility_scale = req.rate_volatility_scale

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
            stay_years=req.stay_years,
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

def _resolve_and_validate(req: SummaryRequest) -> tuple[list[InputWarning], float, float, float]:
    """Resolve house price + mortgage rate, run validation. Returns (warnings, price, rate, tax_rate).

    Raises HTTPException(422) if any errors are found (purchase is impossible).
    """
    from mortgage import credit_rate_adjustment

    # Resolve mortgage rate
    data = get_data()
    if req.mortgage_rate is not None:
        base_rate = req.mortgage_rate
    else:
        base_rate = data.mortgage_rates[-1] / 100
    rate_adj = credit_rate_adjustment(req.credit_quality, req.down_payment_pct)
    mortgage_rate = base_rate + rate_adj / 100

    # Resolve house price
    if req.house_price and req.house_price > 0:
        house_price = req.house_price
    else:
        median = get_median_home_price(req.zip_code) if req.zip_code else None
        house_price = median or get_national_median_home_price()

    # Resolve property tax rate
    prop_tax_rate = get_property_tax_rate(req.zip_code)

    issues = validate_inputs(
        monthly_rent=req.monthly_rent,
        monthly_budget=req.monthly_budget,
        initial_cash=req.initial_cash,
        yearly_income=req.yearly_income,
        house_price=house_price,
        down_payment_pct=req.down_payment_pct,
        closing_cost_pct=req.closing_cost_pct,
        move_in_cost=req.move_in_cost,
        mortgage_rate=mortgage_rate,
        term_years=req.term_years,
        maintenance_rate=req.maintenance_rate,
        insurance_annual=req.insurance_annual,
        property_tax_rate=prop_tax_rate,
    )

    errors = [i for i in issues if i.severity == "error"]
    if errors:
        raise HTTPException(
            status_code=422,
            detail=[{"code": e.code, "message": e.message} for e in errors],
        )

    warnings = [InputWarning(code=i.code, severity=i.severity, message=i.message)
                for i in issues if i.severity == "warning"]
    return warnings, house_price, mortgage_rate, prop_tax_rate


def _build_summary_response(
    result, score: int, warnings: list[InputWarning],
    cache_key: str, data_vintage: str,
) -> dict:
    """Build the SummaryResponse dict from simulation result."""
    pct = result.percentiles
    return {
        "cache_key": cache_key,
        "data_vintage": data_vintage,
        "house_price": result.house_price_used,
        "mortgage_rate": result.mortgage_rate_used,
        "property_tax_rate": result.property_tax_rate,
        "avg_buyer_net_worth": result.avg_buyer_net_worth,
        "avg_renter_net_worth": result.avg_renter_net_worth,
        "buy_score": score,
        "verdict": compute_verdict(score),
        "breakeven_month": result.breakeven_month,
        "crossing_count": result.crossing_count,
        "warnings": [{"code": w.code, "severity": w.severity, "message": w.message} for w in warnings],
        "monthly": [_snapshot_to_dict(s) for s in result.monthly],
        "percentiles": {
            "buyer_net_worth": vars(pct.buyer_net_worth),
            "renter_net_worth": vars(pct.renter_net_worth),
            "home_value": vars(pct.home_value),
            "buyer_equity": vars(pct.buyer_equity),
            "mortgage_rate": vars(pct.mortgage_rate),
        },
    }


@app.post("/summary", response_model=SummaryResponse)
def summary(req: SummaryRequest):
    warnings, _, _, _ = _resolve_and_validate(req)

    # Cache lookup
    vintage = get_data_vintage()
    req_dict = req.model_dump()
    cache_key = compute_cache_key(req_dict, vintage)

    entry = get_cache_entry(cache_key)
    if entry and entry.summary_json:
        # Cache hit — return stored result with fresh warnings
        cached = json.loads(entry.summary_json)
        cached["warnings"] = [{"code": w.code, "severity": w.severity, "message": w.message} for w in warnings]
        cached["cache_key"] = cache_key
        cached["data_vintage"] = vintage
        return cached

    # Cache miss — run simulation
    data = get_data()
    inputs = _request_to_input(req)
    result = run_simulation(inputs, data)
    score = compute_buy_score(result)

    response = _build_summary_response(result, score, warnings, cache_key, vintage)

    # Store in cache
    inputs_json = canonical_inputs(req_dict)
    create_cache_entry(cache_key, vintage, inputs_json)
    update_cache_column(cache_key, "summary_json", json.dumps(response))

    return response


# ═══════════════════════════════════════════════════════════════════════════
# POST /summary/csv — export simulation results as CSV (pro tier)
# ═══════════════════════════════════════════════════════════════════════════

from fastapi.responses import StreamingResponse
import csv
import io


@app.post("/summary/csv")
def summary_csv(req: SummaryRequest):
    """Run the simulation and return month-by-month results as a downloadable CSV."""
    warnings, _, _, _ = _resolve_and_validate(req)

    data = get_data()
    inputs = _request_to_input(req)
    result = run_simulation(inputs, data)
    score = compute_buy_score(result)

    buf = io.StringIO()
    writer = csv.writer(buf)

    # Header metadata
    writer.writerow(["# Rent vs Buy Simulation Export"])
    writer.writerow(["# House Price", f"${result.house_price_used:,.0f}"])
    writer.writerow(["# Mortgage Rate", f"{result.mortgage_rate_used:.2%}"])
    writer.writerow(["# Property Tax Rate", f"{result.property_tax_rate:.2%}"])
    writer.writerow(["# Buy Score", score])
    writer.writerow(["# Verdict", compute_verdict(score)])
    writer.writerow(["# Breakeven Month", result.breakeven_month or "Never"])
    for w in warnings:
        writer.writerow(["# Warning", w.message])
    writer.writerow([])

    # Column headers
    fields = list(MonthlySnapshot.__dataclass_fields__.keys())
    writer.writerow(["month", "year"] + fields)

    # Data rows
    for i, snap in enumerate(result.monthly):
        row = [i + 1, f"{i // 12 + 1}.{i % 12 + 1:02d}"]
        for f in fields:
            val = getattr(snap, f)
            row.append(round(val, 2))
        writer.writerow(row)

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=rent_vs_buy_simulation.csv"},
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


class SensitivityRequest(SummaryRequest):
    # Which 1D axes to sweep. Default: rate, price, down payment, outlook.
    # Available: mortgage_rate, house_price, down_payment_pct, outlook,
    #            stay_years, yearly_income, initial_cash, risk_appetite
    axes: list[str] | None = None
    heatmap_x: str | None = None   # X axis for 2D heatmap. Default: house_price
    heatmap_y: str | None = None   # Y axis for 2D heatmap. Default: mortgage_rate


@app.post("/sensitivity", response_model=SensitivityResponse)
def sensitivity(req: SensitivityRequest):
    # Cache check (includes axes/heatmap params in key)
    vintage = get_data_vintage()
    cache_key = compute_cache_key(req.model_dump(), vintage)
    entry = get_cache_entry(cache_key)
    if entry and entry.sensitivity_json:
        return json.loads(entry.sensitivity_json)

    data = get_data()
    inputs = _request_to_input(req)
    result = run_sensitivity(
        inputs, data,
        axes_to_run=req.axes,
        heatmap_x=req.heatmap_x,
        heatmap_y=req.heatmap_y,
    )

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

    response = SensitivityResponse(
        base_buyer_nw=result.base_buyer_nw,
        base_renter_nw=result.base_renter_nw,
        base_net_diff=result.base_net_diff,
        base_buy_score=result.base_buy_score,
        axes=axes_out,
        heatmap=heatmap_out,
    )

    # Store in cache
    if not entry:
        create_cache_entry(cache_key, vintage, canonical_inputs(req.model_dump()))
    update_cache_column(cache_key, "sensitivity_json", response.model_dump_json())
    return response


# ═══════════════════════════════════════════════════════════════════════════
# POST /whatif — named what-if scenarios (pro tier)
# ═══════════════════════════════════════════════════════════════════════════

class WhatIfRequest(SummaryRequest):
    scenario_ids: list[str] | None = None  # subset to run. None = all applicable


class WhatIfScenarioOut(BaseModel):
    id: str
    name: str
    description: str
    buyer_net_worth: float
    renter_net_worth: float
    net_difference: float
    delta_from_base: float  # change vs base scenario (positive = better for buying)
    breakeven_month: int | None
    buy_score: int


class WhatIfResponse(BaseModel):
    base_net_diff: float
    scenarios: list[WhatIfScenarioOut]


@app.post("/whatif", response_model=WhatIfResponse)
def whatif(req: WhatIfRequest):
    data = get_data()
    inputs = _request_to_input(req)
    base_diff, scenarios = run_whatif_scenarios(inputs, data, scenario_ids=req.scenario_ids)

    return WhatIfResponse(
        base_net_diff=base_diff,
        scenarios=[
            WhatIfScenarioOut(
                id=s.id, name=s.name, description=s.description,
                buyer_net_worth=s.buyer_net_worth, renter_net_worth=s.renter_net_worth,
                net_difference=s.net_difference, delta_from_base=s.delta_from_base,
                breakeven_month=s.breakeven_month, buy_score=s.buy_score,
            )
            for s in scenarios
        ],
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
    # Cache check (trend includes max_delay_quarters in key via model_dump)
    vintage = get_data_vintage()
    cache_key = compute_cache_key(req.model_dump(), vintage)
    entry = get_cache_entry(cache_key)
    if entry and entry.trend_json:
        return json.loads(entry.trend_json)

    data = get_data()
    inputs = _request_to_input(req)
    result = run_trend(inputs, data, max_delay_quarters=req.max_delay_quarters)

    response = TrendResponse(
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

    if not entry:
        create_cache_entry(cache_key, vintage, canonical_inputs(req.model_dump()))
    update_cache_column(cache_key, "trend_json", response.model_dump_json())
    return response


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

    # Cache check (zip_compare includes zip_codes in key)
    vintage = get_data_vintage()
    cache_key = compute_cache_key(req.model_dump(), vintage)
    entry = get_cache_entry(cache_key)
    if entry and entry.zip_compare_json:
        return json.loads(entry.zip_compare_json)

    data = get_data()
    inputs = _request_to_input(req)
    result = run_zip_comparison(inputs, data, zip_codes)

    response = ZipCompareResponse(
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

    if not entry:
        create_cache_entry(cache_key, vintage, canonical_inputs(req.model_dump()))
    update_cache_column(cache_key, "zip_compare_json", response.model_dump_json())
    return response


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
    # Cache check — LLM output is expensive, always cache
    vintage = get_data_vintage()
    cache_key = compute_cache_key(req.model_dump(), vintage)
    entry = get_cache_entry(cache_key)
    if entry and entry.llm_summary_json:
        return json.loads(entry.llm_summary_json)

    # Use cached summary result if available, otherwise run fresh
    data = get_data()
    inputs = _request_to_input(req)
    result = run_simulation(inputs, data)
    llm_result = await generate_summary(result, sell_cost_pct=req.sell_cost_pct)

    response = LLMSummaryResponse(
        summary=llm_result.summary,
        buy_costs_summary=llm_result.buy_costs_summary,
        buy_pros=llm_result.buy_pros,
        rent_pros=llm_result.rent_pros,
        buy_costs=llm_result.buy_costs,
        rent_costs=llm_result.rent_costs,
        verdict=llm_result.verdict,
        score=llm_result.score,
    )

    if not entry:
        create_cache_entry(cache_key, vintage, canonical_inputs(req.model_dump()))
    update_cache_column(cache_key, "llm_summary_json", response.model_dump_json())
    return response


# ═══════════════════════════════════════════════════════════════════════════
# GET /health
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/health")
def health():
    return {"status": "ok"}
