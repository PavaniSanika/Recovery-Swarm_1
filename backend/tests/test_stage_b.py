"""Unit tests for Stage B of RECOVERY-SWARM.

Tests:
1. Golden Vector 9.1 & 9.2: Meera baseline scores and trajectory calculations.
2. Golden Vector 9.3 & Safety Guardian rules R1-R8 (trigger and non-trigger edge cases).
3. R5 forbidden term regex word-boundary precision tests.
4. Typed Deviation Check (run_deviation_check).
5. Running all synthetic scenario files through TwinEngine.update and asserting exact outcomes.
"""

import json
from pathlib import Path
import pytest
from app.agents.safety import SafetyGuardian, check_forbidden_terms
from app.models.schemas import (
    HistoryEntry,
    ObservationIn,
    Proposal,
    TwinState,
)
from app.simulator import Simulator
from app.twin.engine import TwinEngine
from app.workflow.deviation import run_deviation_check

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "scenarios"


@pytest.fixture
def meera_twin() -> TwinState:
    with open(DATA_DIR / "meera_day4.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return TwinState(**data)


@pytest.fixture
def meera_obs_in() -> ObservationIn:
    with open(DATA_DIR / "meera_day4.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    obs = data["observations"]
    obs["timestamp"] = "2026-09-21T08:00:00Z"
    obs["scenario_overrides"] = {
        "medication_effectiveness": 5.5,
        "complication_risk": 3.2,
    }
    return ObservationIn(**obs)


# ---------- Golden Vector 9.1 & 9.2 Tests ----------
def test_golden_vector_9_1_meera_scores_and_trajectory(meera_twin, meera_obs_in):
    """Verify Golden Vector 9.1: Meera baseline scores and trajectory."""
    updated = TwinEngine.update(meera_twin, meera_obs_in)

    # Float tolerances of 0.05
    assert abs(updated.scores.inflammation_score - 6.2) <= 0.05
    assert abs(updated.scores.mobility_capacity - 5.0) <= 0.05
    assert abs(updated.scores.sleep_quality - 3.5) <= 0.05
    assert updated.scores.recovery_score == 68

    # Trajectory assertions
    assert updated.trajectory.overall == "slightly_below_expected"
    assert updated.trajectory.inflammation == "stable_high"
    assert updated.trajectory.mobility == "below_expected"
    assert updated.trajectory.sleep == "poor"


def test_recovery_score_arithmetic(meera_twin, meera_obs_in):
    """Verify Golden Vector 9.2: Recovery Score arithmetic gives 68."""
    updated = TwinEngine.update(meera_twin, meera_obs_in)
    assert updated.scores.recovery_score == 68


# ---------- Safety Guardian R1-R8 & Golden Vector 9.3 Tests ----------
def test_safety_r4_proposal_modification(meera_twin):
    """Proposal mobility target 2200 with steps 1800 -> R4 modify to 1980."""
    guardian = SafetyGuardian()
    proposal = Proposal(
        agent="mobility",
        action_type="mobility",
        direction="increase",
        target_value=2200.0,
        confidence=0.8,
        evidence=["Steps are below target"],
        rationale="Increase walking steps",
        risks=["Minor fatigue"],
    )

    hits = guardian.evaluate_proposal(proposal, meera_twin)
    assert len(hits) == 1
    assert hits[0].rule_id == "R4"
    assert hits[0].outcome == "modify"
    assert "1980" in hits[0].detail


def test_safety_r1_pain_spike(meera_twin):
    """Pain 8.0 -> R1 escalate."""
    guardian = SafetyGuardian()
    twin = meera_twin.model_copy(deep=True)
    twin.observations.pain = 8.0

    res = guardian.evaluate(twin, proposals=[])
    assert res.result == "escalate"
    assert any(r.rule_id == "R1" for r in res.rules_triggered)


def test_safety_r3_fever_and_red_flags(meera_twin):
    """Temperature 38.2 -> R3 escalate."""
    guardian = SafetyGuardian()
    twin = meera_twin.model_copy(deep=True)
    twin.observations.temperature = 38.2

    res = guardian.evaluate(twin, proposals=[])
    assert res.result == "escalate"
    assert any(r.rule_id == "R3" for r in res.rules_triggered)


def test_safety_r8_wound_flags(meera_twin):
    """Flag wound_discharge -> R8 escalate."""
    guardian = SafetyGuardian()
    twin = meera_twin.model_copy(deep=True)
    twin.observations.flags = ["wound_discharge"]

    res = guardian.evaluate(twin, proposals=[])
    assert res.result == "escalate"
    assert any(r.rule_id == "R8" for r in res.rules_triggered)


def test_safety_r5_medication_word_boundaries(meera_twin):
    """R5 word boundary precision: 'clinical review...' allowed, 'increase dose' & invalid action rejected."""
    guardian = SafetyGuardian()

    # Allowed phrase
    allowed_text = "clinical review of pain-management timing"
    assert not check_forbidden_terms(allowed_text)

    # Forbidden term 'increase dose'
    forbidden_text = "Patient requires an increase dose of analgesics"
    assert check_forbidden_terms(forbidden_text)

    # Medication agent with action_type 'mobility' must be blocked
    med_prop = Proposal(
        agent="medication",
        action_type="mobility",
        direction="increase",
        target_value=2000.0,
        confidence=0.8,
        evidence=["Pain control adequate"],
        rationale="Medication agent recommending mobility",
        risks=[],
    )
    hits = guardian.evaluate_proposal(med_prop, meera_twin)
    assert any(h.rule_id == "R5" and h.outcome == "reject" for h in hits)


def test_safety_r6_poor_sleep_high_pain(meera_twin):
    """Sleep 3.5h and pain 7.0 -> R6 modify (capped at current steps)."""
    guardian = SafetyGuardian()
    twin = meera_twin.model_copy(deep=True)
    twin.observations.sleep_hours = 3.5
    twin.observations.pain = 7.0

    res = guardian.evaluate(twin, proposals=[])
    assert res.result == "modify"
    assert any(r.rule_id == "R6" for r in res.rules_triggered)
    assert res.modified_plan is not None
    assert res.modified_plan.steps_target == twin.observations.steps


def test_safety_r2_swelling_slope(meera_twin):
    """Swelling >= 6.0 and rising -> R2 modify (requires >= 2 history entries)."""
    guardian = SafetyGuardian()
    twin = meera_twin.model_copy(deep=True)
    twin.observations.swelling = 6.5

    # No history -> R2 does NOT trigger
    twin.history = []
    res_no_hist = guardian.evaluate(twin, proposals=[])
    assert not any(r.rule_id == "R2" for r in res_no_hist.rules_triggered)

    # With history showing rising swelling -> R2 triggers
    obs_prev = twin.observations.model_copy(deep=True)
    obs_prev.swelling = 5.5
    twin.history = [
        HistoryEntry(
            timestamp="2026-09-21T06:00:00Z",
            observations=obs_prev,
            scores=twin.scores,
            overall="on_track",
        ),
        HistoryEntry(
            timestamp="2026-09-21T07:00:00Z",
            observations=obs_prev,
            scores=twin.scores,
            overall="on_track",
        ),
    ]

    res_hist = guardian.evaluate(twin, proposals=[])
    assert any(r.rule_id == "R2" for r in res_hist.rules_triggered)


def test_safety_meera_baseline_allow(meera_twin):
    """Meera baseline -> allow with no rules triggered."""
    guardian = SafetyGuardian()
    res = guardian.evaluate(meera_twin, proposals=[])
    assert res.result == "allow"
    assert len(res.rules_triggered) == 0


# ---------- Safety Guardian R7 Tests ----------
def test_safety_r7_low_confidence_proposal(meera_twin):
    """(a) Winning proposal with confidence 0.45 -> R7 escalate."""
    guardian = SafetyGuardian()
    proposal = Proposal(
        agent="mobility",
        action_type="mobility",
        direction="maintain",
        target_value=1800.0,
        confidence=0.45,
        evidence=["Patient mobility stable"],
        rationale="Maintain current mobility",
        risks=[],
    )
    res = guardian.evaluate(meera_twin, proposals=[proposal])
    assert res.result == "escalate"
    assert any(r.rule_id == "R7" for r in res.rules_triggered)


def test_safety_r7_sufficient_confidence_proposal(meera_twin):
    """(b) Winning proposal with confidence 0.50 -> no R7."""
    guardian = SafetyGuardian()
    proposal = Proposal(
        agent="mobility",
        action_type="mobility",
        direction="maintain",
        target_value=1800.0,
        confidence=0.50,
        evidence=["Patient mobility stable"],
        rationale="Maintain current mobility",
        risks=[],
    )
    res = guardian.evaluate(meera_twin, proposals=[proposal])
    assert not any(r.rule_id == "R7" for r in res.rules_triggered)
    assert res.result == "allow"


def test_safety_r7_missing_key_data(meera_twin):
    """(c) Missing key data (via missing_fields argument) -> R7 escalate."""
    guardian = SafetyGuardian()
    res = guardian.evaluate(meera_twin, proposals=[], missing_fields=["crp"])
    assert res.result == "escalate"
    assert any(r.rule_id == "R7" for r in res.rules_triggered)


def test_safety_r7_complete_data(meera_twin):
    """(d) Complete data -> no R7."""
    guardian = SafetyGuardian()
    proposal = Proposal(
        agent="mobility",
        action_type="mobility",
        direction="maintain",
        target_value=1800.0,
        confidence=0.80,
        evidence=["Patient mobility stable"],
        rationale="Maintain current mobility",
        risks=[],
    )
    res = guardian.evaluate(meera_twin, proposals=[proposal], missing_fields=None)
    assert not any(r.rule_id == "R7" for r in res.rules_triggered)
    assert res.result == "allow"



# ---------- Scenario Assertion Tests ----------
def test_scenario_outcomes(meera_twin):
    """Assert exact outcomes for all synthetic scenarios."""
    guardian = SafetyGuardian()
    sim = Simulator(scenarios_dir=DATA_DIR)

    # 1. pain_spike: ends with R1 firing (escalate)
    sim.load("pain_spike")
    twin_ps = meera_twin.model_copy(deep=True)
    for _ in range(4):
        obs = sim.advance(60)
        twin_ps = TwinEngine.update(twin_ps, obs)
    res_ps = guardian.evaluate(twin_ps, proposals=[])
    assert res_ps.result == "escalate"
    assert any(r.rule_id == "R1" for r in res_ps.rules_triggered)

    # 2. recovery_deviation: deviation_detected = True AND R1 firing
    sim.load("recovery_deviation")
    twin_rd = meera_twin.model_copy(deep=True)
    for _ in range(3):
        obs = sim.advance(60)
        twin_rd = TwinEngine.update(twin_rd, obs)
    dev_rd = run_deviation_check(twin_rd, flags=twin_rd.observations.flags)
    res_rd = guardian.evaluate(twin_rd, proposals=[], flags=twin_rd.observations.flags)
    assert dev_rd.deviation_detected is True
    assert res_rd.result == "escalate"
    assert any(r.rule_id == "R1" for r in res_rd.rules_triggered)

    # 3. increased_inflammation: R2 fires (modify)
    sim.load("increased_inflammation")
    twin_ii = meera_twin.model_copy(deep=True)
    for _ in range(3):
        obs = sim.advance(60)
        twin_ii = TwinEngine.update(twin_ii, obs)
    res_ii = guardian.evaluate(twin_ii, proposals=[])
    assert any(r.rule_id == "R2" for r in res_ii.rules_triggered)

    # 4. poor_sleep: sleep_quality lowers (< 4.0)
    sim.load("poor_sleep")
    twin_psl = meera_twin.model_copy(deep=True)
    for _ in range(2):
        obs = sim.advance(60)
        twin_psl = TwinEngine.update(twin_psl, obs)
    assert twin_psl.scores.sleep_quality < 4.0

    # 5. stable_recovery: no escalation
    sim.load("stable_recovery")
    twin_sr = meera_twin.model_copy(deep=True)
    for _ in range(4):
        obs = sim.advance(60)
        twin_sr = TwinEngine.update(twin_sr, obs)
    res_sr = guardian.evaluate(twin_sr, proposals=[])
    assert res_sr.result != "escalate"
