"""Tests for API endpoints via FastAPI TestClient."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from data_store import init_db


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    """Use a temp SQLite DB for each test."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("data_store.DB_PATH", db_path)
    init_db()
    yield db_path


@pytest.fixture
def client():
    from api import app
    return TestClient(app)


MINIMAL_REQUEST = {"monthly_rent": 3000, "monthly_budget": 5000}

FULL_REQUEST = {
    "monthly_rent": 3000,
    "monthly_budget": 5000,
    "initial_cash": 150_000,
    "yearly_income": 120_000,
    "house_price": 500_000,
    "down_payment_pct": 0.20,
    "mortgage_rate": 0.065,
    "years": 10,
    "num_simulations": 50,
    "outlook_preset": "historical",
}

DEVICE_HEADERS = {"X-Device-Id": "test-device-001"}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# POST /summary
# ---------------------------------------------------------------------------

class TestSummary:
    def test_minimal_request(self, client):
        """Just rent + budget — everything else auto-resolved."""
        r = client.post("/summary", json=MINIMAL_REQUEST)
        assert r.status_code == 200
        data = r.json()
        assert "house_price" in data
        assert "mortgage_rate" in data
        assert "buy_score" in data
        assert "verdict" in data
        assert "breakeven_month" in data
        assert "monthly" in data
        assert "percentiles" in data
        assert "warnings" in data
        assert isinstance(data["monthly"], list)
        assert len(data["monthly"]) == 120  # 10 years default

    def test_response_shape(self, client):
        r = client.post("/summary", json=FULL_REQUEST)
        data = r.json()

        # Scalar fields
        assert isinstance(data["house_price"], (int, float))
        assert isinstance(data["mortgage_rate"], (int, float))
        assert isinstance(data["buy_score"], int)
        assert 8 <= data["buy_score"] <= 96
        assert isinstance(data["verdict"], str)

        # Monthly data
        m0 = data["monthly"][0]
        expected_fields = [
            "home_value", "mortgage_payment", "interest_payment", "principal_payment",
            "remaining_balance", "maintenance", "property_tax", "insurance", "pmi",
            "tax_savings", "total_housing_cost", "rent", "budget",
            "buyer_investment", "renter_investment", "buyer_equity",
            "buyer_net_worth", "renter_net_worth",
            "cumulative_buy_cost", "cumulative_rent_cost",
        ]
        for field in expected_fields:
            assert field in m0, f"Missing field: {field}"

        # Percentiles
        pct = data["percentiles"]
        for key in ["buyer_net_worth", "renter_net_worth", "home_value", "buyer_equity"]:
            assert key in pct
            for band in ["p10", "p25", "p50", "p75", "p90"]:
                assert band in pct[key]
                assert len(pct[key][band]) == 120

    def test_validation_error_422(self, client):
        """Budget < rent should return 422 with error details."""
        r = client.post("/summary", json={
            "monthly_rent": 5000,
            "monthly_budget": 3000,
        })
        assert r.status_code == 422

    def test_explicit_house_price(self, client):
        r = client.post("/summary", json={**FULL_REQUEST, "house_price": 600_000})
        assert r.status_code == 200
        assert r.json()["house_price"] == 600_000

    def test_stay_years(self, client):
        """stay_years < years should produce shorter ownership."""
        r = client.post("/summary", json={**FULL_REQUEST, "stay_years": 5})
        assert r.status_code == 200
        data = r.json()
        # Post-sell: mortgage should be 0
        assert data["monthly"][70]["mortgage_payment"] == 0

    def test_outlook_presets(self, client):
        """Different outlooks should produce different scores."""
        r1 = client.post("/summary", json={**FULL_REQUEST, "outlook_preset": "optimistic"})
        r2 = client.post("/summary", json={**FULL_REQUEST, "outlook_preset": "crisis"})
        assert r1.status_code == 200
        assert r2.status_code == 200
        # Crisis should generally produce lower buy score
        assert r1.json()["buy_score"] >= r2.json()["buy_score"]


# ---------------------------------------------------------------------------
# Scenario CRUD
# ---------------------------------------------------------------------------

class TestScenarios:
    def test_no_device_id_401(self, client):
        r = client.get("/scenarios")
        assert r.status_code == 401

    def test_create_list_delete(self, client):
        # Create
        r = client.post("/scenarios", headers=DEVICE_HEADERS, json={
            "name": "Test Scenario",
            "inputs": FULL_REQUEST,
        })
        assert r.status_code == 201
        sc = r.json()
        sc_id = sc["id"]
        assert sc["name"] == "Test Scenario"
        assert sc["inputs"]["monthly_rent"] == 3000

        # List
        r = client.get("/scenarios", headers=DEVICE_HEADERS)
        assert r.status_code == 200
        scenarios = r.json()["scenarios"]
        assert len(scenarios) == 1
        assert scenarios[0]["id"] == sc_id

        # Get single
        r = client.get(f"/scenarios/{sc_id}", headers=DEVICE_HEADERS)
        assert r.status_code == 200
        assert r.json()["name"] == "Test Scenario"

        # Delete
        r = client.delete(f"/scenarios/{sc_id}", headers=DEVICE_HEADERS)
        assert r.status_code == 204

        # Verify deleted
        r = client.get("/scenarios", headers=DEVICE_HEADERS)
        assert len(r.json()["scenarios"]) == 0

    def test_wrong_device_404(self, client):
        # Create with device 1
        r = client.post("/scenarios", headers=DEVICE_HEADERS, json={
            "name": "Secret", "inputs": FULL_REQUEST,
        })
        sc_id = r.json()["id"]

        # Try to access with device 2
        r = client.get(f"/scenarios/{sc_id}", headers={"X-Device-Id": "other-device"})
        assert r.status_code == 404

    def test_run_scenario(self, client):
        """Re-run returns fresh SummaryResponse shape."""
        r = client.post("/scenarios", headers=DEVICE_HEADERS, json={
            "name": "Runnable", "inputs": FULL_REQUEST,
        })
        sc_id = r.json()["id"]

        r = client.post(f"/scenarios/{sc_id}/run", headers=DEVICE_HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert "house_price" in data
        assert "monthly" in data
        assert "buy_score" in data


# ---------------------------------------------------------------------------
# Alert config
# ---------------------------------------------------------------------------

class TestAlerts:
    def _create_scenario(self, client):
        r = client.post("/scenarios", headers=DEVICE_HEADERS, json={
            "name": "Alert Test", "inputs": FULL_REQUEST,
        })
        return r.json()["id"]

    def test_create_alert(self, client):
        sc_id = self._create_scenario(client)
        r = client.post(f"/scenarios/{sc_id}/alerts", headers=DEVICE_HEADERS, json={
            "alert_type": "threshold",
        })
        assert r.status_code == 201
        alert = r.json()
        assert alert["alert_type"] == "threshold"
        assert alert["enabled"] is True

    def test_duplicate_alert_type_409(self, client):
        sc_id = self._create_scenario(client)
        r = client.post(f"/scenarios/{sc_id}/alerts", headers=DEVICE_HEADERS, json={
            "alert_type": "threshold",
        })
        assert r.status_code == 201

        r = client.post(f"/scenarios/{sc_id}/alerts", headers=DEVICE_HEADERS, json={
            "alert_type": "threshold",
        })
        assert r.status_code == 409

    def test_list_alerts(self, client):
        sc_id = self._create_scenario(client)
        client.post(f"/scenarios/{sc_id}/alerts", headers=DEVICE_HEADERS, json={
            "alert_type": "threshold",
        })
        client.post(f"/scenarios/{sc_id}/alerts", headers=DEVICE_HEADERS, json={
            "alert_type": "shift",
        })

        r = client.get(f"/scenarios/{sc_id}/alerts", headers=DEVICE_HEADERS)
        assert r.status_code == 200
        assert len(r.json()["alerts"]) == 2

    def test_delete_single_alert(self, client):
        sc_id = self._create_scenario(client)
        r = client.post(f"/scenarios/{sc_id}/alerts", headers=DEVICE_HEADERS, json={
            "alert_type": "digest",
        })
        alert_id = r.json()["id"]

        r = client.delete(f"/scenarios/{sc_id}/alerts/{alert_id}", headers=DEVICE_HEADERS)
        assert r.status_code == 204

        r = client.get(f"/scenarios/{sc_id}/alerts", headers=DEVICE_HEADERS)
        assert len(r.json()["alerts"]) == 0

    def test_delete_all_alerts(self, client):
        sc_id = self._create_scenario(client)
        client.post(f"/scenarios/{sc_id}/alerts", headers=DEVICE_HEADERS, json={"alert_type": "threshold"})
        client.post(f"/scenarios/{sc_id}/alerts", headers=DEVICE_HEADERS, json={"alert_type": "shift"})

        r = client.delete(f"/scenarios/{sc_id}/alerts", headers=DEVICE_HEADERS)
        assert r.status_code == 204

        r = client.get(f"/scenarios/{sc_id}/alerts", headers=DEVICE_HEADERS)
        assert len(r.json()["alerts"]) == 0


# ---------------------------------------------------------------------------
# Device email
# ---------------------------------------------------------------------------

class TestDeviceEmail:
    def test_register_email(self, client):
        r = client.post("/devices/email", headers=DEVICE_HEADERS, json={
            "email": "test@example.com",
        })
        assert r.status_code == 200
        assert r.json()["email"] == "test@example.com"

    def test_invalid_email_422(self, client):
        r = client.post("/devices/email", headers=DEVICE_HEADERS, json={
            "email": "not-an-email",
        })
        assert r.status_code == 422

    def test_no_device_id_401(self, client):
        r = client.post("/devices/email", json={"email": "test@example.com"})
        assert r.status_code == 401
