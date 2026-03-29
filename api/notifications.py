"""Notification engine — diff detection + alert delivery.

Runs after each data refresh to detect meaningful changes in saved scenarios:
- Breakeven shifted by >3 months
- Verdict flipped (e.g. "lean buy" → "lean rent")
- Score changed significantly

Alert types:
- threshold: fires when verdict flips
- shift: fires when breakeven moves by >3 months
- digest: monthly summary of all changes (sent regardless of magnitude)

Email delivery via AWS SES.
"""

import json
import time
import uuid
import logging
from dataclasses import dataclass
from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from data_store import (
    ensure_device, get_device_email,
    get_scenario, get_alerts_for_scenario,
    save_alert, delete_alerts_for_scenario, delete_alert,
    update_alert_triggered, log_notification,
    get_all_scenarios_with_alerts, update_scenario_response,
    AlertRow, ScenarioRow,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["alerts"])

BREAKEVEN_SHIFT_THRESHOLD = 3  # months


# ---------------------------------------------------------------------------
# Alert config request / response models
# ---------------------------------------------------------------------------

class CreateAlertRequest(BaseModel):
    alert_type: str = Field(..., pattern="^(threshold|digest|shift)$")
    config: Optional[dict] = None  # type-specific config (e.g. shift threshold override)


class AlertOut(BaseModel):
    id: str
    scenario_id: str
    alert_type: str
    enabled: bool
    config: Optional[dict]
    last_triggered_at: Optional[float]
    created_at: float


class AlertListResponse(BaseModel):
    alerts: list[AlertOut]


# ---------------------------------------------------------------------------
# Diff engine
# ---------------------------------------------------------------------------

@dataclass
class ScenarioDiff:
    scenario_id: str
    old_verdict: Optional[str]
    new_verdict: str
    old_breakeven: Optional[int]
    new_breakeven: Optional[int]
    old_score: Optional[int]
    new_score: int
    verdict_flipped: bool
    breakeven_shifted: bool
    breakeven_shift_months: Optional[int]


def compute_diff(old_response: Optional[dict], new_response: dict, scenario_id: str) -> ScenarioDiff:
    """Compare old cached result to fresh result, flag meaningful changes."""
    new_verdict = new_response.get("verdict", "")
    new_breakeven = new_response.get("breakeven_month")
    new_score = new_response.get("buy_score", 0)

    if old_response is None:
        return ScenarioDiff(
            scenario_id=scenario_id,
            old_verdict=None, new_verdict=new_verdict,
            old_breakeven=None, new_breakeven=new_breakeven,
            old_score=None, new_score=new_score,
            verdict_flipped=False, breakeven_shifted=False,
            breakeven_shift_months=None,
        )

    old_verdict = old_response.get("verdict", "")
    old_breakeven = old_response.get("breakeven_month")
    old_score = old_response.get("buy_score", 0)

    verdict_flipped = old_verdict != new_verdict

    breakeven_shift = None
    breakeven_shifted = False
    if old_breakeven is not None and new_breakeven is not None:
        breakeven_shift = abs(new_breakeven - old_breakeven)
        breakeven_shifted = breakeven_shift >= BREAKEVEN_SHIFT_THRESHOLD
    elif old_breakeven is None and new_breakeven is not None:
        breakeven_shifted = True
        breakeven_shift = new_breakeven
    elif old_breakeven is not None and new_breakeven is None:
        breakeven_shifted = True
        breakeven_shift = old_breakeven

    return ScenarioDiff(
        scenario_id=scenario_id,
        old_verdict=old_verdict, new_verdict=new_verdict,
        old_breakeven=old_breakeven, new_breakeven=new_breakeven,
        old_score=old_score, new_score=new_score,
        verdict_flipped=verdict_flipped,
        breakeven_shifted=breakeven_shifted,
        breakeven_shift_months=breakeven_shift,
    )


def should_fire_alert(alert: AlertRow, diff: ScenarioDiff) -> bool:
    """Determine if an alert should fire based on its type and the diff."""
    if not alert.enabled:
        return False

    if alert.alert_type == "threshold":
        return diff.verdict_flipped

    if alert.alert_type == "shift":
        threshold = BREAKEVEN_SHIFT_THRESHOLD
        if alert.config_json:
            cfg = json.loads(alert.config_json)
            threshold = cfg.get("shift_months", BREAKEVEN_SHIFT_THRESHOLD)
        if diff.breakeven_shift_months is not None:
            return diff.breakeven_shift_months >= threshold
        return False

    if alert.alert_type == "digest":
        # Digest always fires (monthly cron controls frequency)
        return True

    return False


# ---------------------------------------------------------------------------
# Email delivery via AWS SES
# ---------------------------------------------------------------------------

def _send_email_ses(to_email: str, subject: str, body_html: str) -> bool:
    """Send email via AWS SES. Returns True on success."""
    try:
        import boto3
        client = boto3.client("ses", region_name="us-east-1")
        client.send_email(
            Source="alerts@rentbuysellapp.com",
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject},
                "Body": {"Html": {"Data": body_html}},
            },
        )
        return True
    except Exception as e:
        logger.error(f"SES send failed for {to_email}: {e}")
        return False


def _build_alert_email(diff: ScenarioDiff, scenario_name: str) -> tuple[str, str]:
    """Build email subject and HTML body from a diff."""
    subject = f"RentBuySell Alert: {scenario_name}"

    parts = []
    if diff.verdict_flipped:
        parts.append(
            f"<p><strong>Verdict changed:</strong> {diff.old_verdict} → {diff.new_verdict}</p>"
        )
    if diff.breakeven_shifted and diff.breakeven_shift_months is not None:
        old_be = f"{diff.old_breakeven} months" if diff.old_breakeven else "never"
        new_be = f"{diff.new_breakeven} months" if diff.new_breakeven else "never"
        parts.append(
            f"<p><strong>Breakeven shifted by {diff.breakeven_shift_months} months:</strong> "
            f"{old_be} → {new_be}</p>"
        )
    if diff.old_score is not None and diff.old_score != diff.new_score:
        parts.append(
            f"<p><strong>Buy score:</strong> {diff.old_score} → {diff.new_score}</p>"
        )

    if not parts:
        parts.append("<p>Your scenario results have been updated with fresh market data.</p>")

    body_html = (
        f"<h2>Scenario: {scenario_name}</h2>"
        + "".join(parts)
        + "<p><a href='https://rentbuysellapp.com'>View updated results →</a></p>"
        + "<p style='color:#888;font-size:12px'>You're receiving this because you set up alerts on rentbuysellapp.com.</p>"
    )

    return subject, body_html


# ---------------------------------------------------------------------------
# Post-refresh hook — called from refresh_data.py
# ---------------------------------------------------------------------------

def run_post_refresh_check():
    """Re-run all scenarios with alerts, detect diffs, send notifications.

    Called after data refresh completes. Safe to run during serving (read-only
    on market data, writes only to scenario/alert tables).
    """
    from api import SummaryRequest, _request_to_input, _snapshot_to_dict
    from market import get_data
    from simulator import run_simulation
    from scoring import compute_buy_score, compute_verdict

    scenarios = get_all_scenarios_with_alerts()
    if not scenarios:
        logger.info("No scenarios with alerts to check")
        return

    data = get_data()
    fired_count = 0

    for scenario in scenarios:
        try:
            # Re-run simulation
            inputs_dict = json.loads(scenario.inputs_json)
            req = SummaryRequest(**inputs_dict)
            sim_input = _request_to_input(req)
            result = run_simulation(sim_input, data)
            score = compute_buy_score(result)
            pct = result.percentiles

            new_response = {
                "house_price": result.house_price_used,
                "mortgage_rate": result.mortgage_rate_used,
                "property_tax_rate": result.property_tax_rate,
                "avg_buyer_net_worth": result.avg_buyer_net_worth,
                "avg_renter_net_worth": result.avg_renter_net_worth,
                "buy_score": score,
                "verdict": compute_verdict(score),
                "breakeven_month": result.breakeven_month,
                "monthly": [_snapshot_to_dict(s) for s in result.monthly],
                "percentiles": {
                    "buyer_net_worth": vars(pct.buyer_net_worth),
                    "renter_net_worth": vars(pct.renter_net_worth),
                    "home_value": vars(pct.home_value),
                    "buyer_equity": vars(pct.buyer_equity),
                },
            }

            # Compare with cached result
            old_response = json.loads(scenario.response_json) if scenario.response_json else None
            diff = compute_diff(old_response, new_response, scenario.id)

            # Update cached response
            update_scenario_response(scenario.id, json.dumps(new_response))

            # Check alerts
            alerts = get_alerts_for_scenario(scenario.id)
            for alert in alerts:
                if should_fire_alert(alert, diff):
                    email = get_device_email(alert.device_id)
                    if email:
                        subject, body = _build_alert_email(diff, scenario.name)
                        sent = _send_email_ses(email, subject, body)
                        if sent:
                            update_alert_triggered(alert.id)
                            diff_data = json.dumps({
                                "verdict_flipped": diff.verdict_flipped,
                                "breakeven_shifted": diff.breakeven_shifted,
                                "breakeven_shift_months": diff.breakeven_shift_months,
                                "old_verdict": diff.old_verdict,
                                "new_verdict": diff.new_verdict,
                                "old_score": diff.old_score,
                                "new_score": diff.new_score,
                            })
                            log_notification(
                                str(uuid.uuid4()), alert.id, scenario.id,
                                alert.device_id, diff_data,
                            )
                            fired_count += 1
                    else:
                        logger.warning(
                            f"No email for device {alert.device_id}, skipping alert {alert.id}"
                        )

        except Exception as e:
            logger.error(f"Failed to process scenario {scenario.id}: {e}")
            continue

    logger.info(f"Post-refresh check complete: {len(scenarios)} scenarios, {fired_count} alerts sent")


# ---------------------------------------------------------------------------
# Alert config endpoints
# ---------------------------------------------------------------------------

def _require_device_id(x_device_id: Optional[str]) -> str:
    if not x_device_id:
        raise HTTPException(401, "X-Device-Id header required")
    return x_device_id


def _row_to_out(row: AlertRow) -> AlertOut:
    return AlertOut(
        id=row.id,
        scenario_id=row.scenario_id,
        alert_type=row.alert_type,
        enabled=bool(row.enabled),
        config=json.loads(row.config_json) if row.config_json else None,
        last_triggered_at=row.last_triggered_at,
        created_at=row.created_at,
    )


@router.post("/scenarios/{scenario_id}/alerts", response_model=AlertOut, status_code=201)
def create_alert(
    scenario_id: str,
    req: CreateAlertRequest,
    x_device_id: Optional[str] = Header(None),
):
    """Add an alert to a saved scenario."""
    device_id = _require_device_id(x_device_id)
    ensure_device(device_id)

    scenario = get_scenario(scenario_id)
    if not scenario or scenario.device_id != device_id:
        raise HTTPException(404, "Scenario not found")

    # Check for duplicate alert type on this scenario
    existing = get_alerts_for_scenario(scenario_id)
    for a in existing:
        if a.alert_type == req.alert_type:
            raise HTTPException(409, f"Alert type '{req.alert_type}' already exists for this scenario")

    alert = AlertRow(
        id=str(uuid.uuid4()),
        scenario_id=scenario_id,
        device_id=device_id,
        alert_type=req.alert_type,
        enabled=1,
        config_json=json.dumps(req.config) if req.config else None,
        last_triggered_at=None,
        created_at=time.time(),
    )
    save_alert(alert)
    return _row_to_out(alert)


@router.get("/scenarios/{scenario_id}/alerts", response_model=AlertListResponse)
def list_alerts(
    scenario_id: str,
    x_device_id: Optional[str] = Header(None),
):
    """List alerts for a scenario."""
    device_id = _require_device_id(x_device_id)
    scenario = get_scenario(scenario_id)
    if not scenario or scenario.device_id != device_id:
        raise HTTPException(404, "Scenario not found")

    rows = get_alerts_for_scenario(scenario_id)
    return AlertListResponse(alerts=[_row_to_out(r) for r in rows])


@router.delete("/scenarios/{scenario_id}/alerts", status_code=204)
def delete_all_alerts(
    scenario_id: str,
    x_device_id: Optional[str] = Header(None),
):
    """Delete all alerts for a scenario."""
    device_id = _require_device_id(x_device_id)
    scenario = get_scenario(scenario_id)
    if not scenario or scenario.device_id != device_id:
        raise HTTPException(404, "Scenario not found")
    delete_alerts_for_scenario(scenario_id)


@router.delete("/scenarios/{scenario_id}/alerts/{alert_id}", status_code=204)
def delete_single_alert(
    scenario_id: str,
    alert_id: str,
    x_device_id: Optional[str] = Header(None),
):
    """Delete a single alert."""
    device_id = _require_device_id(x_device_id)
    scenario = get_scenario(scenario_id)
    if not scenario or scenario.device_id != device_id:
        raise HTTPException(404, "Scenario not found")
    if not delete_alert(alert_id):
        raise HTTPException(404, "Alert not found")


# ---------------------------------------------------------------------------
# Device email registration (needed for email alerts)
# ---------------------------------------------------------------------------

class SetEmailRequest(BaseModel):
    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@router.post("/devices/email", status_code=200)
def set_device_email(
    req: SetEmailRequest,
    x_device_id: Optional[str] = Header(None),
):
    """Register or update email for this device (required for email alerts)."""
    device_id = _require_device_id(x_device_id)
    ensure_device(device_id, email=req.email)
    return {"status": "ok", "email": req.email}
