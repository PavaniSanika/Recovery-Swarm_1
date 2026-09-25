"""Medication Response Agent for RECOVERY-SWARM.

Rule-based reasoning for medication response patterns within clinical limits (CONTRACTS section 5.4).
MUST NOT prescribe, change doses, or use forbidden medication terms.
"""

from typing import Any

from app.config import config
from app.models.schemas import Proposal, TwinState


def rule_based_medication(twin: TwinState) -> Proposal:
    """Returns rule-based proposal for medication response."""
    cfg = config.thresholds.get("agents", {}).get("medication", {})
    base_confidence = float(cfg.get("base_confidence", 0.75))

    pain = twin.observations.pain
    resp_score = twin.medications.response_score
    meds_str = ", ".join(twin.medications.current) if twin.medications.current else "None"

    evidence = [
        f"Pain = {pain:.1f}",
        f"Medication response score = {resp_score:.1f}",
        f"Active medications count = {len(twin.medications.current)}",
    ]


    esc_pain = float(cfg.get("escalate_pain", 8.0))
    rev_pain = float(cfg.get("review_pain", 6.0))
    min_resp = float(cfg.get("min_adequate_response", 5.0))

    if pain >= esc_pain:
        action_type = "escalate"
        direction = "maintain"
        rationale = (
            f"Severe pain ({pain:.1f}/10) persists despite current regimen. Clinical evaluation recommended."
        )
        risks = ["Uncontrolled pain spike"]
    elif pain >= rev_pain or (pain >= 5.0 and resp_score < min_resp):
        action_type = "pain_review"
        direction = "maintain"
        rationale = (
            f"Elevated pain ({pain:.1f}/10) indicates pain relief wears off before scheduled intervals. Clinical review of pain-management timing is recommended."
        )
        risks = ["Inadequate pain relief during recovery activities"]
    else:
        action_type = "monitoring"
        direction = "maintain"
        rationale = (
            f"Current pain management response is adequate (pain {pain:.1f}/10, response score {resp_score:.1f}/10). Continued monitoring recommended."
        )
        risks = ["Delayed reporting of symptoms"]

    return Proposal(
        agent="medication",
        action_type=action_type,
        direction=direction,
        target_value=None,
        confidence=base_confidence,
        evidence=evidence,
        rationale=rationale,
        risks=risks,
    )


def run_medication_agent(twin: TwinState) -> Proposal:
    """Standard interface for Medication Agent."""
    return rule_based_medication(twin)


MEDICATION_SYSTEM_PROMPT = """You are the Medication Response Specialist Agent for post-op knee recovery.
Your task is to analyze patient digital twin data and generate a Proposal JSON.
Specialty: Analyzing medication response and pain trends.
STRICT CLINICAL BOUNDARIES:
- MUST FORBID any dose, drug, or prescription recommendation. Never mention doses, milligrams (mg), or starting/stopping medications.
- Allow ONLY action_type: 'pain_review', 'monitoring', or 'escalate'.
- Use ONLY facts and exact numbers from the twin.
- List real evidence from twin observations (pain, medication_effectiveness).
- Return JSON strictly matching the Proposal schema: agent='medication', action_type ('pain_review' | 'monitoring' | 'escalate'), direction ('maintain'), target_value=None, confidence (float 0..1), evidence (list of strings citing real numbers), rationale (string), risks (list of strings).
"""


def run_medication_agent_llm(twin: TwinState, priority_result: Any = None, fallback: bool = False) -> Proposal:
    """LLM interface for Medication Agent with fallback."""
    if fallback:
        return rule_based_medication(twin)

    from app.agents.base import call_llm_structured
    from app.agents.guardrails import validate_proposal_guardrails

    user_prompt = f"Patient Twin Data:\n{twin.model_dump_json(indent=2)}\n\nGenerate Medication Response Proposal."
    return call_llm_structured(
        system_prompt=MEDICATION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=Proposal,
        fallback_fn=rule_based_medication,
        twin=twin,
        agent_name="medication",
        guardrail_fn=validate_proposal_guardrails,
    )
