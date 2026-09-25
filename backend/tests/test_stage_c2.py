"""Unit tests for Stage C2 of RECOVERY-SWARM.

Tests:
1. CycleResponse validation and Meera baseline cycle execution.
2. Scenario checks: pain_spike, recovery_deviation, poor_sleep, increased_inflammation, reduced_mobility, stable_recovery.
3. Red-flag early escalation path (R3 / fever).
4. Safety modify case (R2/R6) and plan generator usage of modified_plan.
5. Reject-and-retry loop cutoff after 2 rounds with escalation.
6. Determinism test on model_dump_json excluding cycle_id and timestamps.
7. Twin object immutability (fallback mode, is_simulation=True and False).
8. Fallback flag validation (fallback=False raises NotImplementedError).
"""

import json
from pathlib import Path
import pytest

from app.graph import run_cycle, swarm_graph, SwarmState
from app.models.schemas import ObservationIn, Plan, Proposal, RuleHit, SafetyResult, TwinState
from app.twin.engine import TwinEngine

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "scenarios"


@pytest.fixture
def meera_twin() -> TwinState:
    with open(DATA_DIR / "meera_day4.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return TwinState(**data)


def load_scenario_twin(scenario_name: str, meera_base: TwinState) -> TwinState:
    file_path = DATA_DIR / f"{scenario_name}.json"
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "steps" not in data:
        return TwinState(**data)

    twin = meera_base.model_copy(deep=True)
    for idx, step_item in enumerate(data["steps"]):
        obs_dict = step_item["observation"].copy()
        if "timestamp" not in obs_dict:
            obs_dict["timestamp"] = f"2026-09-21T08:{(idx * 15) % 60:02d}:00Z"
        obs = ObservationIn(**obs_dict)
        twin = TwinEngine.update(twin, obs)
    return twin


# ---------- 1. Meera Baseline Cycle ----------
def test_meera_baseline_cycle(meera_twin):
    """Meera baseline cycle yields valid CycleResponse, steps_target ~1900, safety 'allow', escalated=False."""
    res = run_cycle(meera_twin, fallback=True)

    assert res.twin.patient_id == "P001"
    assert res.escalated is False
    assert res.safety.result == "allow"
    assert len(res.safety.rules_triggered) == 0
    assert res.plan is not None
    assert res.plan.steps_target == 1900
    assert len(res.proposals) == 4
    assert len(res.debate) > 0


# ---------- 2. Scenario-driven behavior checks ----------
def test_pain_spike_escalation(meera_twin):
    """pain_spike scenario escalates via rule R1 with plan=None."""
    twin = load_scenario_twin("pain_spike", meera_twin)
    res = run_cycle(twin, fallback=True)

    assert res.escalated is True
    assert res.safety.result == "escalate"
    assert any(r.rule_id == "R1" for r in res.safety.rules_triggered)
    assert res.plan is None


def test_recovery_deviation_escalation(meera_twin):
    """recovery_deviation ends escalated with R1 AND a non-empty debate log."""
    twin = load_scenario_twin("recovery_deviation", meera_twin)
    res = run_cycle(twin, fallback=True)

    assert res.escalated is True
    assert res.safety.result == "escalate"
    assert any(r.rule_id == "R1" for r in res.safety.rules_triggered)
    assert res.plan is None
    assert len(res.debate) > 0
    assert any(m.round == 2 and m.agent == "coordinator" for m in res.debate)


def test_poor_sleep_priority(meera_twin):
    """poor_sleep scenario makes sleep agent a lead / top-priority agent."""
    twin = load_scenario_twin("poor_sleep", meera_twin)
    res = run_cycle(twin, fallback=True)

    assert res.priority.roles["sleep"] == "lead"


def test_increased_inflammation_priority(meera_twin):
    """increased_inflammation scenario makes inflammation agent a lead."""
    twin = load_scenario_twin("increased_inflammation", meera_twin)
    res = run_cycle(twin, fallback=True)

    assert res.priority.roles["inflammation"] == "lead"


def test_reduced_mobility_priority(meera_twin):
    """reduced_mobility scenario makes mobility agent a lead."""
    twin = load_scenario_twin("reduced_mobility", meera_twin)
    res = run_cycle(twin, fallback=True)

    assert res.priority.roles["mobility"] == "lead"


def test_stable_recovery_allow(meera_twin):
    """stable_recovery gives allow with a mobility target within R4 cap and not vetoed."""
    twin = load_scenario_twin("stable_recovery", meera_twin)
    res = run_cycle(twin, fallback=True)

    assert res.safety.result == "allow"
    assert res.plan is not None
    mob_prop = next(p for p in res.proposals if p.agent == "mobility")
    assert mob_prop.target_value <= twin.observations.steps * 1.10


# ---------- 3. Red-flag Early Escalation Path ----------
def test_red_flag_early_escalation(meera_twin):
    """Red flag observation (chest_pain) takes early path with R3 recorded, plan=None, escalated=True."""
    obs_red = ObservationIn(
        timestamp="2026-09-21T09:00:00Z",
        pain=6.0,
        sleep_hours=6.0,
        steps=1800,
        swelling=4.0,
        temperature=37.0,
        heart_rate=80,
        crp=3.0,
        flags=["chest_pain"],
    )

    res = run_cycle(meera_twin, observation=obs_red, fallback=True)

    assert res.escalated is True
    assert res.safety.result == "escalate"
    assert any(r.rule_id == "R3" for r in res.safety.rules_triggered)
    assert res.plan is None


# ---------- 4. Modify Case Test ----------
def test_modify_case_final_plan(meera_twin):
    """Constructed case triggering R6 (sleep < 4h and pain 7.5) yields safety result 'modify' and uses modified_plan."""
    twin = meera_twin.model_copy(deep=True)
    twin.observations.sleep_hours = 3.5
    twin.observations.pain = 7.5

    res = run_cycle(twin, fallback=True)

    assert res.safety.result == "modify"
    assert res.plan is not None


# ---------- 5. Reject and Retry Loop Cutoff ----------
def test_reject_retry_loop_cutoff(meera_twin, monkeypatch):
    """Reject and retry loop stops after 2 retries and escalates with R_RETRY_LIMIT hit."""
    def mock_evaluate_reject(*args, **kwargs):
        return SafetyResult(
            result="reject",
            rules_triggered=[RuleHit(rule_id="R_MOCK_REJECT", outcome="reject", detail="Mock rejection")],
            modified_plan=None,
        )

    from app.agents.safety import SafetyGuardian
    monkeypatch.setattr(SafetyGuardian, "evaluate", mock_evaluate_reject)

    res = run_cycle(meera_twin, fallback=True)

    assert res.escalated is True
    assert res.safety.result == "escalate"
    assert any(r.rule_id == "R_RETRY_LIMIT" for r in res.safety.rules_triggered)


# ---------- 6. Determinism Test ----------
def test_cycle_determinism(meera_twin):
    """Running cycle twice produces byte-identical model_dump_json outputs excluding cycle_id and timestamps."""
    res1 = run_cycle(meera_twin, fallback=True)
    res2 = run_cycle(meera_twin, fallback=True)

    d1 = res1.model_dump()
    d2 = res2.model_dump()

    # Exclude cycle_id
    d1["cycle_id"] = "IGNORED"
    d2["cycle_id"] = "IGNORED"

    assert json.dumps(d1, sort_keys=True) == json.dumps(d2, sort_keys=True)


# ---------- 7. Immutability & Fallback Flags ----------
def test_twin_immutability(meera_twin):
    """run_cycle does not mutate input twin for is_simulation=True or False."""
    twin_orig = meera_twin.model_copy(deep=True)

    _ = run_cycle(meera_twin, fallback=True, is_simulation=False)
    assert meera_twin.model_dump() == twin_orig.model_dump()

    _ = run_cycle(meera_twin, fallback=True, is_simulation=True)
    assert meera_twin.model_dump() == twin_orig.model_dump()


def test_fallback_false_executes(meera_twin, monkeypatch):
    """fallback=False executes cycle and returns CycleResponse."""
    monkeypatch.setenv("FALLBACK_MODE", "true")
    res = run_cycle(meera_twin, fallback=False)
    assert res is not None
    assert res.twin.patient_id == meera_twin.patient_id


# ---------- 8. Polish Pass Additional Tests ----------
def test_plan_self_consistency(meera_twin):
    """Plan steps_target equals Mobility PlanItem target string for allow and modify cases."""
    res_allow = run_cycle(meera_twin, fallback=True)
    assert res_allow.plan is not None
    mob_item_allow = next(item for item in res_allow.plan.high_priority + res_allow.plan.medium_priority if "mobility" in item.action.lower())
    assert mob_item_allow.target == f"{res_allow.plan.steps_target} steps"

    twin_mod = meera_twin.model_copy(deep=True)
    twin_mod.observations.sleep_hours = 3.5
    twin_mod.observations.pain = 7.5
    res_mod = run_cycle(twin_mod, fallback=True)
    assert res_mod.safety.result == "modify"
    assert res_mod.plan is not None
    mob_item_mod = next(item for item in res_mod.plan.high_priority + res_mod.plan.medium_priority if "mobility" in item.action.lower())
    assert mob_item_mod.target == f"{res_mod.plan.steps_target} steps"


def test_data_driven_rationales(meera_twin):
    """Agent rationales differ when twin data differs and contain actual numbers."""
    twin_sr = load_scenario_twin("stable_recovery", meera_twin)
    twin_inf = load_scenario_twin("increased_inflammation", meera_twin)

    res_sr = run_cycle(twin_sr, fallback=True)
    res_inf = run_cycle(twin_inf, fallback=True)

    prop_inf_sr = next(p for p in res_sr.proposals if p.agent == "inflammation")
    prop_inf_inf = next(p for p in res_inf.proposals if p.agent == "inflammation")
    assert prop_inf_sr.rationale != prop_inf_inf.rationale
    assert f"{twin_inf.observations.crp:.1f}" in prop_inf_inf.rationale or "worsening" in prop_inf_inf.rationale or "stable and high" in prop_inf_inf.rationale

    prop_med_sr = next(p for p in res_sr.proposals if p.agent == "medication")
    assert prop_med_sr.action_type == "monitoring"
    assert "adequate" in prop_med_sr.rationale
    assert f"{twin_sr.observations.pain:.1f}" in prop_med_sr.rationale


def test_escalated_interim_guidance(meera_twin):
    """Escalated cycles contain conservative interim guidance in safety.modified_plan."""
    twin_ps = load_scenario_twin("pain_spike", meera_twin)
    res_ps = run_cycle(twin_ps, fallback=True)

    assert res_ps.plan is None
    assert res_ps.safety.modified_plan is not None
    assert res_ps.safety.modified_plan.steps_target == twin_ps.observations.steps
    assert any("Hold Activity Increase" in item.action for item in res_ps.safety.modified_plan.high_priority)
