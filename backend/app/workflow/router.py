"""Priority Router for RECOVERY-SWARM.

Workflow component evaluating patient twin data to assign relevance priorities and roles (lead, supporting, waiting) to specialist agents.
"""

from app.config import config
from app.models.schemas import PriorityResult, TwinState
from app.twin.reference import get_step_target


def clamp(val: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, val))


def run_priority_router(twin: TwinState) -> PriorityResult:
    """Computes specialist agent priority scores and roles from twin state.
    
    Formula per CONTRACTS 5.1 and thresholds.yaml.
    """
    step_target = get_step_target(twin.profile.surgery, twin.profile.post_op_day)

    pain = twin.observations.pain
    swelling = twin.observations.swelling
    steps = twin.observations.steps
    sleep_hours = twin.observations.sleep_hours
    sleep_qual = twin.scores.sleep_quality
    inf_score = twin.scores.inflammation_score
    med_eff = twin.scores.medication_effectiveness

    mobility_gap = clamp(1.0 - (steps / float(step_target)))
    sleep_deficit = clamp(1.0 - (sleep_hours / 7.5))

    signals = {
        "mobility": 0.50 * (pain / 10.0) + 0.25 * mobility_gap + 0.25 * (swelling / 10.0),
        "sleep": 0.60 * (1.0 - sleep_qual / 10.0) + 0.40 * sleep_deficit,
        "inflammation": 0.60 * (inf_score / 10.0) + 0.40 * (swelling / 10.0),
        "medication": 0.50 * (1.0 - med_eff / 10.0) + 0.20 * (pain / 10.0),
    }

    router_cfg = config.thresholds.get("router", {})
    base = float(router_cfg.get("base", 0.3))
    scale = float(router_cfg.get("scale", 0.9))
    lead_count = int(router_cfg.get("lead_count", 3))
    waiting_below = float(router_cfg.get("waiting_below", 0.30))

    priority_scores: dict[str, float] = {}
    for agent, sig in signals.items():
        score = clamp(base + scale * sig, 0.0, 1.0)
        priority_scores[agent] = round(score, 4)

    # Sort agents by priority score descending
    sorted_agents = sorted(
        priority_scores.keys(), key=lambda a: priority_scores[a], reverse=True
    )

    roles: dict[str, str] = {}
    for idx, agent in enumerate(sorted_agents):
        score = priority_scores[agent]
        if score < waiting_below:
            roles[agent] = "waiting"
        elif idx < lead_count:
            roles[agent] = "lead"
        else:
            roles[agent] = "supporting"

    return PriorityResult(priority_scores=priority_scores, roles=roles)
