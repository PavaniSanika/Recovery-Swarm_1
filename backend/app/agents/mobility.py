"""Mobility & Pain Agent for RECOVERY-SWARM.

Rule-based reasoning for mobility and exercise targets.
"""

import math
from typing import Any
from app.config import config
from app.models.schemas import Proposal, TwinState
from app.twin.reference import get_step_target


def round_to_nearest(val: float, nearest: int = 50) -> float:
    return float(int(round(val / float(nearest))) * nearest)


def rule_based_mobility(twin: TwinState) -> Proposal:
    """Returns rule-based proposal for mobility."""
    cfg = config.thresholds.get("agents", {}).get("mobility", {})
    gap_fraction = float(cfg.get("gap_fraction", 0.60))
    round_step_target = int(cfg.get("round_step_target", 50))
    base_confidence = float(cfg.get("base_confidence", 0.70))

    current_steps = twin.observations.steps
    pain = twin.observations.pain
    swelling = twin.observations.swelling
    step_target = get_step_target(twin.profile.surgery, twin.profile.post_op_day)

    evidence = [
        f"Pain = {pain:.1f}",
        f"Steps = {current_steps}",
        f"Swelling = {swelling:.1f}",
    ]

    if pain >= 7.0:
        direction = "maintain"
        target_val = float(current_steps)
        rationale = "Elevated pain limits activity increase."
        risks = ["Pain exacerbation", "Further mobility decline"]
    elif pain >= 5.5 or swelling >= 5.5:
        raw_target = current_steps + gap_fraction * (step_target - current_steps)
        target_val = round_to_nearest(raw_target, round_step_target)
        direction = "increase"
        rationale = "Mobility is below target but pain and swelling limit aggressive increase."
        risks = ["Increased pain", "Increased swelling"]
    else:
        raw_target = current_steps + gap_fraction * (step_target - current_steps)
        max_allowed = float(math.floor(current_steps * 1.10))
        target_capped = min(raw_target, max_allowed)
        target_val = float((int(target_capped) // round_step_target) * round_step_target)
        direction = "increase"
        rationale = "Pain is controlled. Gradual increase in mobility is safe."
        risks = ["Mild muscle fatigue"]

    return Proposal(
        agent="mobility",
        action_type="mobility",
        direction=direction,
        target_value=target_val,
        confidence=base_confidence,
        evidence=evidence,
        rationale=rationale,
        risks=risks,
    )


def run_mobility_agent(twin: TwinState) -> Proposal:
    """Standard interface for Mobility Agent."""
    return rule_based_mobility(twin)


MOBILITY_SYSTEM_PROMPT = """You are the Mobility & Pain Specialist Agent for post-op knee recovery.
Your task is to analyze patient digital twin data and generate a Proposal JSON.
Specialty: Post-surgical mobility & exercise progression.
Limits:
- Prefer gradual step target changes of 10% or less above current steps.
- Use ONLY facts and exact numbers from the twin.
- List real evidence from twin observations (pain, steps, swelling).
- Return JSON strictly matching the Proposal schema: agent='mobility', action_type='mobility', direction ('increase', 'maintain', 'decrease'), target_value (float or null), confidence (float 0..1), evidence (list of strings citing real numbers), rationale (string), risks (list of strings).
"""


def run_mobility_agent_llm(twin: TwinState, priority_result: Any = None, fallback: bool = False) -> Proposal:
    """LLM interface for Mobility Agent with fallback."""
    if fallback:
        return rule_based_mobility(twin)

    from app.agents.base import call_llm_structured
    from app.agents.guardrails import validate_proposal_guardrails

    user_prompt = f"Patient Twin Data:\n{twin.model_dump_json(indent=2)}\n\nGenerate Mobility Proposal."
    return call_llm_structured(
        system_prompt=MOBILITY_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=Proposal,
        fallback_fn=rule_based_mobility,
        twin=twin,
        agent_name="mobility",
        guardrail_fn=validate_proposal_guardrails,
    )
