"""LangGraph Agent Workflow Engine for RECOVERY-SWARM (Stage C2).

Offline (rule-based) orchestration graph implementing SPEC 15.2 and CONTRACTS.
"""

from copy import deepcopy
import os
import uuid
from typing import Annotated, Any, Dict, List, Literal, Optional, TypedDict

from app.agents.cache import reset_last_run_stats
from app.agents.coordinator import Decision, run_negotiation_coordinator
from app.agents.inflammation import run_inflammation_agent, run_inflammation_agent_llm
from app.agents.medication import run_medication_agent, run_medication_agent_llm
from app.agents.mobility import run_mobility_agent, run_mobility_agent_llm
from app.agents.safety import SafetyGuardian
from app.agents.sleep import run_sleep_agent, run_sleep_agent_llm
from app.config import config
from app.models.schemas import (
    CycleResponse,
    DebateMessage,
    ObservationIn,
    Plan,
    PriorityResult,
    Proposal,
    RuleHit,
    SafetyResult,
    Stance,
    TwinState,
)
from app.twin.engine import TwinEngine
from app.workflow.debate import DebateResult, run_llm_debate, run_rule_based_debate
from app.workflow.deviation import DeviationResult, run_deviation_check
from app.workflow.planner import build_llm_plan, build_plan
from app.workflow.router import run_priority_router
from langgraph.graph import END, START, StateGraph


def merge_r1_proposals(left: list[Proposal], right: list[Proposal]) -> list[Proposal]:
    """Reducer used ONLY by parallel specialist nodes accumulating Round 1 proposals."""
    if not left:
        return list(right)
    if not right:
        return list(left)
    return left + right


class SwarmState(TypedDict):
    patient_id: str
    twin: TwinState
    observation: Optional[ObservationIn]
    is_simulation: bool
    fallback: bool
    deviation_result: Optional[DeviationResult]
    priority_result: Optional[PriorityResult]
    priority_scores: dict[str, float]
    lead_agents: list[str]
    r1_proposals: Annotated[list[Proposal], merge_r1_proposals]
    revised_proposals: list[Proposal]
    proposals: list[Proposal]
    stances: list[Stance]
    coalitions: list[list[str]]
    debate_messages: list[DebateMessage]
    decision: Optional[Decision]
    draft_plan: Optional[Plan]
    safety_result: Optional[SafetyResult]
    retry_count: int
    constraints: dict[str, Any]
    escalated: bool
    final_plan: Optional[Plan]


def is_fallback(state: SwarmState) -> bool:
    if state.get("fallback") is not None:
        return bool(state["fallback"])
    if config.fallback_mode or os.getenv("FALLBACK_MODE", "false").lower() == "true":
        return True
    return False



# ---------- Nodes ----------

def node_ingest(state: SwarmState) -> dict:
    """Workflow component: Validates and stores ObservationIn in state without mutating twin."""
    obs = state.get("observation")
    if obs and not isinstance(obs, ObservationIn):
        obs = ObservationIn(**obs)
    return {"observation": obs}


def node_twin_builder(state: SwarmState) -> dict:
    """Twin Builder Agent (1 of 7 agents): Updates TwinState using TwinEngine if observation exists."""
    twin = state["twin"]
    obs = state.get("observation")
    if obs:
        twin = TwinEngine.update(twin, obs)

    msg = DebateMessage(
        round=1,
        agent="twin_builder",
        status="Analyzing",
        message=f"Digital Twin updated for post-op day {twin.profile.post_op_day} (Recovery score: {twin.scores.recovery_score}).",
        target_agent=None,
    )
    return {
        "twin": twin,
        "debate_messages": state.get("debate_messages", []) + [msg],
    }


def node_deviation_check(state: SwarmState) -> dict:
    """Workflow component: Runs deviation check comparing expected vs actual trends."""
    twin = state["twin"]
    obs_flags = list(twin.observations.flags or [])
    dev_res = run_deviation_check(twin, flags=obs_flags)
    return {"deviation_result": dev_res}


def route_red_flag(state: SwarmState) -> str:
    """Routes to early escalation ONLY for true red-flag clinical signs (chest_pain, breathlessness, calf_pain) or high fever (>= 38.0°C)."""
    twin = state["twin"]
    flags = set(twin.observations.flags or [])
    red_flag_signs = {
        "chest_pain",
        "breathlessness",
        "calf_pain",
    }
    has_red_sign = bool(flags.intersection(red_flag_signs))
    has_fever = twin.observations.temperature >= 38.0

    if has_red_sign or has_fever:
        return "red_flag"
    return "normal"


def node_early_escalate(state: SwarmState) -> dict:
    """Early escalation path for true red-flag signs (R3/R8 triggers)."""
    twin = state["twin"]
    guardian = SafetyGuardian()
    s_res = guardian.evaluate(twin=twin, proposals=[], flags=twin.observations.flags)

    safety_msg = DebateMessage(
        round=1,
        agent="safety",
        status="Vetoing",
        message=f"Critical red flag detected: {', '.join([h.detail for h in s_res.rules_triggered]) or 'Red flag signs'}. Escalating immediately.",
        target_agent=None,
    )
    return {
        "safety_result": s_res,
        "escalated": True,
        "final_plan": None,
        "debate_messages": state.get("debate_messages", []) + [safety_msg],
    }


def node_priority_router(state: SwarmState) -> dict:
    """Workflow component: Computes priority scores and specialist roles."""
    twin = state["twin"]
    p_res = run_priority_router(twin)
    leads = [a for a, r in p_res.roles.items() if r == "lead"]
    return {
        "priority_result": p_res,
        "priority_scores": p_res.priority_scores,
        "lead_agents": leads,
    }


# Specialist Agent Nodes (4 of the 7 agents)
def node_mobility(state: SwarmState) -> dict:
    if is_fallback(state):
        prop = run_mobility_agent(state["twin"])
    else:
        prop = run_mobility_agent_llm(state["twin"])
    return {"r1_proposals": [prop]}


def node_inflammation(state: SwarmState) -> dict:
    if is_fallback(state):
        prop = run_inflammation_agent(state["twin"])
    else:
        prop = run_inflammation_agent_llm(state["twin"])
    return {"r1_proposals": [prop]}


def node_medication(state: SwarmState) -> dict:
    if is_fallback(state):
        prop = run_medication_agent(state["twin"])
    else:
        prop = run_medication_agent_llm(state["twin"])
    return {"r1_proposals": [prop]}


def node_sleep(state: SwarmState) -> dict:
    if is_fallback(state):
        prop = run_sleep_agent(state["twin"])
    else:
        prop = run_sleep_agent_llm(state["twin"])
    return {"r1_proposals": [prop]}


def node_debate_round(state: SwarmState) -> dict:
    """Debate Engine: Stance evaluation, safety screening, coalition formation, and proposal revision."""
    twin = state["twin"]
    r1_props = state["r1_proposals"]
    p_res = state["priority_result"]

    if is_fallback(state):
        d_res = run_rule_based_debate(twin, r1_props, p_res)
    else:
        d_res = run_llm_debate(twin, r1_props, p_res)

    new_msgs = list(state.get("debate_messages", [])) + d_res.debate_messages

    return {
        "revised_proposals": d_res.proposals,
        "proposals": d_res.proposals,
        "stances": d_res.stances,
        "coalitions": d_res.coalitions,
        "debate_messages": new_msgs,
    }



def node_coordinator(state: SwarmState) -> dict:
    """Negotiation Coordinator Agent (1 of the 7 agents): Weighted scoring and consensus decision."""
    twin = state["twin"]
    p_res = state["priority_result"]
    props = state["proposals"]
    stances = state["stances"]
    constraints = state.get("constraints", {})

    decision = run_negotiation_coordinator(
        twin=twin,
        priority_result=p_res,
        proposals=props,
        stances=stances,
        constraints=constraints if constraints else None,
    )
    draft_p = build_plan(decision, priority_result=p_res)

    coord_msg = DebateMessage(
        round=2,
        agent="coordinator",
        status="Approved",
        message=f"Coordinator decision reached (steps target: {decision.steps_target}).",
        target_agent=None,
    )
    new_msgs = list(state.get("debate_messages", [])) + [coord_msg]
    return {
        "decision": decision,
        "draft_plan": draft_p,
        "debate_messages": new_msgs,
    }


def node_safety_guardian(state: SwarmState) -> dict:
    """Risk & Safety Guardian Agent (1 of the 7 agents): Evaluates rules R1-R8 deterministically."""
    twin = state["twin"]
    props = state["proposals"]
    draft_p = state.get("draft_plan")
    retry_cnt = state.get("retry_count", 0)
    guardian = SafetyGuardian()

    s_res = guardian.evaluate(
        twin=twin,
        proposals=props,
        draft_plan=draft_p,
        history=twin.history,
        flags=twin.observations.flags,
    )

    new_retry_count = retry_cnt
    constraints = dict(state.get("constraints", {}))

    if s_res.result == "reject":
        new_retry_count += 1
        constraints["max_steps_target"] = twin.observations.steps

        if new_retry_count > 2:
            # Max 2 retry loops reached -> escalate
            retry_hit = RuleHit(
                rule_id="R_RETRY_LIMIT",
                outcome="escalate",
                detail="Safety retry limit (2 rounds) reached following repeated proposal rejection. Escalating to clinician.",
            )
            s_res = s_res.model_copy(
                update={
                    "result": "escalate",
                    "rules_triggered": s_res.rules_triggered + [retry_hit],
                }
            )

    status = (
        "Approved"
        if s_res.result == "allow"
        else ("Vetoing" if s_res.result in ["reject", "escalate"] else "Revising")
    )
    safety_msg = DebateMessage(
        round=2,
        agent="safety",
        status=status,
        message=f"Safety evaluation result: '{s_res.result}'. Triggered rules: {[r.rule_id for r in s_res.rules_triggered] or 'None'}.",
        target_agent=None,
    )

    new_msgs = list(state.get("debate_messages", [])) + [safety_msg]
    return {
        "safety_result": s_res,
        "retry_count": new_retry_count,
        "constraints": constraints,
        "debate_messages": new_msgs,
    }


def route_after_safety(state: SwarmState) -> str:
    """Routes after safety evaluation: 'ok' (plan generator), 'retry' (coordinator), or 'escalate' (persist)."""
    s_res = state.get("safety_result")
    if not s_res:
        return "ok"

    if s_res.result in ["allow", "modify"]:
        return "ok"
    elif s_res.result == "reject":
        return "retry"
    else:
        return "escalate"


def node_plan_generator(state: SwarmState) -> dict:
    """Workflow component: Builds final user-facing plan from decision and safety result."""
    s_res = state.get("safety_result")
    decision = state.get("decision")
    p_res = state.get("priority_result")

    if s_res and s_res.result == "modify" and s_res.modified_plan:
        final_plan = s_res.modified_plan
    elif decision:
        if is_fallback(state):
            final_plan = build_plan(decision, safety_result=s_res, priority_result=p_res)
        else:
            final_plan = build_llm_plan(decision, safety_result=s_res, priority_result=p_res, twin=state["twin"])
    else:
        final_plan = None

    return {
        "final_plan": final_plan,
        "escalated": False,
    }


def node_persist(state: SwarmState) -> dict:
    """Workflow component: Persistence stub. Ensures escalated flag and final plan consistency."""
    s_res = state.get("safety_result")
    escalated = state.get("escalated", False)
    final_plan = state.get("final_plan")

    if s_res and s_res.result == "escalate":
        escalated = True
        final_plan = None

    return {
        "escalated": escalated,
        "final_plan": final_plan,
    }


# ---------- Graph Construction ----------

def create_swarm_graph():
    g = StateGraph(SwarmState)
    g.add_node("ingest", node_ingest)
    g.add_node("twin_builder", node_twin_builder)
    g.add_node("deviation_check", node_deviation_check)
    g.add_node("early_escalate", node_early_escalate)
    g.add_node("priority_router", node_priority_router)
    g.add_node("mobility", node_mobility)
    g.add_node("inflammation", node_inflammation)
    g.add_node("medication", node_medication)
    g.add_node("sleep", node_sleep)
    g.add_node("debate_round", node_debate_round)
    g.add_node("coordinator", node_coordinator)
    g.add_node("safety_guardian", node_safety_guardian)
    g.add_node("plan_generator", node_plan_generator)
    g.add_node("persist", node_persist)

    g.add_edge(START, "ingest")
    g.add_edge("ingest", "twin_builder")
    g.add_edge("twin_builder", "deviation_check")
    g.add_conditional_edges(
        "deviation_check",
        route_red_flag,
        {"red_flag": "early_escalate", "normal": "priority_router"},
    )
    g.add_edge("early_escalate", "persist")

    for spec in ["mobility", "inflammation", "medication", "sleep"]:
        g.add_edge("priority_router", spec)
        g.add_edge(spec, "debate_round")

    g.add_edge("debate_round", "coordinator")
    g.add_edge("coordinator", "safety_guardian")
    g.add_conditional_edges(
        "safety_guardian",
        route_after_safety,
        {"ok": "plan_generator", "retry": "coordinator", "escalate": "persist"},
    )
    g.add_edge("plan_generator", "persist")
    g.add_edge("persist", END)

    return g.compile()


swarm_graph = create_swarm_graph()


# ---------- Public API ----------

def persist_cycle_data(final_state: dict, cycle_id: str):
    """Persists only the final cycle decision and related rows after retries to the database."""
    from datetime import datetime, timezone
    from app.db import (
        SessionLocal,
        TwinStateModel,
        DecisionModel,
        AgentProposalModel,
        DebateMessageModel,
        SafetyEventModel,
        RecoveryPlanModel,
    )
    db = SessionLocal()
    try:
        twin = final_state["twin"]
        timestamp_str = datetime.now(timezone.utc).isoformat()

        # 1. Twin state row
        state_row = TwinStateModel(
            patient_id=twin.patient_id,
            timestamp=timestamp_str,
            twin_json=twin.model_dump(),
            recovery_score=twin.scores.recovery_score,
            trajectory_overall=twin.trajectory.overall,
        )
        db.add(state_row)
        db.flush()

        # 2. Final Decision row
        p_res = final_state.get("priority_result")
        safety_res = final_state.get("safety_result")
        escalated = final_state.get("escalated", False)
        final_plan = final_state.get("final_plan")

        decision_row = DecisionModel(
            cycle_id=cycle_id,
            patient_id=twin.patient_id,
            state_id=state_row.state_id,
            priority_scores=p_res.priority_scores if p_res else {},
            lead_agents=[a for a, r in (p_res.roles.items() if p_res else {}) if r == "lead"],
            coalitions=final_state.get("coalitions", []),
            draft_plan=final_plan.model_dump() if final_plan else None,
            safety_result=safety_res.result if safety_res else "allow",
            escalated=escalated,
            created_at=timestamp_str,
        )
        db.add(decision_row)

        # 3. Final Agent Proposals
        for p in final_state.get("proposals", []):
            prop_row = AgentProposalModel(
                cycle_id=cycle_id,
                agent=p.agent,
                action_type=p.action_type,
                direction=p.direction,
                target_value=p.target_value,
                confidence=p.confidence,
                evidence=p.evidence,
                rationale=p.rationale,
                risks=p.risks,
                round=1,
            )
            db.add(prop_row)

        # 4. Debate messages
        for msg in final_state.get("debate_messages", []):
            msg_row = DebateMessageModel(
                cycle_id=cycle_id,
                round=msg.round,
                agent=msg.agent,
                status=msg.status,
                message=msg.message,
                target_agent=msg.target_agent,
                revised_confidence=None,
            )
            db.add(msg_row)

        # 5. Safety events
        if safety_res and safety_res.rules_triggered:
            for r in safety_res.rules_triggered:
                event_row = SafetyEventModel(
                    cycle_id=cycle_id,
                    rule_id=r.rule_id,
                    outcome=r.outcome,
                    detail=r.detail,
                    timestamp=timestamp_str,
                )
                db.add(event_row)
        else:
            event_row = SafetyEventModel(
                cycle_id=cycle_id,
                rule_id="R_ALLOW",
                outcome="allow",
                detail="No safety rules triggered.",
                timestamp=timestamp_str,
            )
            db.add(event_row)

        # 6. Recovery plan row
        if final_plan:
            plan_row = RecoveryPlanModel(
                cycle_id=cycle_id,
                horizon_hours=final_plan.horizon_hours,
                plan_json=final_plan.model_dump(),
                priorities={"high": [item.model_dump() for item in final_plan.high_priority], "medium": [item.model_dump() for item in final_plan.medium_priority]},
                monitoring=final_plan.monitoring,
                next_reassessment=final_plan.next_reassessment,
                score_change=final_plan.expected_score_change,
            )
            db.add(plan_row)

        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def run_cycle(
    twin: TwinState,
    observation: Optional[ObservationIn] = None,
    fallback: bool = True,
    is_simulation: bool = False,
) -> CycleResponse:
    """Executes a full recovery optimization cycle through the LangGraph workflow.
    
    Returns a validated CycleResponse.
    Never mutates the input twin object.
    """
    reset_last_run_stats()

    # Deep copy input twin so input object is NEVER mutated
    twin_copy = twin.model_copy(deep=True)

    initial_state: SwarmState = {
        "patient_id": twin_copy.patient_id,
        "twin": twin_copy,
        "observation": observation,
        "is_simulation": is_simulation,
        "fallback": fallback,
        "deviation_result": None,
        "priority_result": None,
        "priority_scores": {},
        "lead_agents": [],
        "r1_proposals": [],
        "revised_proposals": [],
        "proposals": [],
        "stances": [],
        "coalitions": [],
        "debate_messages": [],
        "decision": None,
        "draft_plan": None,
        "safety_result": None,
        "retry_count": 0,
        "constraints": {},
        "escalated": False,
        "final_plan": None,
    }

    final_state = swarm_graph.invoke(initial_state)

    cycle_id = f"cycle_{uuid.uuid4().hex[:8]}"

    # Construct CycleResponse
    response = CycleResponse(
        cycle_id=cycle_id,
        priority=final_state["priority_result"]
        or PriorityResult(
            priority_scores={"mobility": 0.5, "inflammation": 0.5, "medication": 0.5, "sleep": 0.5},
            roles={"mobility": "supporting", "inflammation": "supporting", "medication": "supporting", "sleep": "supporting"},
        ),
        proposals=final_state.get("proposals") or [],
        stances=final_state.get("stances") or [],
        coalitions=final_state.get("coalitions") or [],
        debate=final_state.get("debate_messages") or [],
        safety=final_state["safety_result"]
        or SafetyResult(result="allow", rules_triggered=[], modified_plan=None),
        plan=final_state.get("final_plan"),
        escalated=final_state.get("escalated", False),
        twin=final_state["twin"],
    )

    # Persist non-simulation runs to DB (only final decision after retries)
    if not is_simulation:
        persist_cycle_data(final_state, cycle_id)

    return response


async def astream_cycle(
    twin: TwinState,
    observation: Optional[ObservationIn] = None,
    fallback: bool = True,
    is_simulation: bool = False,
):
    """Async generator that streams LangGraph node completion events in real time as nodes execute."""
    reset_last_run_stats()
    twin_copy = twin.model_copy(deep=True)

    initial_state: SwarmState = {
        "patient_id": twin_copy.patient_id,
        "twin": twin_copy,
        "observation": observation,
        "is_simulation": is_simulation,
        "fallback": fallback,
        "deviation_result": None,
        "priority_result": None,
        "priority_scores": {},
        "lead_agents": [],
        "r1_proposals": [],
        "revised_proposals": [],
        "proposals": [],
        "stances": [],
        "coalitions": [],
        "debate_messages": [],
        "decision": None,
        "draft_plan": None,
        "safety_result": None,
        "retry_count": 0,
        "constraints": {},
        "escalated": False,
        "final_plan": None,
    }

    cycle_id = f"cycle_{uuid.uuid4().hex[:8]}"

    async for step in swarm_graph.astream(initial_state, stream_mode="updates"):
        yield cycle_id, step



