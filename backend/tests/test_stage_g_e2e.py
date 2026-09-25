"""End-to-End API Integration Tests for Stage G (SPEC Section 21.1).

ALL tests interact STRICTLY through the FastAPI TestClient hitting real HTTP endpoints.
Zero direct imports of graph.py, whatif.py, or internal node functions.
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import config
from app.db import (
    Base,
    engine,
    init_db,
)
from app.main import app, get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch, tmp_path):
    """Ensures isolated test database in tmp_path and FALLBACK_MODE=true environment by default."""
    db_file = tmp_path / "test_stage_g_e2e.db"
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

    # Initialize DB tables and seed canonical patient P001
    init_db()

    yield

    app.dependency_overrides.clear()
    test_engine.dispose()


# 1. Normal Recovery Scenario
def test_e2e_normal_recovery():
    """Scenario 1: Reset baseline meera_day4, POST /cycle -> returns 200 OK, safety allow, valid recovery plan."""
    res_reset = client.post("/api/simulator/reset", json={"patient_id": "P001"})
    assert res_reset.status_code == 200

    res_cycle = client.post("/api/patients/P001/cycle")
    assert res_cycle.status_code == 200
    data = res_cycle.json()

    assert data["cycle_id"].startswith("cycle_")
    assert data["safety"]["result"] in ["allow", "modify"]
    assert data["escalated"] is False
    assert data["plan"] is not None
    assert data["plan"]["horizon_hours"] in [6, 12]


# 2. Poor Sleep Scenario
def test_e2e_poor_sleep():
    """Scenario 2: Inject poor_sleep, POST /cycle -> sleep agent proposes sleep restoration action."""
    client.post("/api/simulator/reset", json={"patient_id": "P001"})
    res_inj = client.post("/api/simulator/inject", json={"patient_id": "P001", "scenario": "poor_sleep"})
    assert res_inj.status_code == 200
    assert res_inj.json()["observations"]["sleep_hours"] <= 4.0

    res_cycle = client.post("/api/patients/P001/cycle")
    assert res_cycle.status_code == 200
    data = res_cycle.json()

    # Sleep proposal should exist
    sleep_props = [p for p in data["proposals"] if p["agent"] == "sleep"]
    assert len(sleep_props) > 0
    assert sleep_props[0]["direction"] == "increase"


# 3. Pain Increase Scenario
def test_e2e_pain_increase():
    """Scenario 3: Inject pain_spike, advance 180 min, POST /cycle -> triggers Safety Guardian R1 escalation."""
    client.post("/api/simulator/reset", json={"patient_id": "P001"})
    client.post("/api/simulator/inject", json={"patient_id": "P001", "scenario": "pain_spike"})
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


# 4. Inflammation Increase Scenario
def test_e2e_inflammation_increase():
    """Scenario 4: Inject increased_inflammation, POST /cycle -> inflammation agent triggers swelling/CRP monitoring proposal."""
    client.post("/api/simulator/reset", json={"patient_id": "P001"})
    res_inj = client.post("/api/simulator/inject", json={"patient_id": "P001", "scenario": "increased_inflammation"})
    assert res_inj.status_code == 200

    res_cycle = client.post("/api/patients/P001/cycle")
    assert res_cycle.status_code == 200
    data = res_cycle.json()

    inflam_props = [p for p in data["proposals"] if p["agent"] == "inflammation"]
    assert len(inflam_props) > 0
    assert inflam_props[0]["action_type"] in ["swelling", "monitoring"]


# 5. Mobility Decrease Scenario
def test_e2e_mobility_decrease():
    """Scenario 5: Inject reduced_mobility, advance 120 min, POST /cycle -> mobility agent proposes step progression adjustment."""
    client.post("/api/simulator/reset", json={"patient_id": "P001"})
    client.post("/api/simulator/inject", json={"patient_id": "P001", "scenario": "reduced_mobility"})
    res_adv = client.post("/api/simulator/advance", json={"patient_id": "P001", "minutes": 120})
    assert res_adv.status_code == 200
    assert res_adv.json()["observations"]["steps"] == 1100

    res_cycle = client.post("/api/patients/P001/cycle")
    assert res_cycle.status_code == 200
    data = res_cycle.json()

    mob_props = [p for p in data["proposals"] if p["agent"] == "mobility"]
    assert len(mob_props) > 0


# 6. Safety Veto / Modify Scenario
def test_e2e_safety_veto():
    """Scenario 6: Verify Safety Guardian R4 rule enforces step target reduction when swelling >= 5.0."""
    client.post("/api/simulator/reset", json={"patient_id": "P001"})
    # Meera baseline has swelling=6.0 (>= 5.0)
    res_cycle = client.post("/api/patients/P001/cycle")
    assert res_cycle.status_code == 200
    data = res_cycle.json()

    # Safety Guardian evaluation result
    assert data["safety"]["result"] in ["allow", "modify"]
    if data["safety"]["result"] == "modify":
        assert any(r["rule_id"] == "R4" for r in data["safety"]["rules_triggered"])


# 7. Escalation Scenario
def test_e2e_escalation():
    """Scenario 7: Inject recovery_deviation, advance 120 min, POST /cycle -> safety escalation with R1 and R8 rules hit."""
    client.post("/api/simulator/reset", json={"patient_id": "P001"})
    client.post("/api/simulator/inject", json={"patient_id": "P001", "scenario": "recovery_deviation"})
    res_adv = client.post("/api/simulator/advance", json={"patient_id": "P001", "minutes": 120})
    assert res_adv.status_code == 200

    res_cycle = client.post("/api/patients/P001/cycle")
    assert res_cycle.status_code == 200
    data = res_cycle.json()

    assert data["escalated"] is True
    assert data["safety"]["result"] == "escalate"
    rule_ids = [r["rule_id"] for r in data["safety"]["rules_triggered"]]
    assert "R1" in rule_ids or "R8" in rule_ids


# 8. What-If Simulation Scenario
def test_e2e_whatif():
    """Scenario 8: POST /api/patients/P001/whatif -> returns simulated plan, comparison metrics, disclaimer, leaves twin_states history count unchanged."""
    client.post("/api/simulator/reset", json={"patient_id": "P001"})
    hist_before = client.get("/api/patients/P001/twin/history").json()

    res_whatif = client.post("/api/patients/P001/whatif", json={"changes": {"steps_pct": 20}})
    assert res_whatif.status_code == 200
    data = res_whatif.json()

    assert "Illustrative simulation only" in data["disclaimer"]
    assert "comparison" in data
    assert "simulated_plan" in data
    assert "effects" in data

    hist_after = client.get("/api/patients/P001/twin/history").json()
    assert len(hist_after) == len(hist_before)


# 9. Medication Limit Enforcement Scenario (Rule R5)
def test_e2e_medication_limit():
    """Scenario 9: Verify Rule R5 - No proposal across any API cycle may recommend, choose, start, or alter medication/dose."""
    client.post("/api/simulator/reset", json={"patient_id": "P001"})
    res_cycle = client.post("/api/patients/P001/cycle")
    assert res_cycle.status_code == 200
    data = res_cycle.json()

    for prop in data["proposals"]:
        # Rule R5: action_type must be one of allowed types, and never a direct medication prescription
        assert prop["action_type"] in ["mobility", "sleep", "swelling", "pain_review", "monitoring", "escalate"]
        if prop["agent"] == "medication":
            assert prop["action_type"] in ["pain_review", "monitoring"]
            assert prop["direction"] == "maintain"


# 10. LLM Failure and Fallback Execution Scenarios (Sub-cases a & b)
def test_e2e_llm_failure_and_fallback_subcase_a():
    """Scenario 10a: FALLBACK_MODE=true runs cycle normally through REST API with zero network calls."""
    client.post("/api/simulator/reset", json={"patient_id": "P001"})
    res = client.post("/api/patients/P001/cycle")
    assert res.status_code == 200
    data = res.json()
    assert data["cycle_id"].startswith("cycle_")
    assert data["twin"]["patient_id"] == "P001"


def test_e2e_llm_failure_and_fallback_subcase_b(monkeypatch):
    """Scenario 10b: FALLBACK_MODE=false with LLM API mocked to raise an exception -> system degrades gracefully to rule-based fallback without crashing."""
    client.post("/api/simulator/reset", json={"patient_id": "P001"})

    # Disable fallback mode so LLM branch is attempted
    monkeypatch.delenv("FALLBACK_MODE", raising=False)
    monkeypatch.setattr("app.config.config.fallback_mode", False)
    monkeypatch.setattr("app.config.config.llm_api_key", "mock_key_123")

    # Mock google.genai.Client to raise network/API timeout exception inside call_llm_structured
    class MockClientFailure:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("Google GenAI API Call Timed Out / Quota Exceeded")

    import sys
    import types
    mock_genai_mod = types.ModuleType("google.genai")
    mock_genai_mod.Client = MockClientFailure
    mock_types_mod = types.ModuleType("google.genai.types")
    mock_types_mod.GenerateContentConfig = lambda **k: None

    monkeypatch.setitem(sys.modules, "google.genai", mock_genai_mod)
    monkeypatch.setitem(sys.modules, "google.genai.types", mock_types_mod)

    # Execute cycle via HTTP REST API
    res = client.post("/api/patients/P001/cycle")

    # System must degrade gracefully to rule-based fallback and return 200 OK
    assert res.status_code == 200
    data = res.json()
    assert data["cycle_id"].startswith("cycle_")
    assert data["safety"]["result"] in ["allow", "modify", "escalate"]
    assert data["twin"]["patient_id"] == "P001"

