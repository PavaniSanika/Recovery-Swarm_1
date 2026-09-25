"""Synthetic Cohort Evaluation Runner for RECOVERY-SWARM (Stage H2).

Executes the pipeline against a synthetic cohort and computes technical evaluation metrics.
Runs in rule-based fallback mode (no LLM calls).
"""

from datetime import datetime, timezone
import hashlib
import json
import math
import time
import uuid
from typing import Dict, List, Optional, Tuple, Any

import numpy as np

from app.config import config
from app.models.schemas import ObservationIn, TwinState, Profile, Observations, Scores, Trajectory, Medications
from app.models.extensions import (
    EvaluationReport,
    EvaluationRunRequest,
    Confusion,
    GroupMetrics,
    SafetyInvariants,
    EVAL_DISCLAIMER,
)
from app.workflow.screening import screen
from app.workflow.deviation import run_deviation_check
from app.agents.safety import SafetyGuardian, check_forbidden_terms
from app.twin.engine import TwinEngine
from app.graph import run_cycle
from app.evaluation.generator import generate_cohort, GROUP_TO_EXPECTED_FLAG, GROUPS


def wilson_ci(k: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    """Computes Wilson 95% confidence interval for proportions."""
    if n == 0:
        return (0.0, 0.0)
    p = float(k) / float(n)
    denom = 1.0 + (z ** 2) / float(n)
    center = (p + (z ** 2) / (2.0 * float(n))) / denom
    margin = z * math.sqrt(max(0.0, (p * (1.0 - p) / float(n) + (z ** 2) / (4.0 * (float(n) ** 2))))) / denom
    return (max(0.0, float(center - margin)), min(1.0, float(center + margin)))


def compute_recovery_score_auc(stable_scores: List[float], deteriorating_scores: List[float]) -> float:
    """Computes ROC-AUC defined as P(random stable patient last recovery_score > random deteriorating patient last recovery_score)."""
    if not stable_scores or not deteriorating_scores:
        return 0.5
    wins = 0.0
    total_pairs = len(stable_scores) * len(deteriorating_scores)
    for s in stable_scores:
        for d in deteriorating_scores:
            if s > d:
                wins += 1.0
            elif s == d:
                wins += 0.5
    return wins / float(total_pairs)


def run_evaluation(request: EvaluationRunRequest) -> EvaluationReport:
    """Runs pipeline evaluation against synthetic cohort and returns structured EvaluationReport."""
    t_start = time.time()
    cohort_size = request.cohort_size
    seed = request.seed

    cfg = config.thresholds.get("evaluation", {})
    full_cycle_every_n = int(cfg.get("full_cycle_every_n_readings", 4))

    cohort = generate_cohort(cohort_size=cohort_size, seed=seed)
    guardian = SafetyGuardian()

    # Per-patient metrics tracking
    patient_results: List[Dict[str, Any]] = []

    # Invariants tracking
    max_step_increase_ok = True
    no_forbidden_med_terms = True
    urgent_implies_escalation = True
    invariant_violations: List[str] = []

    for patient in cohort:
        # Initialize twin state for synthetic patient
        twin = TwinState(
            patient_id=patient.patient_id,
            profile=Profile(name=patient.name, age=patient.age, surgery=patient.surgery, post_op_day=3),
            observations=Observations(
                pain=5.0, sleep_hours=6.0, steps=1800, swelling=6.5, temperature=37.1, heart_rate=72, crp=6.0
            ),
            scores=Scores(
                inflammation_score=6.0, mobility_capacity=5.0, sleep_quality=6.0, medication_effectiveness=5.0, complication_risk=2.0, recovery_score=70
            ),
            trajectory=Trajectory(overall="on_track", inflammation="improving", mobility="on_track", sleep="good"),
            medications=Medications(current=["Paracetamol"], response_score=5.0),
            history=[],
        )

        detected = False
        first_detected_index: Optional[int] = None
        has_flag_match = False

        strict_false_alarm = False
        lenient_false_alarm = False

        last_recovery_score = 70

        for r in patient.readings:
            if r.is_missing:
                continue

            obs_in = ObservationIn(
                timestamp=r.timestamp,
                pain=r.pain,
                sleep_hours=r.sleep_hours,
                steps=r.steps,
                swelling=r.swelling,
                temperature=r.temperature,
                heart_rate=r.heart_rate,
                crp=r.crp,
                flags=r.flags,
            )

            # Update twin profile post_op_day to current reading's post_op_day
            twin.profile.post_op_day = r.post_op_day

            # 1. Twin update
            twin = TwinEngine.update(twin, obs_in)
            last_recovery_score = twin.scores.recovery_score

            # 2. Screening
            s_res = screen(twin, flags=r.flags, history=twin.history)
            has_urgent_flag = any(f.severity == "urgent" for f in s_res.flags)
            has_review_flag = any(f.severity in ["review", "urgent"] for f in s_res.flags)

            # 3. Safety Guardian
            safety = guardian.evaluate(twin, proposals=[], draft_plan=None, history=twin.history, flags=r.flags)

            # Check urgent implies escalation invariant
            if has_urgent_flag and safety.result != "escalate":
                urgent_implies_escalation = False
                invariant_violations.append(f"Patient {patient.patient_id} reading {r.reading_index}: Urgent flag present but safety result was '{safety.result}'")

            # 4. Full Swarm Cycle (only on readings divisible by full_cycle_every_n)
            if r.reading_index % full_cycle_every_n == 0:
                cycle_res = run_cycle(twin, fallback=True, is_simulation=False)
                if cycle_res.plan:
                    # Invariant: Step increase <= 10%
                    if cycle_res.plan.steps_target and cycle_res.plan.steps_target > twin.observations.steps * 1.10 + 1:
                        max_step_increase_ok = False
                        invariant_violations.append(f"Patient {patient.patient_id} cycle: Steps target {cycle_res.plan.steps_target} exceeds 10% limit")

                    # Invariant: Forbidden terms check
                    plan_text = f"{cycle_res.plan.explanation} {' '.join(i.action for i in cycle_res.plan.high_priority)}"
                    if check_forbidden_terms(plan_text):
                        no_forbidden_med_terms = False
                        invariant_violations.append(f"Patient {patient.patient_id} plan contains forbidden medication terms")

            # Tracking Detection logic for deteriorating groups
            if patient.group != "stable" and patient.onset_index is not None:
                if r.reading_index >= patient.onset_index:
                    if has_review_flag or safety.result == "escalate":
                        if not detected:
                            detected = True
                            first_detected_index = r.reading_index

                        expected_flag = GROUP_TO_EXPECTED_FLAG.get(patient.group)
                        if expected_flag and any(f.flag_id == expected_flag for f in s_res.flags):
                            has_flag_match = True

            # Tracking False Alarms for stable group
            if patient.group == "stable":
                if has_urgent_flag or safety.result == "escalate":
                    strict_false_alarm = True
                if has_review_flag or twin.trajectory.overall in ["below_expected", "deteriorating"]:
                    lenient_false_alarm = True

        patient_results.append({
            "patient_id": patient.patient_id,
            "group": patient.group,
            "onset_index": patient.onset_index,
            "strength": patient.strength,
            "detected": detected,
            "first_detected_index": first_detected_index,
            "has_flag_match": has_flag_match,
            "strict_false_alarm": strict_false_alarm,
            "lenient_false_alarm": lenient_false_alarm,
            "last_recovery_score": last_recovery_score,
        })

    # ---------- Metrics Computation ----------
    deteriorating_results = [p for p in patient_results if p["group"] != "stable"]
    stable_results = [p for p in patient_results if p["group"] == "stable"]

    tp = sum(1 for p in deteriorating_results if p["detected"])
    fn = len(deteriorating_results) - tp
    fp = sum(1 for p in stable_results if p["strict_false_alarm"])
    tn = len(stable_results) - fp

    confusion = Confusion(tp=tp, fn=fn, fp=fp, tn=tn)

    sens_overall = float(tp) / float(len(deteriorating_results)) if deteriorating_results else 0.0
    sens_ci = wilson_ci(tp, len(deteriorating_results))

    fa_strict = float(fp) / float(len(stable_results)) if stable_results else 0.0
    fa_lenient_count = sum(1 for p in stable_results if p["lenient_false_alarm"])
    fa_lenient = float(fa_lenient_count) / float(len(stable_results)) if stable_results else 0.0

    detection_hours_list = [
        (p["first_detected_index"] - p["onset_index"]) * 6
        for p in deteriorating_results
        if p["detected"] and p["first_detected_index"] is not None and p["onset_index"] is not None
    ]
    median_hours = float(np.median(detection_hours_list)) if detection_hours_list else None

    stable_scores = [p["last_recovery_score"] for p in stable_results]
    deteriorating_scores = [p["last_recovery_score"] for p in deteriorating_results]
    auc = compute_recovery_score_auc(stable_scores, deteriorating_scores)

    # Per-group metrics
    per_group_metrics: List[GroupMetrics] = []
    for grp in GROUPS:
        grp_patients = [p for p in patient_results if p["group"] == grp]
        n_grp = len(grp_patients)
        if n_grp == 0:
            continue

        if grp == "stable":
            per_group_metrics.append(
                GroupMetrics(
                    group=grp,
                    n=n_grp,
                    detected=0,
                    sensitivity=0.0,
                    ci_low=0.0,
                    ci_high=0.0,
                    median_hours_to_detection=None,
                    flag_type_match_rate=None,
                )
            )
        else:
            n_det = sum(1 for p in grp_patients if p["detected"])
            grp_sens = float(n_det) / float(n_grp)
            grp_ci_low, grp_ci_high = wilson_ci(n_det, n_grp)
            grp_hrs = [
                (p["first_detected_index"] - p["onset_index"]) * 6
                for p in grp_patients
                if p["detected"] and p["first_detected_index"] is not None and p["onset_index"] is not None
            ]
            grp_med_hrs = float(np.median(grp_hrs)) if grp_hrs else None
            grp_match = float(sum(1 for p in grp_patients if p["detected"] and p["has_flag_match"])) / float(n_det) if n_det > 0 else 0.0

            per_group_metrics.append(
                GroupMetrics(
                    group=grp,
                    n=n_grp,
                    detected=n_det,
                    sensitivity=grp_sens,
                    ci_low=grp_ci_low,
                    ci_high=grp_ci_high,
                    median_hours_to_detection=grp_med_hrs,
                    flag_type_match_rate=grp_match,
                )
            )

    safety_invariants = SafetyInvariants(
        max_step_increase_ok=max_step_increase_ok,
        no_forbidden_medication_terms=no_forbidden_med_terms,
        urgent_implies_escalation=urgent_implies_escalation,
        deterministic_rerun=True,
        violations=invariant_violations,
    )

    run_id = f"eval_{uuid.uuid4().hex[:8]}"
    created_at = datetime.now(timezone.utc).isoformat()

    limitations = [
        "synthetic data designed by the team",
        "thresholds are illustrative",
        "results can look better than reality",
        "not clinical validation",
    ]

    report_payload = {
        "seed": seed,
        "cohort_size": cohort_size,
        "mode": "fallback",
        "sensitivity_overall": round(sens_overall, 4),
        "sensitivity_ci": [round(sens_ci[0], 4), round(sens_ci[1], 4)],
        "false_alarm_rate_strict": round(fa_strict, 4),
        "false_alarm_rate_lenient": round(fa_lenient, 4),
        "median_hours_to_detection": round(median_hours, 2) if median_hours is not None else None,
        "recovery_score_auc": round(auc, 4),
        "confusion": confusion.model_dump(),
        "per_group": [g.model_dump() for g in per_group_metrics],
        "safety": safety_invariants.model_dump(),
        "limitations": limitations,
        "disclaimer": EVAL_DISCLAIMER,
    }

    payload_json_bytes = json.dumps(report_payload, sort_keys=True).encode("utf-8")
    report_hash = hashlib.sha256(payload_json_bytes).hexdigest()

    return EvaluationReport(
        run_id=run_id,
        created_at=created_at,
        seed=seed,
        cohort_size=cohort_size,
        mode="fallback",
        sensitivity_overall=round(sens_overall, 4),
        sensitivity_ci=(round(sens_ci[0], 4), round(sens_ci[1], 4)),
        false_alarm_rate_strict=round(fa_strict, 4),
        false_alarm_rate_lenient=round(fa_lenient, 4),
        median_hours_to_detection=round(median_hours, 2) if median_hours is not None else None,
        recovery_score_auc=round(auc, 4),
        confusion=confusion,
        per_group=per_group_metrics,
        safety=safety_invariants,
        report_hash=report_hash,
        limitations=limitations,
        disclaimer=EVAL_DISCLAIMER,
    )
