"""Inflammation & Healing Agent for RECOVERY-SWARM.

Rule-based reasoning for inflammation, swelling, and healing trends.
"""

from typing import Any

from app.config import config
from app.models.schemas import Proposal, TwinState


def rule_based_inflammation(twin: TwinState) -> Proposal:
    """Returns rule-based proposal for inflammation."""
    cfg = config.thresholds.get("agents", {}).get("inflammation", {})
    base_confidence = float(cfg.get("base_confidence", 0.80))

    crp = twin.observations.crp
    swelling = twin.observations.swelling
    inf_score = twin.scores.inflammation_score

    evidence = [
        f"CRP index = {crp:.1f}",
        f"Swelling = {swelling:.1f}",
        f"Inflammation score = {inf_score:.1f}",
    ]

    inf_traj = twin.trajectory.inflammation
    high_thresh = float(cfg.get("high_threshold", 6.0))

    if inf_traj == "worsening" or (len(twin.history) >= 1 and twin.observations.crp > twin.history[-1].observations.crp):
        direction = "maintain"
        rationale = f"Inflammation is worsening (CRP {crp:.1f}, swelling {swelling:.1f}/10). Recommend holding activity to control swelling."
        risks = ["Worsening swelling if activity increased too quickly"]
    elif inf_traj == "stable_high" or inf_score >= high_thresh or swelling >= high_thresh or crp >= high_thresh:
        direction = "maintain"
        rationale = f"Inflammation is stable and high (CRP {crp:.1f}, swelling {swelling:.1f}/10, score {inf_score:.1f}). Recommend conservative activity and swelling control."
        risks = ["Worsening swelling if activity increased too quickly"]
    else:
        direction = "maintain"
        rationale = f"Inflammation is improving (CRP {crp:.1f}, swelling {swelling:.1f}/10, score {inf_score:.1f}) within acceptable post-op thresholds."
        risks = ["Re-injury or flare-up upon exertion"]

    return Proposal(
        agent="inflammation",
        action_type="swelling",
        direction=direction,
        target_value=None,
        confidence=base_confidence,
        evidence=evidence,
        rationale=rationale,
        risks=risks,
    )


def run_inflammation_agent(twin: TwinState) -> Proposal:
    """Standard interface for Inflammation Agent."""
    return rule_based_inflammation(twin)


INFLAMMATION_SYSTEM_PROMPT = """You are the Inflammation & Healing Specialist Agent for post-op knee recovery.
Your task is to analyze patient digital twin data and generate a Proposal JSON.
Specialty: Post-surgical inflammation, CRP index, and swelling control.
Limits:
- Use ONLY facts and exact numbers from the twin.
- List real evidence from twin observations (crp, swelling, temperature).
- Return JSON strictly matching the Proposal schema: agent='inflammation', action_type='swelling', direction ('increase', 'maintain', 'decrease'), target_value=None, confidence (float 0..1), evidence (list of strings citing real numbers), rationale (string), risks (list of strings).
"""


def run_inflammation_agent_llm(twin: TwinState, priority_result: Any = None, fallback: bool = False) -> Proposal:
    """LLM interface for Inflammation Agent with fallback."""
    if fallback:
        return rule_based_inflammation(twin)

    from app.agents.base import call_llm_structured
    from app.agents.guardrails import validate_proposal_guardrails

    user_prompt = f"Patient Twin Data:\n{twin.model_dump_json(indent=2)}\n\nGenerate Inflammation Proposal."
    return call_llm_structured(
        system_prompt=INFLAMMATION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=Proposal,
        fallback_fn=rule_based_inflammation,
        twin=twin,
        agent_name="inflammation",
        guardrail_fn=validate_proposal_guardrails,
    )
