"""Tests for scenarios.py and notifications.py — CRUD + diff engine."""

import json
import time
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data_store import (
    init_db, get_connection, ensure_device, save_scenario, get_scenario,
    get_scenarios_for_device, delete_scenario, update_scenario_response,
    save_alert, get_alerts_for_scenario, delete_alerts_for_scenario,
    get_all_scenarios_with_alerts, ScenarioRow, AlertRow, DB_PATH,
)
from notifications import compute_diff, should_fire_alert, ScenarioDiff


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    """Use a temp SQLite DB for each test."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("data_store.DB_PATH", db_path)
    init_db()
    yield db_path


SAMPLE_INPUTS = {
    "monthly_rent": 3000,
    "monthly_budget": 4500,
    "initial_cash": 100000,
    "years": 10,
    "num_simulations": 50,
}


def _make_scenario(device_id: str = "dev-1", name: str = "Test Scenario",
                   scenario_id: str = "sc-1") -> ScenarioRow:
    now = time.time()
    return ScenarioRow(
        id=scenario_id,
        device_id=device_id,
        name=name,
        inputs_json=json.dumps(SAMPLE_INPUTS),
        response_json=None,
        created_at=now,
        updated_at=now,
    )


def _make_alert(scenario_id: str = "sc-1", device_id: str = "dev-1",
                alert_type: str = "threshold", alert_id: str = "al-1") -> AlertRow:
    return AlertRow(
        id=alert_id,
        scenario_id=scenario_id,
        device_id=device_id,
        alert_type=alert_type,
        enabled=1,
        config_json=None,
        last_triggered_at=None,
        created_at=time.time(),
    )


# ---------------------------------------------------------------------------
# Device identity
# ---------------------------------------------------------------------------

class TestDeviceIdentity:
    def test_ensure_device_creates(self):
        ensure_device("dev-1")
        conn = get_connection()
        row = conn.execute("SELECT * FROM devices WHERE device_id = 'dev-1'").fetchone()
        conn.close()
        assert row is not None
        assert row["email"] is None

    def test_ensure_device_with_email(self):
        ensure_device("dev-2", email="test@example.com")
        conn = get_connection()
        row = conn.execute("SELECT * FROM devices WHERE device_id = 'dev-2'").fetchone()
        conn.close()
        assert row["email"] == "test@example.com"

    def test_ensure_device_updates_last_seen(self):
        ensure_device("dev-3")
        conn = get_connection()
        row1 = conn.execute("SELECT last_seen_at FROM devices WHERE device_id = 'dev-3'").fetchone()
        conn.close()

        time.sleep(0.01)
        ensure_device("dev-3")
        conn = get_connection()
        row2 = conn.execute("SELECT last_seen_at FROM devices WHERE device_id = 'dev-3'").fetchone()
        conn.close()
        assert row2["last_seen_at"] >= row1["last_seen_at"]


# ---------------------------------------------------------------------------
# Scenarios CRUD
# ---------------------------------------------------------------------------

class TestScenariosCRUD:
    def test_save_and_get(self):
        ensure_device("dev-1")
        sc = _make_scenario()
        save_scenario(sc)

        retrieved = get_scenario("sc-1")
        assert retrieved is not None
        assert retrieved.name == "Test Scenario"
        assert json.loads(retrieved.inputs_json) == SAMPLE_INPUTS

    def test_list_for_device(self):
        ensure_device("dev-1")
        save_scenario(_make_scenario(scenario_id="sc-1"))
        save_scenario(_make_scenario(scenario_id="sc-2", name="Second"))

        scenarios = get_scenarios_for_device("dev-1")
        assert len(scenarios) == 2

    def test_list_filters_by_device(self):
        ensure_device("dev-1")
        ensure_device("dev-2")
        save_scenario(_make_scenario(device_id="dev-1", scenario_id="sc-1"))
        save_scenario(_make_scenario(device_id="dev-2", scenario_id="sc-2"))

        assert len(get_scenarios_for_device("dev-1")) == 1
        assert len(get_scenarios_for_device("dev-2")) == 1

    def test_delete(self):
        ensure_device("dev-1")
        save_scenario(_make_scenario())
        assert delete_scenario("sc-1") is True
        assert get_scenario("sc-1") is None

    def test_delete_nonexistent(self):
        assert delete_scenario("nope") is False

    def test_update_response(self):
        ensure_device("dev-1")
        save_scenario(_make_scenario())
        response = {"buy_score": 75, "verdict": "lean buy", "breakeven_month": 48}
        update_scenario_response("sc-1", json.dumps(response))

        retrieved = get_scenario("sc-1")
        assert json.loads(retrieved.response_json) == response


# ---------------------------------------------------------------------------
# Alerts CRUD
# ---------------------------------------------------------------------------

class TestAlertsCRUD:
    def test_save_and_get(self):
        ensure_device("dev-1")
        save_scenario(_make_scenario())
        save_alert(_make_alert())

        alerts = get_alerts_for_scenario("sc-1")
        assert len(alerts) == 1
        assert alerts[0].alert_type == "threshold"

    def test_multiple_alert_types(self):
        ensure_device("dev-1")
        save_scenario(_make_scenario())
        save_alert(_make_alert(alert_type="threshold", alert_id="al-1"))
        save_alert(_make_alert(alert_type="shift", alert_id="al-2"))
        save_alert(_make_alert(alert_type="digest", alert_id="al-3"))

        alerts = get_alerts_for_scenario("sc-1")
        assert len(alerts) == 3

    def test_delete_all_alerts(self):
        ensure_device("dev-1")
        save_scenario(_make_scenario())
        save_alert(_make_alert(alert_id="al-1"))
        save_alert(_make_alert(alert_type="shift", alert_id="al-2"))

        deleted = delete_alerts_for_scenario("sc-1")
        assert deleted == 2
        assert len(get_alerts_for_scenario("sc-1")) == 0

    def test_get_scenarios_with_alerts(self):
        ensure_device("dev-1")
        save_scenario(_make_scenario(scenario_id="sc-1"))
        save_scenario(_make_scenario(scenario_id="sc-2", name="No alerts"))
        save_alert(_make_alert(scenario_id="sc-1"))

        with_alerts = get_all_scenarios_with_alerts()
        assert len(with_alerts) == 1
        assert with_alerts[0].id == "sc-1"


# ---------------------------------------------------------------------------
# Diff engine
# ---------------------------------------------------------------------------

class TestDiffEngine:
    def test_no_old_response(self):
        diff = compute_diff(None, {"verdict": "lean buy", "breakeven_month": 48, "buy_score": 70}, "sc-1")
        assert diff.verdict_flipped is False
        assert diff.breakeven_shifted is False
        assert diff.new_verdict == "lean buy"

    def test_verdict_flip(self):
        old = {"verdict": "lean buy", "breakeven_month": 48, "buy_score": 70}
        new = {"verdict": "lean rent", "breakeven_month": 48, "buy_score": 35}
        diff = compute_diff(old, new, "sc-1")
        assert diff.verdict_flipped is True
        assert diff.breakeven_shifted is False

    def test_breakeven_shift_small(self):
        old = {"verdict": "lean buy", "breakeven_month": 48, "buy_score": 70}
        new = {"verdict": "lean buy", "breakeven_month": 50, "buy_score": 70}
        diff = compute_diff(old, new, "sc-1")
        assert diff.breakeven_shifted is False
        assert diff.breakeven_shift_months == 2

    def test_breakeven_shift_large(self):
        old = {"verdict": "lean buy", "breakeven_month": 48, "buy_score": 70}
        new = {"verdict": "lean buy", "breakeven_month": 60, "buy_score": 70}
        diff = compute_diff(old, new, "sc-1")
        assert diff.breakeven_shifted is True
        assert diff.breakeven_shift_months == 12

    def test_breakeven_appeared(self):
        old = {"verdict": "lean rent", "breakeven_month": None, "buy_score": 30}
        new = {"verdict": "lean buy", "breakeven_month": 36, "buy_score": 65}
        diff = compute_diff(old, new, "sc-1")
        assert diff.breakeven_shifted is True

    def test_breakeven_disappeared(self):
        old = {"verdict": "lean buy", "breakeven_month": 48, "buy_score": 70}
        new = {"verdict": "lean rent", "breakeven_month": None, "buy_score": 30}
        diff = compute_diff(old, new, "sc-1")
        assert diff.breakeven_shifted is True


# ---------------------------------------------------------------------------
# Alert firing logic
# ---------------------------------------------------------------------------

class TestAlertFiring:
    def _diff(self, verdict_flipped=False, breakeven_shifted=False, shift_months=None):
        return ScenarioDiff(
            scenario_id="sc-1",
            old_verdict="lean buy", new_verdict="lean rent" if verdict_flipped else "lean buy",
            old_breakeven=48, new_breakeven=48 + (shift_months or 0),
            old_score=70, new_score=35 if verdict_flipped else 70,
            verdict_flipped=verdict_flipped,
            breakeven_shifted=breakeven_shifted,
            breakeven_shift_months=shift_months,
        )

    def test_threshold_fires_on_flip(self):
        alert = _make_alert(alert_type="threshold")
        diff = self._diff(verdict_flipped=True)
        assert should_fire_alert(alert, diff) is True

    def test_threshold_silent_on_no_flip(self):
        alert = _make_alert(alert_type="threshold")
        diff = self._diff(verdict_flipped=False)
        assert should_fire_alert(alert, diff) is False

    def test_shift_fires_on_large_shift(self):
        alert = _make_alert(alert_type="shift")
        diff = self._diff(breakeven_shifted=True, shift_months=6)
        assert should_fire_alert(alert, diff) is True

    def test_shift_silent_on_small_shift(self):
        alert = _make_alert(alert_type="shift")
        diff = self._diff(breakeven_shifted=False, shift_months=1)
        assert should_fire_alert(alert, diff) is False

    def test_shift_custom_threshold(self):
        alert = _make_alert(alert_type="shift")
        alert.config_json = json.dumps({"shift_months": 6})
        diff = self._diff(shift_months=5)
        assert should_fire_alert(alert, diff) is False

        diff = self._diff(shift_months=6)
        assert should_fire_alert(alert, diff) is True

    def test_digest_always_fires(self):
        alert = _make_alert(alert_type="digest")
        diff = self._diff()
        assert should_fire_alert(alert, diff) is True

    def test_disabled_alert_never_fires(self):
        alert = _make_alert(alert_type="threshold")
        alert.enabled = 0
        diff = self._diff(verdict_flipped=True)
        assert should_fire_alert(alert, diff) is False
