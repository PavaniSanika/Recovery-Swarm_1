"""Deviation Check workflow component for RECOVERY-SWARM.

Rule-based early warning system comparing expected recovery curves vs actual twin trends.
Returns a typed DeviationResult.
"""

from typing import List, Optional
from app.config import config
from app.models.schemas import Strict, TwinState
from app.twin.reference import get_expected_pain


class DeviationResult(Strict):
    deviation_detected: bool
    reasons: list[str]
    red_flags: list[str]


RED_FLAG_SIGNS = {
    "chest_pain",
    "breathlessness",
    "calf_pain",
    "wound_redness",
    "wound_discharge",
    "wound_opening",
}


def check_red_flags(flags: Optional[List[str]]) -> List[str]:
    if not flags:
        return []
    return [f for f in flags if f in RED_FLAG_SIGNS]


def run_deviation_check(twin: TwinState, flags: Optional[List[str]] = None) -> DeviationResult:
    reasons: List[str] = []
    combined_flags = set(twin.observations.flags or [])
    if flags:
        combined_flags.update(flags)

    found_red_flags = check_red_flags(list(combined_flags))
    if found_red_flags:
        reasons.append(f"Red flag signs detected: {', '.join(found_red_flags)}")

    # 1. Pain above expected curve for consecutive readings
    exp_pain = get_expected_pain(twin.profile.surgery, twin.profile.post_op_day)
    history = twin.history

    if twin.observations.pain > exp_pain:
        if len(history) >= 1 and history[-1].observations.pain > exp_pain:
            reasons.append(
                f"Pain level ({twin.observations.pain}) elevated above expected threshold ({exp_pain}) for consecutive readings"
            )

    # 2. Worsening trends over 3 consecutive history readings
    if len(history) >= 2:
        # Check pain rising
        h_pains = [h.observations.pain for h in history[-2:]] + [twin.observations.pain]
        if h_pains[0] < h_pains[1] < h_pains[2]:
            reasons.append("Pain score worsening for 3 consecutive readings")

        # Check CRP / inflammation rising
        h_crps = [h.observations.crp for h in history[-2:]] + [twin.observations.crp]
        if h_crps[0] < h_crps[1] < h_crps[2]:
            reasons.append("CRP / inflammation score worsening for 3 consecutive readings")

        # Check steps declining
        h_steps = [h.observations.steps for h in history[-2:]] + [twin.observations.steps]
        if h_steps[0] > h_steps[1] > h_steps[2]:
            reasons.append("Mobility step count declining for 3 consecutive readings")

    # 3. Inflammation not falling over 24 hours of history
    if len(history) >= 4:
        # If inflammation score latest >= oldest in last 4+ readings
        first_inf = history[0].scores.inflammation_score
        if twin.scores.inflammation_score >= first_inf and twin.scores.inflammation_score >= 5.5:
            reasons.append("Inflammation score has failed to fall over preceding history window")

    deviation_detected = len(reasons) > 0 or len(found_red_flags) > 0

    return DeviationResult(
        deviation_detected=deviation_detected,
        reasons=reasons,
        red_flags=found_red_flags,
    )
