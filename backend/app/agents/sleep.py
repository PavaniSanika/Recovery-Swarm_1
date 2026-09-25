"""Sleep & Recovery Agent for RECOVERY-SWARM.

Rule-based reasoning for sleep quality and rest requirements.
"""

from typing import Any

from app.config import config
from app.models.schemas import Proposal, TwinState


def rule_based_sleep(twin: TwinState) -> Proposal:
    """Returns rule-based proposal for sleep."""
    cfg = config.thresholds.get("agents", {}).get("sleep", {})
    base_confidence = float(cfg.get("base_confidence", 0.85))

    sleep_hours = twin.observations.sleep_hours
    sleep_qual = twin.scores.sleep_quality

    evidence = [
        f"Sleep hours = {sleep_hours:.1f}",
        f"Sleep quality score = {sleep_qual:.1f}",
    ]

    if sleep_hours < 5.0 or sleep_qual < 4.0:
        direction = "increase"
        rationale = (
            "Sleep quality is poor and total sleep hours are insufficient. Prioritize sleep-supportive environment and rest tonight."
        )
        risks = ["Daytime fatigue", "Increased pain perception due to poor sleep"]
    elif sleep_hours < 6.5 or sleep_qual < 6.0:
        direction = "increase"
        rationale = "Sleep duration is slightly below optimal. Rest and sleep hygiene recommended."
        risks = ["Mild fatigue"]
    else:
        direction = "maintain"
        rationale = "Sleep duration and quality are adequate."
        risks = ["Intermittent night awakenings"]

    return Proposal(
        agent="sleep",
        action_type="sleep",
        direction=direction,
        target_value=None,
        confidence=base_confidence,
        evidence=evidence,
        rationale=rationale,
        risks=risks,
    )


def run_sleep_agent(twin: TwinState) -> Proposal:
    """Standard interface for Sleep Agent."""
    return rule_based_sleep(twin)


SLEEP_SYSTEM_PROMPT = """You are the Sleep & Recovery Specialist Agent for post-op knee recovery.
Your task is to analyze patient digital twin data and generate a Proposal JSON.
Specialty: Post-surgical sleep hygiene, sleep duration, and rest optimization.
Limits:
- Use ONLY facts and exact numbers from the twin.
- List real evidence from twin observations (sleep_hours, sleep_quality).
- Return JSON strictly matching the Proposal schema: agent='sleep', action_type='sleep', direction ('increase', 'maintain', 'decrease'), target_value=None, confidence (float 0..1), evidence (list of strings citing real numbers), rationale (string), risks (list of strings).
"""


def run_sleep_agent_llm(twin: TwinState, priority_result: Any = None, fallback: bool = False) -> Proposal:
    """LLM interface for Sleep Agent with fallback."""
    if fallback:
        return rule_based_sleep(twin)

    from app.agents.base import call_llm_structured
    from app.agents.guardrails import validate_proposal_guardrails

    user_prompt = f"Patient Twin Data:\n{twin.model_dump_json(indent=2)}\n\nGenerate Sleep Proposal."
    return call_llm_structured(
        system_prompt=SLEEP_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=Proposal,
        fallback_fn=rule_based_sleep,
        twin=twin,
        agent_name="sleep",
        guardrail_fn=validate_proposal_guardrails,
    )
