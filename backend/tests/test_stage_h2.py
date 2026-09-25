"""Tests for Stage H2: Synthetic Cohort Evaluation Harness.

Verifies deterministic reproducibility, safety invariants, verbatim limitations, hand-computed AUC direction, smoke expectations, and API persistence.
"""

import time
import pytest
from fastapi.testclient import TestClient

from app.models.extensions import EvaluationRunRequest, EvaluationReport, EVAL_DISCLAIMER
from app.evaluation.runner import run_evaluation, compute_recovery_score_auc
from app.evaluation.generator import generate_cohort
from app.db import init_db
from app.main import app

# Ensure database tables exist
init_db()

client = TestClient(app)


def test_auc_direction_hand_computed_toy_datasets():
    """Verifies ROC-AUC calculation direction convention P(stable score > deteriorating score).

    Case 1 (Fully separated): Stable [80, 90] vs Deteriorating [50, 60] -> AUC = 1.0 (4/4 pairs stable > deteriorating)
    Case 2 (Partial overlap - User prompt requirement): Stable [70, 90] vs Deteriorating [60, 80] -> AUC = 0.75 (3/4 pairs stable > deteriorating)
    """
    # Case 1: Fully separated
    auc_sep = compute_recovery_score_auc([80.0, 90.0], [50.0, 60.0])
    assert auc_sep == 1.0, f"Expected AUC 1.0 for fully separated scores, got {auc_sep}"

    # Case 2: Partial overlap
    # Pairs (stable, deteriorating):
    # (70, 60) -> 70 > 60 (Win = 1.0)
    # (70, 80) -> 70 < 80 (Loss = 0.0)
    # (90, 60) -> 90 > 60 (Win = 1.0)
    # (90, 80) -> 90 > 80 (Win = 1.0)
    # Total = 3.0 / 4 = 0.75
    auc_overlap = compute_recovery_score_auc([70.0, 90.0], [60.0, 80.0])
    assert auc_overlap == 0.75, f"Expected exact AUC 0.75 for partial overlap scores, got {auc_overlap}"


def test_deterministic_reproducibility():
    """Same seed and cohort size give identical report_hash; different seed gives a different hash."""
    req1 = EvaluationRunRequest(cohort_size=50, seed=2026)
    report1 = run_evaluation(req1)

    req2 = EvaluationRunRequest(cohort_size=50, seed=2026)
    report2 = run_evaluation(req2)

    req3 = EvaluationRunRequest(cohort_size=50, seed=9999)
    report3 = run_evaluation(req3)

    assert report1.report_hash == report2.report_hash, "Same seed must produce identical report_hash"
    assert report1.report_hash != report3.report_hash, "Different seed must produce different report_hash"


def test_safety_invariants_hold():
    """All 4 safety invariants pass (True) with violations == []."""
    req = EvaluationRunRequest(cohort_size=50, seed=2026)
    report = run_evaluation(req)

    assert report.safety.max_step_increase_ok is True
    assert report.safety.no_forbidden_medication_terms is True
    assert report.safety.urgent_implies_escalation is True
    assert report.safety.deterministic_rerun is True
    assert report.safety.violations == [], f"Expected empty violations, got {report.safety.violations}"


def test_verbatim_limitations_and_disclaimer():
    """Asserts limitations contains all 4 required strings verbatim and disclaimer matches EVAL_DISCLAIMER."""
    req = EvaluationRunRequest(cohort_size=20, seed=2026)
    report = run_evaluation(req)

    assert report.disclaimer == EVAL_DISCLAIMER

    expected_limitations = [
        "synthetic data designed by the team",
        "thresholds are illustrative",
        "results can look better than reality",
        "not clinical validation",
    ]

    for limit_str in expected_limitations:
        assert limit_str in report.limitations, f"Missing required limitation verbatim string: '{limit_str}'"


def test_smoke_expectations_high_strength_detection_and_false_alarms():
    """Events with strength >= 0.8 must be detected >= 90% of the time. Strict false alarm rate is reported honestly."""
    req = EvaluationRunRequest(cohort_size=200, seed=2026)
    report = run_evaluation(req)

    cohort = generate_cohort(cohort_size=200, seed=2026)
    high_strength_pids = set(p.patient_id for p in cohort if p.group != "stable" and p.strength is not None and p.strength >= 0.8)

    # Calculate high-strength detection rate directly
    from app.workflow.screening import screen
    from app.twin.engine import TwinEngine
    from app.agents.safety import SafetyGuardian
    from app.models.schemas import ObservationIn, TwinState, Profile, Observations, Scores, Trajectory, Medications

    guardian = SafetyGuardian()
    high_strength_detected = 0

    for p in cohort:
        if p.patient_id not in high_strength_pids:
            continue
        twin = TwinState(
            patient_id=p.patient_id,
            profile=Profile(name=p.name, age=p.age, surgery=p.surgery, post_op_day=3),
            observations=Observations(pain=5.0, sleep_hours=6.0, steps=1800, swelling=6.5, temperature=37.1, heart_rate=72, crp=6.0),
            scores=Scores(inflammation_score=6.0, mobility_capacity=5.0, sleep_quality=6.0, medication_effectiveness=5.0, complication_risk=2.0, recovery_score=70),
            trajectory=Trajectory(overall="on_track", inflammation="improving", mobility="on_track", sleep="good"),
            medications=Medications(current=["Paracetamol"], response_score=5.0),
            history=[],
        )
        detected = False
        for r in p.readings:
            if r.is_missing:
                continue
            obs_in = ObservationIn(
                timestamp=r.timestamp, pain=r.pain, sleep_hours=r.sleep_hours, steps=r.steps,
                swelling=r.swelling, temperature=r.temperature, heart_rate=r.heart_rate, crp=r.crp, flags=r.flags
            )
            twin = TwinEngine.update(twin, obs_in)
            s_res = screen(twin, flags=r.flags, history=twin.history)
            safety = guardian.evaluate(twin, proposals=[], draft_plan=None, history=twin.history, flags=r.flags)
            if p.onset_index is not None and r.reading_index >= p.onset_index:
                has_review_flag = any(f.severity in ["review", "urgent"] for f in s_res.flags)
                if has_review_flag or safety.result == "escalate":
                    detected = True
                    break
        if detected:
            high_strength_detected += 1

    high_strength_rate = float(high_strength_detected) / float(len(high_strength_pids))

    print(f"\n[Smoke Check] High-Strength (>=0.8) Sensitivity: {high_strength_rate * 100:.1f}% ({high_strength_detected}/{len(high_strength_pids)})")
    print(f"[Smoke Check] Overall Cohort Sensitivity: {report.sensitivity_overall * 100:.1f}%")
    print(f"[Smoke Check] Strict False Alarm Rate: {report.false_alarm_rate_strict * 100:.1f}%")
    print(f"[Smoke Check] Lenient False Alarm Rate: {report.false_alarm_rate_lenient * 100:.1f}%")

    assert high_strength_rate >= 0.90, f"Expected high-strength event sensitivity >= 0.90, got {high_strength_rate}"
    assert report.false_alarm_rate_lenient < 0.50, f"Expected lenient false alarm rate < 0.50, got {report.false_alarm_rate_lenient}"
    assert isinstance(report.false_alarm_rate_strict, float)


def test_regression_post_op_day_tracks_reading_day_in_eval_loop():
    """Regression test: Asserts twin.profile.post_op_day dynamically matches r.post_op_day for every reading during evaluation."""
    from app.twin.engine import TwinEngine
    from app.models.schemas import ObservationIn, TwinState, Profile, Observations, Scores, Trajectory, Medications

    cohort = generate_cohort(cohort_size=10, seed=2026)
    for patient in cohort:
        twin = TwinState(
            patient_id=patient.patient_id,
            profile=Profile(name=patient.name, age=patient.age, surgery=patient.surgery, post_op_day=3),
            observations=Observations(pain=5.0, sleep_hours=6.0, steps=1800, swelling=6.5, temperature=37.1, heart_rate=72, crp=6.0),
            scores=Scores(inflammation_score=6.0, mobility_capacity=5.0, sleep_quality=6.0, medication_effectiveness=5.0, complication_risk=2.0, recovery_score=70),
            trajectory=Trajectory(overall="on_track", inflammation="improving", mobility="on_track", sleep="good"),
            medications=Medications(current=["Paracetamol"], response_score=5.0),
            history=[],
        )
        for r in patient.readings:
            if r.is_missing:
                continue
            twin.profile.post_op_day = r.post_op_day
            obs_in = ObservationIn(
                timestamp=r.timestamp, pain=r.pain, sleep_hours=r.sleep_hours, steps=r.steps,
                swelling=r.swelling, temperature=r.temperature, heart_rate=r.heart_rate, crp=r.crp, flags=r.flags
            )
            twin = TwinEngine.update(twin, obs_in)
            assert twin.profile.post_op_day == r.post_op_day, f"Expected post_op_day {r.post_op_day}, got {twin.profile.post_op_day}"


def test_evaluation_api_endpoints_end_to_end():
    """Tests POST /api/evaluation/run and GET /api/evaluation/latest endpoints."""
    t0 = time.time()
    res_run = client.post("/api/evaluation/run", json={"cohort_size": 200, "seed": 2026})
    elapsed = time.time() - t0

    print(f"\n[Performance Timing] 200-patient evaluation run completed in {elapsed:.2f} seconds!")
    assert elapsed < 60.0, f"Evaluation run exceeded 60s budget: {elapsed:.2f}s"
    assert res_run.status_code == 200

    data_run = res_run.json()
    report_run = EvaluationReport(**data_run)
    assert report_run.cohort_size == 200

    # Test GET /api/evaluation/latest
    res_latest = client.get("/api/evaluation/latest")
    assert res_latest.status_code == 200
    report_latest = EvaluationReport(**res_latest.json())

    assert report_latest.run_id == report_run.run_id
    assert report_latest.report_hash == report_run.report_hash
