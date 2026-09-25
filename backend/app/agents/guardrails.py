"""Guardrails Engine for RECOVERY-SWARM (Stage D).

Validates LLM proposals and stances beyond basic schema validation.
"""

import math
import re
from typing import List, Optional
from app.models.schemas import Proposal, Stance, TwinState

ALLOWED_ACTION_TYPES = {
    "mobility": {"mobility"},
    "sleep": {"sleep"},
    "inflammation": {"swelling"},
    "medication": {"pain_review", "monitoring", "escalate"},
}


def extract_numbers_from_text(text: str) -> List[float]:
    """Extracts floating point and integer numbers from a string."""
    matches = re.findall(r"[-+]?\d*\.\d+|\d+", text)
    nums = []
    for m in matches:
        try:
            nums.append(float(m))
        except ValueError:
            pass
    return nums


def validate_proposal_guardrails(
    proposal: Proposal,
    calling_agent: str,
    twin: TwinState,
) -> bool:
    """Validates an LLM-generated Proposal against agent boundaries and twin facts."""
    # 1. Agent field equality
    if proposal.agent != calling_agent:
        return False

    # 2. Action type restriction per agent
    allowed_actions = ALLOWED_ACTION_TYPES.get(calling_agent, set())
    if proposal.action_type not in allowed_actions:
        return False

    # 3. Mobility target value sane range
    if calling_agent == "mobility" and proposal.target_value is not None:
        curr_steps = twin.observations.steps
        max_allowed = math.floor(curr_steps * 1.10)
        # Target must be non-negative and not exceed R4 daily cap by more than small tolerance
        if proposal.target_value < 0 or proposal.target_value > max_allowed * 1.05:
            return False

    # 4. Evidence numbers must exist in twin observations / scores / profile
    twin_values = [
        float(twin.observations.pain),
        float(twin.observations.sleep_hours),
        float(twin.observations.steps),
        float(twin.observations.swelling),
        float(twin.observations.temperature),
        float(twin.observations.heart_rate),
        float(twin.observations.crp),
        float(twin.scores.inflammation_score),
        float(twin.scores.mobility_capacity),
        float(twin.scores.sleep_quality),
        float(twin.scores.medication_effectiveness),
        float(twin.scores.complication_risk),
        float(twin.scores.recovery_score),
        float(twin.profile.age),
        float(twin.profile.post_op_day),
        10.0,
        100.0,
        0.0,
    ]

    for ev_text in proposal.evidence:
        nums_in_ev = extract_numbers_from_text(ev_text)
        for num in nums_in_ev:
            # Check if num is close to any twin value
            if not any(abs(num - val) <= 0.1 for val in twin_values):
                return False

    return True


def validate_stance_guardrails(
    stance: Stance,
    calling_agent: str,
    active_agents: List[str],
) -> bool:
    """Validates an LLM-generated Stance object."""
    if stance.agent != calling_agent:
        return False
    if stance.target_agent not in active_agents:
        return False
    if stance.stance not in ["support", "oppose", "revise"]:
        return False
    if stance.revised_confidence < 0.0 or stance.revised_confidence > 1.0:
        return False
    return True
