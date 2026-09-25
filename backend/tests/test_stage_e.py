"""Unit and Integration Tests for Stage E (Persistence, API, Real-Time WebSocket, What-If, Demo Mode).

All tests run in FALLBACK_MODE=true with ZERO network API calls.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import config
from app.db import (
    Base,
    DecisionModel,
    ObservationModel,
    RecoveryPlanModel,
    SafetyEventModel,
    SimulationRunModel,
    TwinStateModel,
    engine,
    init_db,
)
from app.main import app, get_db
from app.models.schemas import CycleResponse, Plan, SafetyResult, TwinState, WhatIfResponse

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch, tmp_path):
    """Ensures isolated test database in tmp_path and FALLBACK_MODE=true environment."""
    db_file = tmp_path / "test_recovery.db"
    db_url = f"sqlite:///{db_file}"

    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("FALLBACK_MODE", "true")
    config.fallback_mode = True
    config.database_url = db_url

    test_engine = create_engine(db_url, connect_args={"check_same_thread": False})
    test_sessionmaker = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    monkeypatch.setattr("app.db.engine", test_engine)
    monkeypatch.setattr("app.db.SessionLocal", test_sessionmaker)

    def override_get_db():
        db = test_sessionmaker()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # Re-initialize DB tables and seed canonical P001 in isolated test DB
    init_db()

    yield

    app.dependency_overrides.clear()
    test_engine.dispose()


def test_db_creation_and_seeding():
    """Verify tables created and patient P001 seeded at startup."""
    res = client.get("/api/patients/P001/twin")
    assert res.status_code == 200
    data = res.json()
    assert data["patient_id"] == "P001"
    assert data["profile"]["name"] == "Meera Sharma"


def test_patient_twin_endpoints():
    """GET /twin, GET /twin/history, POST /observations."""
    res_twin = client.get("/api/patients/P001/twin")
    assert res_twin.status_code == 200
    assert res_twin.json()["scores"]["recovery_score"] == 68

    res_hist = client.get("/api/patients/P001/twin/history")
    assert res_hist.status_code == 200
    assert isinstance(res_hist.json(), list)

    obs_payload = {
        "timestamp": "2026-09-21T10:00:00Z",
        "pain": 5.5,
        "sleep_hours": 6.0,
        "steps": 1900,
        "swelling": 5.0,
        "temperature": 37.0,
        "heart_rate": 80,
        "crp": 5.5,
        "night_awakenings": 2,
        "flags": [],
    }
    res_obs = client.post("/api/patients/P001/observations", json=obs_payload)
    assert res_obs.status_code == 200
    assert res_obs.json()["observations"]["pain"] == 5.5


def test_cycle_endpoint_and_persistence():
    """POST /cycle runs cycle, persists final decision after retries, returns CycleResponse."""
    client.post("/api/simulator/reset", json={"patient_id": "P001"})
    res = client.post("/api/patients/P001/cycle")
    assert res.status_code == 200
    data = res.json()
    assert "cycle_id" in data
    assert data["twin"]["patient_id"] == "P001"
    assert data["safety"]["result"] in ["allow", "modify", "escalate"]

    # Verify latest plan endpoint
    if not data["escalated"]:
        res_plan = client.get("/api/patients/P001/plan/latest")
        assert res_plan.status_code == 200
        assert res_plan.json()["steps_target"] == 1900

    # Verify debate details endpoint
    res_debate = client.get(f"/api/decisions/{data['cycle_id']}/debate")
    assert res_debate.status_code == 200
    assert "proposals" in res_debate.json()


def test_whatif_endpoint():
    """POST /whatif (+20% steps): target modified per R4, persists only to simulation_runs, leaves twin_states count unchanged."""
    client.post("/api/simulator/reset", json={"patient_id": "P001"})
    twin_res = client.get("/api/patients/P001/twin")
    curr_steps = twin_res.json()["observations"]["steps"]
    history_count_before = len(client.get("/api/patients/P001/twin/history").json())

    whatif_payload = {"changes": {"steps_pct": 20}}
    res = client.post("/api/patients/P001/whatif", json=whatif_payload)
    assert res.status_code == 200
    data = res.json()

    assert "Illustrative simulation only" in data["disclaimer"]
    assert data["comparison"]["current"]["steps"] == curr_steps
    assert data["comparison"]["simulated"]["steps"] == int(round(curr_steps * 1.20))
    assert data["simulated_plan"]["steps_target"] == 2250
    assert data["safety"]["result"] in ["allow", "modify"]

    # Verify twin_states count is UNCHANGED
    res_after = client.get("/api/patients/P001/twin/history")
    assert len(res_after.json()) == history_count_before


def test_pain_spike_scenario_escalation():
    """Inject pain_spike scenario, advance to pain spike (180 min), run cycle -> ends in escalation with safety_events row for R1."""
    client.post("/api/simulator/reset", json={"patient_id": "P001"})
    res_inj = client.post("/api/simulator/inject", json={"patient_id": "P001", "scenario": "pain_spike"})
    assert res_inj.status_code == 200
    res_adv = client.post("/api/simulator/advance", json={"patient_id": "P001", "minutes": 180})
    assert res_adv.status_code == 200
    assert res_adv.json()["observations"]["pain"] == 8.2

    res_cycle = client.post("/api/patients/P001/cycle")
    assert res_cycle.status_code == 200
    data = res_cycle.json()

    assert data["escalated"] is True
    assert data["safety"]["result"] == "escalate"
    assert any(r["rule_id"] == "R1" for r in data["safety"]["rules_triggered"])
    assert data["plan"] is None


def test_simulator_reset():
    """POST /simulator/reset clears prior decisions/plans/simulations and restores baseline twin."""
    # Inject and run cycle to create records
    client.post("/api/simulator/inject", json={"patient_id": "P001", "scenario": "pain_spike"})
    client.post("/api/patients/P001/cycle")

    res_reset = client.post("/api/simulator/reset", json={"patient_id": "P001"})
    assert res_reset.status_code == 200
    data = res_reset.json()
    assert data["observations"]["pain"] == 6.0
    assert data["observations"]["steps"] == 1800

    # Decisions should be cleared
    res_dec = client.get("/api/patients/P001/decisions")
    assert res_dec.status_code == 200
    assert len(res_dec.json()) == 0


def test_audit_endpoint():
    """GET /audit returns safety events and decision audit trail."""
    client.post("/api/patients/P001/cycle")
    res_audit = client.get("/api/patients/P001/audit")
    assert res_audit.status_code == 200
    data = res_audit.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "actor" in data[0]


def test_websocket_baseline_ordering():
    """WebSocket /ws/patients/P001 receives messages in correct order during baseline cycle."""
    client.post("/api/simulator/reset", json={"patient_id": "P001"})
    with client.websocket_connect("/ws/patients/P001") as websocket:
        # Trigger cycle
        res = client.post("/api/patients/P001/cycle")
        assert res.status_code == 200

        messages = []
        # Read available messages
        for _ in range(50):
            try:
                msg = websocket.receive_json()
                messages.append(msg)
                if msg["type"] == "plan":
                    break
            except Exception:
                break

        msg_types = [m["type"] for m in messages]
        assert "twin_update" in msg_types
        assert "safety" in msg_types
        assert "plan" in msg_types


def test_websocket_escalation_message():
    """Amendment 3: WebSocket /ws/patients/P001 verifies 'escalation' message type is sent for pain_spike scenario."""
    client.post("/api/simulator/reset", json={"patient_id": "P001"})
    with client.websocket_connect("/ws/patients/P001") as websocket:
        # Inject pain_spike scenario and advance to peak pain
        client.post("/api/simulator/inject", json={"patient_id": "P001", "scenario": "pain_spike"})
        client.post("/api/simulator/advance", json={"patient_id": "P001", "minutes": 180})

        # Trigger cycle (which escalates)
        res = client.post("/api/patients/P001/cycle")
        assert res.status_code == 200
        assert res.json()["escalated"] is True

        messages = []
        for _ in range(50):
            try:
                msg = websocket.receive_json()
                messages.append(msg)
                if msg["type"] == "escalation":
                    break
            except Exception:
                break

        msg_types = [m["type"] for m in messages]
        assert "escalation" in msg_types

        esc_msg = next(m for m in messages if m["type"] == "escalation")
        assert "cycle_id" in esc_msg["payload"]
        assert "Clinician escalation" in esc_msg["payload"]["summary"]


def test_get_twin_reference():
    """Verify GET /api/patients/P001/twin/reference returns expected reference curve values sourced from thresholds.yaml."""
    client.post("/api/simulator/reset", json={"patient_id": "P001"})
    res = client.get("/api/patients/P001/twin/reference")
    assert res.status_code == 200
    data = res.json()
    assert data["surgery"] == "Total Knee Replacement"
    assert data["post_op_day"] == 4
    assert data["expected_pain"] == 4.0
    assert data["expected_inflammation"] == 5.2
    assert data["expected_steps"] == 2500
    assert "curves" in data
    assert "pain" in data["curves"]
    assert data["curves"]["pain"]["4"] == 4.0
    assert data["curves"]["inflammation"]["4"] == 5.2
    assert data["curves"]["step_target"]["4"] == 2500.0


def test_whatif_preserves_or_overrides_night_awakenings():
    """Regression test: verify run_whatif preserves baseline night_awakenings and supports explicit override."""
    client.post("/api/simulator/reset", json={"patient_id": "P001"})

    # 1. Without specifying night_awakenings in changes -> should preserve baseline night_awakenings (4 for Meera)
    res1 = client.post("/api/patients/P001/whatif", json={"changes": {"steps_pct": 10}})
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["simulated_twin"]["observations"]["night_awakenings"] == 4

    # 2. With explicit night_awakenings in changes -> should use overridden value
    res2 = client.post("/api/patients/P001/whatif", json={"changes": {"night_awakenings": 2}})
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["simulated_twin"]["observations"]["night_awakenings"] == 2


def test_cycle_endpoint_fallback_mode_false_regression(monkeypatch):
    """Regression test: verify POST /cycle does not crash with NameError when FALLBACK_MODE env var is absent and config.fallback_mode is False."""
    client.post("/api/simulator/reset", json={"patient_id": "P001"})

    # 1. Clear FALLBACK_MODE env var and config flag so fallback_setting calculation path runs
    monkeypatch.delenv("FALLBACK_MODE", raising=False)
    monkeypatch.setattr("app.config.config.fallback_mode", False)

    # 2. Mock astream_cycle to avoid actual LLM network calls during unit test execution
    async def mock_astream_cycle(twin, fallback=False, is_simulation=False):
        yield (
            "cycle_test_123",
            {
                "twin_builder": {"twin": twin},
                "safety_guardian": {
                    "safety_result": SafetyResult(result="allow", rules_triggered=[], modified_plan=None),
                    "escalated": False,
                },
                "plan_generator": {"final_plan": None},
            },
        )

    monkeypatch.setattr("app.main.astream_cycle", mock_astream_cycle)

    # 3. Call endpoint without explicit ?fallback= query parameter
    res = client.post("/api/patients/P001/cycle")

    # 4. Assert response is 200 OK and not a 500 NameError crash
    assert res.status_code == 200
    data = res.json()
    assert data["cycle_id"] == "cycle_test_123"
    assert data["twin"]["patient_id"] == "P001"


def test_cycle_endpoint_unknown_patient_404():
    """Regression test: verify POST /api/patients/P999/cycle for unknown patient returns 404 PATIENT_NOT_FOUND, not 500."""
    res = client.post("/api/patients/P999/cycle")
    assert res.status_code == 404
    data = res.json()
    assert data["detail"]["error"]["code"] == "PATIENT_NOT_FOUND"







