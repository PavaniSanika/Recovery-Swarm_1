"""Physiological Digital Twin Engine for RECOVERY-SWARM.

Computes scores, trajectory, and updates TwinState deterministically.
No magic numbers: all weights and reference parameters come from thresholds.yaml.
"""

from typing import Any, Dict, List, Optional
from app.config import config
from app.models.schemas import (
    HistoryEntry,
    Medications,
    ObservationIn,
    Observations,
    Profile,
    Scores,
    Trajectory,
    TwinState,
)
from app.twin.reference import (
    get_expected_inflammation,
    get_expected_pain,
    get_step_target,
)


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def compute_slope(history: List[HistoryEntry], field: str, window: int = 5) -> float:
    """Computes average change per reading over recent history (last 2 to 5 entries)."""
    if len(history) < 2:
        return 0.0

    recent = history[-window:]
    values = []
    for entry in recent:
        obs = entry.observations
        scores = entry.scores
        if hasattr(obs, field):
            values.append(getattr(obs, field))
        elif hasattr(scores, field):
            values.append(getattr(scores, field))

    if len(values) < 2:
        return 0.0

    return float((values[-1] - values[0]) / (len(values) - 1))


def inflammation_score(obs: Observations, cfg: Dict[str, Any]) -> float:
    c = cfg["scoring"]["inflammation"]
    temp_bonus = max(0.0, (obs.temperature - c["temp_base_c"]) / 0.1) * c["temp_bonus_per_0_1c"]
    raw = c["w_crp"] * obs.crp + c["w_swelling"] * obs.swelling + temp_bonus
    return round(clamp(raw, 0.0, 10.0), 1)


def mobility_capacity(obs: Observations, step_target: int) -> float:
    if step_target <= 0:
        return 0.0
    raw = 10.0 * (obs.steps / step_target) * (1.0 - obs.pain / 20.0)
    return round(clamp(raw, 0.0, 10.0), 1)


def sleep_quality(obs: Observations, night_awakenings: Optional[int], cfg: Dict[str, Any]) -> float:
    s = cfg["scoring"]["sleep"]
    awakenings = night_awakenings if night_awakenings is not None else obs.night_awakenings
    penalty = min(s["max_disturbance_penalty"], (awakenings or 0) * s["penalty_per_awakening"])
    raw = 10.0 * (obs.sleep_hours / s["target_hours"]) - penalty
    return round(clamp(raw, 0.0, 10.0), 1)


def medication_effectiveness(scenario_overrides: Optional[Dict[str, float]]) -> float:
    if scenario_overrides and "medication_effectiveness" in scenario_overrides:
        return float(scenario_overrides["medication_effectiveness"])
    return 5.0


def complication_risk(
    obs: Observations,
    profile: Profile,
    history: List[HistoryEntry],
    scenario_overrides: Optional[Dict[str, float]],
    cfg: Dict[str, Any],
) -> float:
    if scenario_overrides and "complication_risk" in scenario_overrides:
        return float(scenario_overrides["complication_risk"])

    points_cfg = cfg["scoring"]["complication_points"]
    pts = 0.0

    if obs.temperature > 37.8:
        pts += points_cfg.get("temp_above_37_8", 1.0)

    if compute_slope(history, "crp") > 0:
        pts += points_cfg.get("crp_rising", 1.5)

    if "asymmetric_swelling" in obs.flags:
        pts += points_cfg.get("asymmetric_swelling", 1.0)

    # Pain rising 3 consecutive readings
    if len(history) >= 3:
        p1 = history[-3].observations.pain
        p2 = history[-2].observations.pain
        p3 = history[-1].observations.pain
        if p1 < p2 < p3 < obs.pain:
            pts += points_cfg.get("pain_rising_3_readings", 1.0)

    if profile.age > 60:
        pts += points_cfg.get("age_above_60", 0.5)

    return round(clamp(pts, 0.0, 10.0), 1)


def recovery_score(obs: Observations, scores: Scores, step_target: int, cfg: Dict[str, Any]) -> int:
    w = cfg["scoring"]["recovery_score_weights"]
    mobility_penalty = clamp(1.0 - obs.steps / step_target, 0.0, 1.0) if step_target > 0 else 1.0
    sleep_penalty = clamp(1.0 - obs.sleep_hours / 7.5, 0.0, 1.0)

    pen = (
        w["pain"] * (obs.pain / 10.0)
        + w["inflammation"] * (scores.inflammation_score / 10.0)
        + w["mobility"] * mobility_penalty
        + w["sleep"] * sleep_penalty
        + w["complication"] * (scores.complication_risk / 10.0)
    )
    return round(100.0 * (1.0 - pen))


def compute_trajectory(
    obs: Observations,
    scores: Scores,
    profile: Profile,
    history: List[HistoryEntry],
    step_target: int,
    cfg: Dict[str, Any],
) -> Trajectory:
    exp_pain = get_expected_pain(profile.surgery, profile.post_op_day)
    exp_inf = get_expected_inflammation(profile.surgery, profile.post_op_day)

    pain_dev = obs.pain - exp_pain
    inf_dev = scores.inflammation_score - exp_inf
    steps_frac = (obs.steps / step_target) if step_target > 0 else 0.0

    # Overall trajectory calculation
    worsened_3 = False
    if len(history) >= 3:
        h_recent = history[-3:]
        p_worsened = h_recent[0].observations.pain < h_recent[1].observations.pain < h_recent[2].observations.pain < obs.pain
        inf_worsened = h_recent[0].scores.inflammation_score < h_recent[1].scores.inflammation_score < h_recent[2].scores.inflammation_score < scores.inflammation_score
        step_worsened = h_recent[0].observations.steps > h_recent[1].observations.steps > h_recent[2].observations.steps > obs.steps
        worsened_3 = p_worsened or inf_worsened or step_worsened

    if worsened_3:
        overall = "deteriorating"
    else:
        below_conds = 0
        if pain_dev >= 3.0:
            below_conds += 1
        if inf_dev >= 2.0:
            below_conds += 1
        if steps_frac < 0.60:
            below_conds += 1

        if below_conds >= 2:
            overall = "below_expected"
        elif pain_dev >= 1.0 or inf_dev >= 0.5 or steps_frac < 0.90:
            overall = "slightly_below_expected"
        else:
            overall = "on_track"

    # Inflammation trajectory
    inf_slope = compute_slope(history, "inflammation_score")
    if inf_slope <= -0.15:
        inf_traj = "improving"
    elif inf_slope >= 0.15:
        inf_traj = "worsening"
    elif scores.inflammation_score >= 5.5:
        inf_traj = "stable_high"
    else:
        inf_traj = "improving"

    # Mobility trajectory
    steps_declining_3 = False
    if len(history) >= 3:
        steps_declining_3 = history[-3].observations.steps > history[-2].observations.steps > history[-1].observations.steps > obs.steps

    if steps_declining_3:
        mob_traj = "declining"
    elif steps_frac < 0.90:
        mob_traj = "below_expected"
    else:
        mob_traj = "on_track"

    # Sleep trajectory
    if scores.sleep_quality > 6.0:
        sleep_traj = "good"
    elif scores.sleep_quality < 4.0:
        sleep_traj = "poor"
    else:
        sleep_traj = "fair"

    return Trajectory(
        overall=overall,
        inflammation=inf_traj,
        mobility=mob_traj,
        sleep=sleep_traj,
    )


class TwinEngine:
    @staticmethod
    def update(twin: TwinState, observation_in: ObservationIn) -> TwinState:
        cfg = config.thresholds

        # 1. Compact previous state into history entry
        current_history = list(twin.history)
        new_entry = HistoryEntry(
            timestamp=observation_in.timestamp,
            observations=twin.observations,
            scores=twin.scores,
            overall=twin.trajectory.overall,
        )
        current_history.append(new_entry)

        # 2. Update observations (post_op_day is NOT mutated by observations)
        new_obs = Observations(
            pain=observation_in.pain,
            sleep_hours=observation_in.sleep_hours,
            steps=observation_in.steps,
            swelling=observation_in.swelling,
            temperature=observation_in.temperature,
            heart_rate=observation_in.heart_rate,
            crp=observation_in.crp,
            night_awakenings=observation_in.night_awakenings,
            flags=list(observation_in.flags or []),
        )

        step_target = get_step_target(twin.profile.surgery, twin.profile.post_op_day)
        overrides = observation_in.scenario_overrides

        # 3. Compute new scores
        inf_s = inflammation_score(new_obs, cfg)
        mob_c = mobility_capacity(new_obs, step_target)
        slp_q = sleep_quality(new_obs, observation_in.night_awakenings, cfg)
        med_e = medication_effectiveness(overrides)
        comp_r = complication_risk(new_obs, twin.profile, current_history, overrides, cfg)

        temp_scores = Scores(
            inflammation_score=inf_s,
            mobility_capacity=mob_c,
            sleep_quality=slp_q,
            medication_effectiveness=med_e,
            complication_risk=comp_r,
            recovery_score=0,
        )

        rec_s = recovery_score(new_obs, temp_scores, step_target, cfg)
        final_scores = Scores(
            inflammation_score=inf_s,
            mobility_capacity=mob_c,
            sleep_quality=slp_q,
            medication_effectiveness=med_e,
            complication_risk=comp_r,
            recovery_score=rec_s,
        )

        # 4. Compute new trajectory
        traj = compute_trajectory(
            new_obs, final_scores, twin.profile, current_history, step_target, cfg
        )

        # 5. Update medications response score
        new_meds = Medications(
            current=twin.medications.current,
            response_score=med_e,
        )

        return TwinState(
            patient_id=twin.patient_id,
            profile=twin.profile,
            observations=new_obs,
            scores=final_scores,
            trajectory=traj,
            medications=new_meds,
            history=current_history,
        )
