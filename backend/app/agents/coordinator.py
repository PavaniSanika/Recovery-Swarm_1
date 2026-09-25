"""Negotiation Coordinator Agent for RECOVERY-SWARM.

Applies weighted scoring, conservative-first conflict resolution, and constraint handling to produce a swarm Decision.
"""

from typing import Any, Dict, List, Optional
from app.config import config
from app.models.schemas import PriorityResult, Proposal, Stance, Strict, TwinState


class Decision(Strict):
    winning_proposals: Dict[str, Proposal]
    decided_actions: List[Proposal]
    steps_target: Optional[int] = None
    explanation: str


def run_negotiation_coordinator(
    twin: TwinState,
    priority_result: PriorityResult,
    proposals: List[Proposal],
    stances: List[Stance],
    constraints: Optional[Dict[str, Any]] = None,
) -> Decision:
    """Evaluates specialist proposals and stances using weighted scoring and returns a consensus Decision."""
    router_cfg = config.thresholds.get("router", {})
    role_mult_cfg = router_cfg.get("role_multiplier", {"lead": 1.5, "supporting": 1.0})

    # Group proposals by topic (action_type)
    by_topic: Dict[str, List[Proposal]] = {}
    for p in proposals:
        by_topic.setdefault(p.action_type, []).append(p)

    winning_proposals: Dict[str, Proposal] = {}
    steps_target: Optional[int] = None

    for topic, topic_proposals in by_topic.items():
        best_prop: Optional[Proposal] = None
        best_score = -999.0

        for p in topic_proposals:
            role = priority_result.roles.get(p.agent, "supporting")
            role_mult = float(role_mult_cfg.get(role, 1.0))
            p_score = float(priority_result.priority_scores.get(p.agent, 0.5))

            stance_score = 0.0
            for s in stances:
                if s.target_agent == p.agent:
                    if s.stance == "support":
                        stance_score += 1.0 * float(s.revised_confidence)
                    elif s.stance == "oppose":
                        stance_score -= 1.0 * float(s.revised_confidence)

            total_score = (role_mult * p_score * float(p.confidence)) + stance_score

            if total_score > best_score:
                best_score = total_score
                best_prop = p

        if best_prop:
            # Conservative-first rule for activity/steps target
            if topic == "mobility" and best_prop.target_value is not None:
                st_val = int(best_prop.target_value)
                if constraints and "max_steps_target" in constraints:
                    max_st = int(constraints["max_steps_target"])
                    if st_val > max_st:
                        st_val = max_st
                        best_prop = best_prop.model_copy(update={"target_value": float(st_val)})
                steps_target = st_val

            winning_proposals[topic] = best_prop

    decided_actions = list(winning_proposals.values())

    # Build concise explanation from decided actions
    explanation_parts = [
        f"{p.agent.capitalize()}: {p.rationale}" for p in decided_actions
    ]
    explanation = " ".join(explanation_parts)

    return Decision(
        winning_proposals=winning_proposals,
        decided_actions=decided_actions,
        steps_target=steps_target,
        explanation=explanation,
    )
