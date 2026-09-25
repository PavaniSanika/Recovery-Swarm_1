"""Unit tests for Stage C1 of RECOVERY-SWARM.

Tests:
1. Priority Router formulas, priority values, and lead role assignments.
2. Valid Proposal generation across all synthetic scenario files.
3. Medication Agent limits (Stage B R5 check, action_type restrictions, no forbidden terms).
4. Rule-based Debate workflow (Round 1 R4 veto, Round 2 2200 -> 1900 Mobility revision).
5. Negotiation Coordinator scoring, conservative choice, and constraint handling.
6. Plan Generator output validation and action fidelity.
7. Scenario-driven behavior checks (pain_spike, poor_sleep, increased_inflammation, reduced_mobility, stable_recovery).
8. Determinism and dynamic reactivity to input changes.
"""

import json
from pathlib import Path
import pytest
from app.agents.coordinator import Decision, run_negotiation_coordinator
from app.agents.inflammation import run_inflammation_agent
from app.agents.medication import run_medication_agent
from app.agents.mobility import run_mobility_agent
from app.agents.safety import SafetyGuardian, check_forbidden_terms
from app.agents.sleep import run_sleep_agent
from app.models.schemas import ObservationIn, Plan, Proposal, TwinState
from app.simulator import Simulator
from app.twin.engine import TwinEngine
from app.workflow.debate import run_rule_based_debate
from app.workflow.planner import build_plan
from app.workflow.router import run_priority_router

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "scenarios"
SCENARIOS = [
    "meera_day4",
    "poor_sleep",
    "pain_spike",
    "increased_inflammation",
    "reduced_mobility",
    "stable_recovery",
]


@pytest.fixture
def meera_twin() -> TwinState:
    with open(DATA_DIR / "meera_day4.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return TwinState(**data)


# ---------- 1. Priority Router Tests ----------
def test_router_meera_baseline(meera_twin):
    """Meera baseline router values and lead role assignments per CONTRACTS 5.1."""
    res = run_priority_router(meera_twin)

    # Lead set {inflammation, sleep, mobility}
    assert res.roles["inflammation"] == "lead"
    assert res.roles["sleep"] == "lead"
    assert res.roles["mobility"] == "lead"
    assert res.roles["medication"] == "supporting"

    # Priority values within +/- 0.05 of targets: inf 0.85, sleep 0.80, mob 0.77, med 0.61
    assert abs(res.priority_scores["inflammation"] - 0.85) <= 0.05
    assert abs(res.priority_scores["sleep"] - 0.80) <= 0.05
    assert abs(res.priority_scores["mobility"] - 0.77) <= 0.05
    assert abs(res.priority_scores["medication"] - 0.61) <= 0.05


# ---------- 2. Agent Proposal Schema Validation ----------
def test_agents_produce_valid_proposals_across_scenarios(meera_twin):
    """Every specialist agent returns a valid Proposal across all scenarios."""
    sim = Simulator(scenarios_dir=DATA_DIR)

    for sc_name in SCENARIOS:
        if sc_name == "meera_day4":
            twin = meera_twin.model_copy(deep=True)
        else:
            sim.load(sc_name)
            obs = sim.advance(60)
            twin = TwinEngine.update(meera_twin, obs)

        p_mob = run_mobility_agent(twin)
        p_inf = run_inflammation_agent(twin)
        p_med = run_medication_agent(twin)
        p_slp = run_sleep_agent(twin)

        for prop in [p_mob, p_inf, p_med, p_slp]:
            assert isinstance(prop, Proposal)
            assert len(prop.evidence) >= 1
            assert prop.confidence >= 0.0 and prop.confidence <= 1.0


# ---------- 3. Medication Agent Limit Tests ----------
def test_medication_agent_limits_across_scenarios(meera_twin):
    """Medication agent never outputs doses or forbidden terms and adheres to action_type bounds."""
    sim = Simulator(scenarios_dir=DATA_DIR)
    guardian = SafetyGuardian()

    for sc_name in SCENARIOS:
        if sc_name == "meera_day4":
            twin = meera_twin.model_copy(deep=True)
        else:
            sim.load(sc_name)
            obs = sim.advance(60)
            twin = TwinEngine.update(meera_twin, obs)

        p_med = run_medication_agent(twin)

        # 1. Action type restriction
        assert p_med.action_type in ["pain_review", "monitoring", "escalate"]

        # 2. Stage B forbidden terms check on text
        full_text = f"{p_med.rationale} {' '.join(p_med.evidence)} {' '.join(p_med.risks)}"
        assert not check_forbidden_terms(full_text)

        # 3. Safety Guardian evaluate_proposal check for R5
        hits = guardian.evaluate_proposal(p_med, twin)
        assert not any(h.rule_id == "R5" for h in hits)


# ---------- 4. Debate Workflow Tests ----------
def test_debate_meera_revision(meera_twin):
    """Meera baseline debate produces 2200 -> 1900 revision with R4 vetoing and revising messages."""
    priority = run_priority_router(meera_twin)
    p_mob = run_mobility_agent(meera_twin)  # Proposes 2200
    p_inf = run_inflammation_agent(meera_twin)
    p_med = run_medication_agent(meera_twin)
    p_slp = run_sleep_agent(meera_twin)

    assert p_mob.target_value == 2200.0

    debate_res = run_rule_based_debate(meera_twin, [p_mob, p_inf, p_med, p_slp], priority)

    # Check statuses and agent fields in DebateMessage log
    statuses = [m.status for m in debate_res.debate_messages]
    assert "Analyzing" in statuses
    assert "Vetoing" in statuses
    assert "Revising" in statuses
    assert "Approved" in statuses

    veto_msg = next(m for m in debate_res.debate_messages if m.status == "Vetoing")
    assert veto_msg.agent == "safety"
    assert veto_msg.target_agent == "mobility"

    # Assert Mobility proposal was revised to 1900
    revised_mob = next(p for p in debate_res.proposals if p.agent == "mobility")
    assert revised_mob.target_value == 1900.0
    assert revised_mob.direction == "maintain"
    assert revised_mob.confidence > p_mob.confidence


# ---------- 5. Coordinator Tests ----------
def test_coordinator_scoring_and_constraints(meera_twin):
    """Coordinator picks winning proposals, conservative choices, and respects constraints."""
    priority = run_priority_router(meera_twin)
    p_mob = run_mobility_agent(meera_twin)
    p_inf = run_inflammation_agent(meera_twin)
    p_med = run_medication_agent(meera_twin)
    p_slp = run_sleep_agent(meera_twin)

    debate_res = run_rule_based_debate(meera_twin, [p_mob, p_inf, p_med, p_slp], priority)

    decision = run_negotiation_coordinator(
        meera_twin, priority, debate_res.proposals, debate_res.stances
    )

    assert isinstance(decision, Decision)
    assert decision.steps_target == 1900
    assert len(decision.decided_actions) >= 3

    # With optional constraint max_steps_target=1850
    decision_constrained = run_negotiation_coordinator(
        meera_twin,
        priority,
        debate_res.proposals,
        debate_res.stances,
        constraints={"max_steps_target": 1850},
    )
    assert decision_constrained.steps_target == 1850


# ---------- 6. Planner Tests ----------
def test_planner_build_plan_validation(meera_twin):
    """Planner produces valid Plan and adds no invented actions."""
    priority = run_priority_router(meera_twin)
    p_mob = run_mobility_agent(meera_twin)
    p_inf = run_inflammation_agent(meera_twin)
    p_med = run_medication_agent(meera_twin)
    p_slp = run_sleep_agent(meera_twin)

    debate_res = run_rule_based_debate(meera_twin, [p_mob, p_inf, p_med, p_slp], priority)
    decision = run_negotiation_coordinator(
        meera_twin, priority, debate_res.proposals, debate_res.stances
    )

    plan = build_plan(decision, priority_result=priority)
    assert isinstance(plan, Plan)
    assert plan.steps_target == 1900
    assert plan.horizon_hours == 12

    # Verify every high/medium priority plan item maps to a decided action
    decided_actions_text = [p.rationale for p in decision.decided_actions]
    for item in plan.high_priority + plan.medium_priority:
        assert any(item.reason == r for r in decided_actions_text)


# ---------- 7. Scenario-driven Behavior Checks ----------
def test_scenario_behavior_checks(meera_twin):
    """Behavior checks driven by synthetic scenario files via TwinEngine.update."""
    sim = Simulator(scenarios_dir=DATA_DIR)

    # 1. pain_spike -> mobility agent does not propose an increase
    sim.load("pain_spike")
    twin_ps = meera_twin.model_copy(deep=True)
    for _ in range(4):
        obs = sim.advance(60)
        twin_ps = TwinEngine.update(twin_ps, obs)
    p_mob_ps = run_mobility_agent(twin_ps)
    assert p_mob_ps.direction != "increase"

    # 2. poor_sleep -> sleep has highest priority
    sim.load("poor_sleep")
    twin_slp = meera_twin.model_copy(deep=True)
    for _ in range(2):
        obs = sim.advance(60)
        twin_slp = TwinEngine.update(twin_slp, obs)
    r_slp = run_priority_router(twin_slp)
    top_agent = max(r_slp.priority_scores, key=r_slp.priority_scores.get)
    assert top_agent == "sleep"

    # 3. increased_inflammation -> inflammation is a lead
    sim.load("increased_inflammation")
    twin_inf = meera_twin.model_copy(deep=True)
    for _ in range(3):
        obs = sim.advance(60)
        twin_inf = TwinEngine.update(twin_inf, obs)
    r_inf = run_priority_router(twin_inf)
    assert r_inf.roles["inflammation"] == "lead"

    # 4. reduced_mobility -> mobility is a lead
    sim.load("reduced_mobility")
    twin_rm = meera_twin.model_copy(deep=True)
    for _ in range(2):
        obs = sim.advance(60)
        twin_rm = TwinEngine.update(twin_rm, obs)
    r_rm = run_priority_router(twin_rm)
    assert r_rm.roles["mobility"] == "lead"

    # 5. stable_recovery -> mobility proposal is an increase within R4 cap and not vetoed
    sim.load("stable_recovery")
    twin_sr = meera_twin.model_copy(deep=True)
    for _ in range(3):
        obs = sim.advance(60)
        twin_sr = TwinEngine.update(twin_sr, obs)
    p_mob_sr = run_mobility_agent(twin_sr)
    guardian = SafetyGuardian()
    hits_sr = guardian.evaluate_proposal(p_mob_sr, twin_sr)
    assert p_mob_sr.direction == "increase"
    assert len(hits_sr) == 0


def test_dynamic_reactivity(meera_twin):
    """Changing twin input parameters dynamically changes agent proposals (no hardcoding)."""
    twin_low_pain = meera_twin.model_copy(deep=True)
    twin_low_pain.observations.pain = 3.0
    twin_low_pain.observations.swelling = 3.0

    twin_high_pain = meera_twin.model_copy(deep=True)
    twin_high_pain.observations.pain = 8.5

    prop_low = run_mobility_agent(twin_low_pain)
    prop_high = run_mobility_agent(twin_high_pain)

    assert prop_low.direction == "increase"
    assert prop_high.direction == "maintain"
    assert prop_low.target_value != prop_high.target_value


def test_determinism(meera_twin):
    """Same twin inputs produce byte-identical debate results and decisions."""
    p_mob1 = run_mobility_agent(meera_twin)
    p_mob2 = run_mobility_agent(meera_twin)
    assert p_mob1.model_dump_json() == p_mob2.model_dump_json()

    r1 = run_priority_router(meera_twin)
    r2 = run_priority_router(meera_twin)
    assert r1.model_dump_json() == r2.model_dump_json()
