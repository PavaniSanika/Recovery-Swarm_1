"""Tests for Stage H1: Screening Flags Workflow Component.

Verifies golden vectors S1-S8, read-only immutability, safety guardian consistency, scenario execution, forbidden wording rules, and current step target retroactive evaluation for SF5.
"""

from copy import deepcopy
import pytest
from fastapi.testclient import TestClient

from app.models.schemas import TwinState, Observations, ObservationIn, HistoryEntry, Scores
from app.models.extensions import SCREENING_DISCLAIMER
from app.workflow.screening import screen
from app.agents.safety import SafetyGuardian
from app.twin.engine import TwinEngine
from app.simulator import Simulator, SCENARIOS_DIR
from app.main import app

client = TestClient(app)

# Canonical Meera baseline twin state for tests
BASE_MEERA = TwinState(
    patient_id="P001",
    profile={"name": "Meera Sharma", "age": 62, "surgery": "Total Knee Replacement", "post_op_day": 4},
    observations={"pain": 6.0, "sleep_hours": 4.5, "steps": 1800, "swelling": 6.0, "temperature": 37.1, "heart_rate": 84, "crp": 6.2},
    scores={"inflammation_score": 6.2, "mobility_capacity": 5.0, "sleep_quality": 3.5, "medication_effectiveness": 5.5, "complication_risk": 3.2, "recovery_score": 68},
    trajectory={"overall": "slightly_below_expected", "inflammation": "stable_high", "mobility": "below_expected", "sleep": "poor"},
    medications={"current": ["Paracetamol", "Low-dose opioid at night"], "response_score": 5.5},
    history=[],
)

def make_history_entry(pain=6.0, steps=1800, overall="slightly_below_expected"):
    return HistoryEntry(
        timestamp="2026-09-25T10:00:00Z",
        observations=Observations(
            pain=pain, sleep_hours=4.5, steps=steps, swelling=6.0, temperature=37.1, heart_rate=84, crp=6.2
        ),
        scores=Scores(
            inflammation_score=6.2, mobility_capacity=5.0, sleep_quality=3.5, medication_effectiveness=5.5, complication_risk=3.2, recovery_score=68
        ),
        overall=overall,
    )


# ---------- GOLDEN VECTORS S1 - S8 ----------

def test_golden_vector_S1_meera_baseline():
    """S1: Meera baseline, empty history, no flags -> flags == []"""
    res = screen(BASE_MEERA, flags=[], history=[])
    assert res.flags == [], f"Expected empty flags for S1, got {res.flags}"
    assert res.disclaimer == SCREENING_DISCLAIMER


def test_golden_vector_S2_infection_urgent():
    """S2: temperature 38.2, observation flags ['wound_discharge'] -> SF1 urgent"""
    twin = BASE_MEERA.model_copy(deep=True)
    twin.observations.temperature = 38.2
    res = screen(twin, flags=["wound_discharge"], history=[])
    
    assert len(res.flags) == 1
    sf1 = res.flags[0]
    assert sf1.flag_id == "SF1"
    assert sf1.severity == "urgent"
    assert sf1.disclaimer == SCREENING_DISCLAIMER


def test_golden_vector_S3_infection_review():
    """S3: temperature 37.9, crp 7.5, no flags -> SF1 review"""
    twin = BASE_MEERA.model_copy(deep=True)
    twin.observations.temperature = 37.9
    twin.observations.crp = 7.5
    res = screen(twin, flags=[], history=[])
    
    assert len(res.flags) == 1
    sf1 = res.flags[0]
    assert sf1.flag_id == "SF1"
    assert sf1.severity == "review"


def test_golden_vector_S4a_clot_urgent():
    """S4a: flags ['calf_pain'], swelling 7.5 -> SF2 urgent"""
    twin = BASE_MEERA.model_copy(deep=True)
    twin.observations.swelling = 7.5
    res = screen(twin, flags=["calf_pain"], history=[])
    
    assert len(res.flags) == 1
    sf2 = res.flags[0]
    assert sf2.flag_id == "SF2"
    assert sf2.severity == "urgent"


def test_golden_vector_S4b_clot_review():
    """S4b: flags ['calf_pain'], swelling 6.5 -> SF2 review"""
    twin = BASE_MEERA.model_copy(deep=True)
    twin.observations.swelling = 6.5
    res = screen(twin, flags=["calf_pain"], history=[])
    
    assert len(res.flags) == 1
    sf2 = res.flags[0]
    assert sf2.flag_id == "SF2"
    assert sf2.severity == "review"


def test_golden_vector_S5_pe_clot_urgent():
    """S5: flags ['chest_pain'] -> SF2 urgent"""
    res = screen(BASE_MEERA, flags=["chest_pain"], history=[])
    
    assert len(res.flags) == 1
    sf2 = res.flags[0]
    assert sf2.flag_id == "SF2"
    assert sf2.severity == "urgent"


def test_golden_vector_S6a_uncontrolled_pain_review():
    """S6a: pain 7.5, previous history pain 7.2 -> SF4 review"""
    twin = BASE_MEERA.model_copy(deep=True)
    twin.observations.pain = 7.5
    hist = [make_history_entry(pain=7.2)]
    res = screen(twin, flags=[], history=hist)
    
    sf4_flags = [f for f in res.flags if f.flag_id == "SF4"]
    assert len(sf4_flags) == 1
    assert sf4_flags[0].severity == "review"


def test_golden_vector_S6b_pain_not_consecutive():
    """S6b: pain 7.5, previous history pain 5.0 -> no SF4"""
    twin = BASE_MEERA.model_copy(deep=True)
    twin.observations.pain = 7.5
    hist = [make_history_entry(pain=5.0)]
    res = screen(twin, flags=[], history=hist)
    
    sf4_flags = [f for f in res.flags if f.flag_id == "SF4"]
    assert len(sf4_flags) == 0


def test_golden_vector_S7a_slow_mobility_review():
    """S7a: steps 1400 (target 2500), previous steps 1300 -> SF5 review"""
    twin = BASE_MEERA.model_copy(deep=True)
    twin.observations.steps = 1400
    hist = [make_history_entry(steps=1300)]
    res = screen(twin, flags=[], history=hist)
    
    sf5_flags = [f for f in res.flags if f.flag_id == "SF5"]
    assert len(sf5_flags) == 1
    assert sf5_flags[0].severity == "review"


def test_golden_vector_S7b_steps_not_consecutive():
    """S7b: steps 1400, previous steps 2400 -> no SF5"""
    twin = BASE_MEERA.model_copy(deep=True)
    twin.observations.steps = 1400
    hist = [make_history_entry(steps=2400)]
    res = screen(twin, flags=[], history=hist)
    
    sf5_flags = [f for f in res.flags if f.flag_id == "SF5"]
    assert len(sf5_flags) == 0


def test_golden_vector_S8_delayed_healing_review():
    """S8: trajectory.overall below_expected now and in previous entry -> SF3 review"""
    twin = BASE_MEERA.model_copy(deep=True)
    twin.trajectory.overall = "below_expected"
    hist = [make_history_entry(overall="below_expected")]
    res = screen(twin, flags=[], history=hist)
    
    sf3_flags = [f for f in res.flags if f.flag_id == "SF3"]
    assert len(sf3_flags) == 1
    assert sf3_flags[0].severity == "review"


# ---------- USER ADDITION #1: READ-ONLY IMMUTABILITY & API ISOLATION ----------

def test_screen_is_readonly_and_does_not_mutate_inputs():
    """Proves screen() does not mutate twin or history objects passed to it."""
    twin_original = BASE_MEERA.model_copy(deep=True)
    hist_original = [make_history_entry(pain=7.5)]
    flags_original = ["wound_discharge", "chest_pain"]

    twin_test = twin_original.model_copy(deep=True)
    hist_test = deepcopy(hist_original)
    flags_test = list(flags_original)

    screen(twin_test, flags=flags_test, history=hist_test)

    assert twin_test.model_dump() == twin_original.model_dump()
    assert hist_test == hist_original
    assert flags_test == flags_original


def test_screening_endpoint_does_not_alter_cycle_result_or_plan():
    """CONTRACTS 12.1 Rule: Screening never changes the plan or the safety result."""
    # Reset to baseline
    client.post("/api/simulator/reset", json={"patient_id": "P001"})

    # Run cycle directly
    res_direct = client.post("/api/patients/P001/cycle", json={})
    data_direct = res_direct.json()

    # Reset again, call GET /screening first, then run cycle
    client.post("/api/simulator/reset", json={"patient_id": "P001"})
    screen_res = client.get("/api/patients/P001/screening")
    assert screen_res.status_code == 200

    res_after_screen = client.post("/api/patients/P001/cycle", json={})
    data_after_screen = res_after_screen.json()

    assert data_direct["safety"] == data_after_screen["safety"]
    assert data_direct["plan"] == data_after_screen["plan"]


# ---------- USER ADDITION #2: RETROACTIVE CURRENT STEP TARGET FOR SF5 ----------

def test_sf5_uses_current_step_target_retroactively_for_historical_readings():
    """CONTRACTS 12.1 SF5 check: Previous history entry must be evaluated against today's target (2500).

    Case: Current Day 4 (step_target = 2500). Current steps = 1400 (56% < 60%).
    Previous Day 1 history entry had steps = 500.
    - If evaluated against Day 1 target (600), 500/600 = 83.3% (NOT < 60%).
    - If evaluated against Day 4 target (2500), 500/2500 = 20.0% (< 60%).
    Correct implementation applies current target (2500) retroactively, triggering SF5.
    """
    twin_day4 = BASE_MEERA.model_copy(deep=True)
    twin_day4.profile.post_op_day = 4  # target = 2500
    twin_day4.observations.steps = 1400  # 1400 / 2500 = 0.56 (< 0.60)

    # Previous reading from Day 1 with 500 steps
    hist_day1_reading = make_history_entry(steps=500)

    res = screen(twin_day4, flags=[], history=[hist_day1_reading])

    sf5_flags = [f for f in res.flags if f.flag_id == "SF5"]
    assert len(sf5_flags) == 1, (
        "SF5 must be triggered when historical steps (500) are evaluated against current target (2500)"
    )
    assert sf5_flags[0].severity == "review"


# ---------- CONSISTENCY & FORBIDDEN WORDING CHECKS ----------

def test_urgent_screening_flag_implies_safety_guardian_escalate():
    """Consistency rule: Whenever any flag has severity urgent, SafetyGuardian.evaluate returns escalate."""
    guardian = SafetyGuardian()

    # Test case 1: Infection urgent (temp 38.2 + wound_discharge)
    twin1 = BASE_MEERA.model_copy(deep=True)
    twin1.observations.temperature = 38.2
    s1_res = screen(twin1, flags=["wound_discharge"])
    assert any(f.severity == "urgent" for f in s1_res.flags)

    safety1 = guardian.evaluate(twin1, proposals=[], draft_plan=None, history=[], flags=["wound_discharge"])
    assert safety1.result == "escalate", f"Expected escalate for urgent infection, got {safety1.result}"

    # Test case 2: Clot urgent (chest_pain)
    twin2 = BASE_MEERA.model_copy(deep=True)
    s2_res = screen(twin2, flags=["chest_pain"])
    assert any(f.severity == "urgent" for f in s2_res.flags)

    safety2 = guardian.evaluate(twin2, proposals=[], draft_plan=None, history=[], flags=["chest_pain"])
    assert safety2.result == "escalate", f"Expected escalate for urgent PE/chest_pain, got {safety2.result}"


def test_all_scenarios_run_through_twin_engine_and_screen():
    """All scenario files run through TwinEngine.update + screen without errors."""
    sim = Simulator()
    scenario_files = [f.stem for f in SCENARIOS_DIR.glob("*.json")]
    assert len(scenario_files) >= 6

    for sc_name in scenario_files:
        sc_data = sim.load(sc_name)
        twin = BASE_MEERA.model_copy(deep=True)
        steps = sc_data.get("steps", [])
        for step in steps:
            obs_dict = step.get("observation", {})
            if obs_dict:
                obs_in = ObservationIn(**obs_dict)
                twin = TwinEngine.update(twin, obs_in)
                flags = obs_in.flags or []
                s_res = screen(twin, flags=flags, history=twin.history)
                assert isinstance(s_res.disclaimer, str)


def test_forbidden_words_in_screening_text():
    """Assert that no flag recommendation/title contains forbidden words: diagnosed, you have, confirmed."""
    forbidden = ["diagnosed", "you have", "confirmed"]
    
    # Test on urgent screening result
    twin = BASE_MEERA.model_copy(deep=True)
    twin.observations.temperature = 38.2
    s_res = screen(twin, flags=["wound_discharge", "chest_pain"])

    for flag in s_res.flags:
        text = f"{flag.title} {flag.recommendation} {' '.join(flag.evidence)}".lower()
        for word in forbidden:
            assert word not in text, f"Forbidden word '{word}' found in screening flag text: {text}"
