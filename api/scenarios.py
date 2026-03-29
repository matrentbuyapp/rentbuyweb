"""Saved scenarios — CRUD endpoints for PRO tier.

Users save simulation inputs, re-run them on demand, and track how results
change over time as market data refreshes.

Device identity: X-Device-Id header (localStorage UUID). No auth flow yet.
"""

import json
import time
import uuid
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from data_store import (
    ensure_device, save_scenario, get_scenarios_for_device,
    get_scenario, delete_scenario, update_scenario_response,
    ScenarioRow,
)

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class CreateScenarioRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    inputs: dict  # full SummaryRequest as dict
    response: Optional[dict] = None  # optional: cache last result


class ScenarioOut(BaseModel):
    id: str
    name: str
    inputs: dict
    response: Optional[dict]
    created_at: float
    updated_at: float


class ScenarioListResponse(BaseModel):
    scenarios: list[ScenarioOut]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_device_id(x_device_id: Optional[str]) -> str:
    if not x_device_id:
        raise HTTPException(401, "X-Device-Id header required")
    return x_device_id


def _row_to_out(row: ScenarioRow) -> ScenarioOut:
    return ScenarioOut(
        id=row.id,
        name=row.name,
        inputs=json.loads(row.inputs_json),
        response=json.loads(row.response_json) if row.response_json else None,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=ScenarioOut, status_code=201)
def create_scenario(
    req: CreateScenarioRequest,
    x_device_id: Optional[str] = Header(None),
):
    """Save a new scenario."""
    device_id = _require_device_id(x_device_id)
    ensure_device(device_id)

    now = time.time()
    scenario = ScenarioRow(
        id=str(uuid.uuid4()),
        device_id=device_id,
        name=req.name,
        inputs_json=json.dumps(req.inputs),
        response_json=json.dumps(req.response) if req.response else None,
        created_at=now,
        updated_at=now,
    )
    save_scenario(scenario)
    return _row_to_out(scenario)


@router.get("", response_model=ScenarioListResponse)
def list_scenarios(
    x_device_id: Optional[str] = Header(None),
):
    """List all scenarios for this device."""
    device_id = _require_device_id(x_device_id)
    ensure_device(device_id)

    rows = get_scenarios_for_device(device_id)
    return ScenarioListResponse(scenarios=[_row_to_out(r) for r in rows])


@router.get("/{scenario_id}", response_model=ScenarioOut)
def get_scenario_detail(
    scenario_id: str,
    x_device_id: Optional[str] = Header(None),
):
    """Get a single scenario."""
    device_id = _require_device_id(x_device_id)
    row = get_scenario(scenario_id)
    if not row or row.device_id != device_id:
        raise HTTPException(404, "Scenario not found")
    return _row_to_out(row)


@router.post("/{scenario_id}/run", response_model=dict)
def run_scenario(
    scenario_id: str,
    x_device_id: Optional[str] = Header(None),
):
    """Re-run a saved scenario with current market data. Returns fresh SummaryResponse."""
    device_id = _require_device_id(x_device_id)
    row = get_scenario(scenario_id)
    if not row or row.device_id != device_id:
        raise HTTPException(404, "Scenario not found")

    # Import here to avoid circular imports
    from api import SummaryRequest, _request_to_input, _snapshot_to_dict
    from market import get_data
    from simulator import run_simulation
    from scoring import compute_buy_score, compute_verdict

    from api import _resolve_and_validate

    inputs_dict = json.loads(row.inputs_json)
    req = SummaryRequest(**inputs_dict)

    warnings, _, _, _ = _resolve_and_validate(req)

    data = get_data()
    sim_input = _request_to_input(req)
    result = run_simulation(sim_input, data)
    score = compute_buy_score(result)

    pct = result.percentiles
    response = {
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

    # Cache result
    update_scenario_response(scenario_id, json.dumps(response))
    return response


@router.delete("/{scenario_id}", status_code=204)
def delete_scenario_endpoint(
    scenario_id: str,
    x_device_id: Optional[str] = Header(None),
):
    """Delete a saved scenario and its alerts."""
    device_id = _require_device_id(x_device_id)
    row = get_scenario(scenario_id)
    if not row or row.device_id != device_id:
        raise HTTPException(404, "Scenario not found")
    delete_scenario(scenario_id)
