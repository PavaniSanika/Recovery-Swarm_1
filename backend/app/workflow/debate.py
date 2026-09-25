"""Debate Engine for RECOVERY-SWARM.

Rule-based stance generation, coalition formation, safety screening, and proposal revision.
"""

import json
import math
from typing import Any, List
from app.agents.safety import SafetyGuardian
from app.config import config
from app.models.schemas import (
    DebateMessage,
    PriorityResult,
    Proposal,
    Stance,
    Strict,
    TwinState,
)


class DebateResult(Strict):
    proposals: List[Proposal]
    stances: List[Stance]
    coalitions: List[List[str]]
    debate_messages: List[DebateMessage]


def round_to_nearest(val: float, nearest: int = 50) -> float:
    return float(int(round(val / float(nearest))) * nearest)


def run_rule_based_debate(
    twin: TwinState,
    proposals: List[Proposal],
    priority_result: PriorityResult,
) -> DebateResult:
    """Executes rule-based agent debate, stance evaluation, safety screening, and proposal revision."""
    guardian = SafetyGuardian()

    debate_messages: List[DebateMessage] = []
    stances: List[Stance] = []
    revised_proposals: List[Proposal] = []

    # Round 1: Initial Proposals & Safety Screening
    vetoed_agents: set[str] = set()

    for p in proposals:
        debate_messages.append(
            DebateMessage(
                round=1,
                agent=p.agent,
                status="Analyzing",
                message=f"{p.agent.capitalize()} proposed {p.action_type} {p.direction}"
                + (f" target {int(p.target_value)}" if p.target_value is not None else "")
                + ".",
                target_agent=None,
            )
        )

        # Call SafetyGuardian.evaluate_proposal from Stage B for R4 veto
        hits = guardian.evaluate_proposal(p, twin)
        if hits:
            vetoed_agents.add(p.agent)
            debate_messages.append(
                DebateMessage(
                    round=1,
                    agent="safety",
                    status="Vetoing",
                    message=hits[0].detail,
                    target_agent=p.agent,
                )
            )

    # Round 2: Stance Generation & Challenging Messages
    for p1 in proposals:
        for p2 in proposals:
            if p1.agent == p2.agent:
                continue

            # Stance logic: opposing aggressive mobility increase when inflammation/sleep/pain high
            if p1.action_type == "mobility" and (p1.direction == "increase" or twin.observations.pain >= 7.0):
                if p2.agent == "sleep":
                    st_kind = "oppose"
                    rev_conf = 0.85
                    if twin.observations.pain >= 7.0:
                        msg = f"Pain is elevated ({twin.observations.pain:.1f}/10); prioritize rest before walking progression."
                    else:
                        msg = f"Sleep quality is low ({twin.scores.sleep_quality:.1f}/10); prioritize rest tonight."
                elif p2.agent == "inflammation":
                    st_kind = "oppose"
                    rev_conf = 0.80
                    msg = f"Inflammation is elevated (swelling {twin.observations.swelling:.1f}/10); hold activity to control swelling."
                elif p2.agent == "medication":
                    st_kind = "oppose"
                    rev_conf = 0.75
                    msg = f"Pain relief timing (pain {twin.observations.pain:.1f}/10) needs review before activity progression."
                else:
                    st_kind = "support"
                    rev_conf = p2.confidence
                    msg = f"Supports the {p1.agent} proposal for {p1.action_type}."
            else:
                st_kind = "support"
                rev_conf = p2.confidence
                msg = f"Supports the {p1.agent} proposal for {p1.action_type}."

            stances.append(
                Stance(
                    agent=p2.agent,
                    target_agent=p1.agent,
                    stance=st_kind,
                    revised_confidence=rev_conf,
                    message=msg,
                )
            )

            # Emit only meaningful Challenge messages to the debate log (no per-pair Supporting spam)
            if st_kind == "oppose":
                debate_messages.append(
                    DebateMessage(
                        round=2,
                        agent=p2.agent,
                        status="Challenging",
                        message=msg,
                        target_agent=p1.agent,
                    )
                )

    # Coalition formation & summary message
    conservative_agents = [
        p.agent
        for p in proposals
        if p.agent in ["sleep", "inflammation", "medication"]
    ]
    coalitions: List[List[str]] = []
    if len(conservative_agents) >= 2:
        coalitions.append(conservative_agents)
        agent_names = ", ".join([a.capitalize() for a in conservative_agents[:-1]]) + f" and {conservative_agents[-1].capitalize()}"
        debate_messages.append(
            DebateMessage(
                round=2,
                agent=conservative_agents[0],
                status="Supporting",
                message=f"{agent_names} agree on a conservative recovery plan.",
                target_agent=None,
            )
        )

    # Round 2 Revision: Revisions based on veto or opposition
    cfg = config.thresholds.get("agents", {}).get("mobility", {})
    boost = float(cfg.get("revised_confidence_boost", 0.12))
    max_conf = float(config.thresholds.get("agents", {}).get("max_confidence", 1.0))

    for p in proposals:
        if p.agent == "mobility" and (p.agent in vetoed_agents or any(s.target_agent == "mobility" and s.stance == "oppose" for s in stances)):
            r4_cap = math.floor(twin.observations.steps * 1.10)
            midpoint = (twin.observations.steps + r4_cap) / 2.0
            revised_target = round_to_nearest(midpoint, 50)
            new_conf = min(max_conf, p.confidence + boost)

            rev_p = Proposal(
                agent=p.agent,
                action_type=p.action_type,
                direction="maintain",
                target_value=revised_target,
                confidence=new_conf,
                evidence=p.evidence,
                rationale="Revised step target to safe conservative level based on swarm feedback and safety limits.",
                risks=p.risks,
            )
            revised_proposals.append(rev_p)

            debate_messages.append(
                DebateMessage(
                    round=2,
                    agent=p.agent,
                    status="Revising",
                    message=f"{p.agent.capitalize()} revised proposal target to {int(revised_target)} steps based on feedback.",
                    target_agent=None,
                )
            )
        else:
            revised_proposals.append(p)

    # Final Approved status messages
    for p in revised_proposals:
        debate_messages.append(
            DebateMessage(
                round=2,
                agent=p.agent,
                status="Approved",
                message=f"{p.agent.capitalize()} proposal approved for draft plan.",
                target_agent=None,
            )
        )

    return DebateResult(
        proposals=revised_proposals,
        stances=stances,
        coalitions=coalitions,
        debate_messages=debate_messages,
    )


class StancesBatch(Strict):
    agent: str
    stances: List[Stance]


STANCE_SYSTEM_PROMPT = """You are a Specialist Agent participating in a multi-agent recovery debate.
Your task is to evaluate proposals from other specialist agents and output a StancesBatch JSON.
Rules:
- For each target proposal, evaluate whether to 'support', 'oppose', or 'revise'.
- Use twin facts and clinical judgment.
- Return JSON strictly matching StancesBatch: agent='{calling_agent}', stances=[Stance(...)].
- Each Stance must have: agent='{calling_agent}', target_agent='...', stance=('support'|'oppose'|'revise'), revised_confidence (float 0..1), message (one short sentence).
"""


def run_llm_debate(
    twin: TwinState,
    proposals: List[Proposal],
    priority_result: PriorityResult,
    fallback: bool = False,
) -> DebateResult:
    """Executes LLM-driven debate round with per-call fallback to rule-based debate."""
    if fallback:
        return run_rule_based_debate(twin, proposals, priority_result)

    from app.agents.base import call_llm_structured
    from app.agents.guardrails import validate_stance_guardrails
    from app.agents.medication import rule_based_medication

    guardian = SafetyGuardian()
    active_agents = [p.agent for p in proposals]
    debate_messages: List[DebateMessage] = []
    stances: List[Stance] = []
    sanitized_proposals: List[Proposal] = []
    vetoed_agents: set[str] = set()

    # Round 1: Safety Screening & R5 Substitution
    for p in proposals:
        debate_messages.append(
            DebateMessage(
                round=1,
                agent=p.agent,
                status="Analyzing",
                message=f"{p.agent.capitalize()} proposed {p.action_type} {p.direction}"
                + (f" target {int(p.target_value)}" if p.target_value is not None else "")
                + ".",
                target_agent=None,
            )
        )

        hits = guardian.evaluate_proposal(p, twin)
        if any(h.rule_id == "R5" for h in hits):
            # Item 7: R5 rejects LLM medication proposal -> record safety event and substitute rule-based proposal
            vetoed_agents.add(p.agent)
            debate_messages.append(
                DebateMessage(
                    round=1,
                    agent="safety",
                    status="Vetoing",
                    message=hits[0].detail + " Substituting safe rule-based proposal.",
                    target_agent=p.agent,
                )
            )
            sub_prop = rule_based_medication(twin)
            sanitized_proposals.append(sub_prop)
        elif hits:
            vetoed_agents.add(p.agent)
            debate_messages.append(
                DebateMessage(
                    round=1,
                    agent="safety",
                    status="Vetoing",
                    message=hits[0].detail,
                    target_agent=p.agent,
                )
            )
            sanitized_proposals.append(p)
        else:
            sanitized_proposals.append(p)

    # Round 2: 4 Specialist Stance Calls (1 call per agent evaluating other proposals)
    for calling_agent in active_agents:
        other_props = [p for p in sanitized_proposals if p.agent != calling_agent]
        if not other_props:
            continue

        system_prompt = STANCE_SYSTEM_PROMPT.format(calling_agent=calling_agent)
        props_summary = json.dumps([p.model_dump() for p in other_props], indent=2)
        user_prompt = f"Patient Twin:\n{twin.model_dump_json(indent=2)}\n\nOther Agent Proposals:\n{props_summary}\n\nGenerate StancesBatch for agent '{calling_agent}'."

        def stance_fallback(t: Any) -> StancesBatch:
            # Rule-based fallback for this agent's stances
            res = run_rule_based_debate(t, sanitized_proposals, priority_result)
            agent_stances = [s for s in res.stances if s.agent == calling_agent]
            return StancesBatch(agent=calling_agent, stances=agent_stances)

        def stance_guardrail(batch: StancesBatch, agent_n: str, t: Any) -> bool:
            if not isinstance(batch, StancesBatch) or batch.agent != agent_n:
                return False
            return all(validate_stance_guardrails(s, agent_n, active_agents) for s in batch.stances)

        batch_result = call_llm_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=StancesBatch,
            fallback_fn=stance_fallback,
            twin=twin,
            agent_name=f"stance_{calling_agent}",
            guardrail_fn=stance_guardrail,
        )

        # Unpack list[Stance] into main stances list per Amendment 3
        stances.extend(batch_result.stances)

        for s in batch_result.stances:
            if s.stance == "oppose":
                debate_messages.append(
                    DebateMessage(
                        round=2,
                        agent=s.agent,
                        status="Challenging",
                        message=s.message,
                        target_agent=s.target_agent,
                    )
                )

    # Coalition formation & summary message
    conservative_agents = [
        p.agent
        for p in sanitized_proposals
        if p.agent in ["sleep", "inflammation", "medication"]
    ]
    coalitions: List[List[str]] = []
    if len(conservative_agents) >= 2:
        coalitions.append(conservative_agents)
        agent_names = ", ".join([a.capitalize() for a in conservative_agents[:-1]]) + f" and {conservative_agents[-1].capitalize()}"
        debate_messages.append(
            DebateMessage(
                round=2,
                agent=conservative_agents[0],
                status="Supporting",
                message=f"{agent_names} agree on a conservative recovery plan.",
                target_agent=None,
            )
        )

    # Round 2 Revision: Deterministic mobility target calculation (Item 6)
    cfg = config.thresholds.get("agents", {}).get("mobility", {})
    boost = float(cfg.get("revised_confidence_boost", 0.12))
    max_conf = float(config.thresholds.get("agents", {}).get("max_confidence", 1.0))
    revised_proposals: List[Proposal] = []

    for p in sanitized_proposals:
        if p.agent == "mobility" and (p.agent in vetoed_agents or any(s.target_agent == "mobility" and s.stance == "oppose" for s in stances)):
            r4_cap = math.floor(twin.observations.steps * 1.10)
            midpoint = (twin.observations.steps + r4_cap) / 2.0
            revised_target = round_to_nearest(midpoint, 50)
            new_conf = min(max_conf, p.confidence + boost)

            rev_p = Proposal(
                agent=p.agent,
                action_type=p.action_type,
                direction="maintain",
                target_value=revised_target,
                confidence=new_conf,
                evidence=p.evidence,
                rationale="Revised step target to safe conservative level based on swarm feedback and safety limits.",
                risks=p.risks,
            )
            revised_proposals.append(rev_p)

            debate_messages.append(
                DebateMessage(
                    round=2,
                    agent=p.agent,
                    status="Revising",
                    message=f"{p.agent.capitalize()} revised proposal target to {int(revised_target)} steps based on feedback.",
                    target_agent=None,
                )
            )
        else:
            revised_proposals.append(p)

    for p in revised_proposals:
        debate_messages.append(
            DebateMessage(
                round=2,
                agent=p.agent,
                status="Approved",
                message=f"{p.agent.capitalize()} proposal approved for draft plan.",
                target_agent=None,
            )
        )

    return DebateResult(
        proposals=revised_proposals,
        stances=stances,
        coalitions=coalitions,
        debate_messages=debate_messages,
    )
