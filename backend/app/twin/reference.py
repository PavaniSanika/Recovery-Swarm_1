"""Reference recovery curves and step targets for RECOVERY-SWARM.

Values read from thresholds.yaml (reference section).
"""

from typing import Dict, Any
from app.config import config


def get_surgery_reference(surgery: str) -> Dict[str, Dict[int, float]]:
    ref = config.thresholds.get("reference", {})
    # Default or fallback to TKR if exact surgery name matches TKR keywords
    if surgery in ref:
        return ref[surgery]
    if "Knee" in surgery or "TKR" in surgery:
        return ref.get("TKR", {})
    return ref.get("TKR", {})


def get_expected_pain(surgery: str, post_op_day: int) -> float:
    ref = get_surgery_reference(surgery)
    pain_curve = ref.get("pain", {})
    day = max(1, min(7, post_op_day))
    return float(pain_curve.get(day, pain_curve.get(str(day), 4.0)))


def get_expected_inflammation(surgery: str, post_op_day: int) -> float:
    ref = get_surgery_reference(surgery)
    inf_curve = ref.get("inflammation", {})
    day = max(1, min(7, post_op_day))
    return float(inf_curve.get(day, inf_curve.get(str(day), 5.2)))


def get_step_target(surgery: str, post_op_day: int) -> int:
    ref = get_surgery_reference(surgery)
    step_curve = ref.get("step_target", {})
    day = max(1, min(7, post_op_day))
    return int(step_curve.get(day, step_curve.get(str(day), 2500)))
