"""CLI Script to execute synthetic cohort evaluation for RECOVERY-SWARM (Stage H2).

Usage:
    python scripts/run_evaluation.py [--cohort-size 200] [--seed 2026]
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.models.extensions import EvaluationRunRequest
from app.evaluation.runner import run_evaluation


def main():
    parser = argparse.ArgumentParser(description="Run RECOVERY-SWARM synthetic cohort evaluation.")
    parser.add_argument("--cohort-size", type=int, default=200, help="Cohort size N (default 200)")
    parser.add_argument("--seed", type=int, default=2026, help="RNG seed (default 2026)")
    args = parser.parse_args()

    print(f"=== Running Synthetic Cohort Evaluation (N={args.cohort_size}, seed={args.seed}) ===")
    t0 = time.time()
    
    req = EvaluationRunRequest(cohort_size=args.cohort_size, seed=args.seed)
    report = run_evaluation(req)
    
    elapsed = time.time() - t0
    print(f"\nCompleted in {elapsed:.2f} seconds!")
    print(f"Report ID: {report.run_id}")
    print(f"Report Hash: {report.report_hash}")
    print(f"\n--- Technical Evaluation Summary ---")
    print(f"Overall Sensitivity: {report.sensitivity_overall * 100:.1f}% (95% CI: [{report.sensitivity_ci[0]*100:.1f}%, {report.sensitivity_ci[1]*100:.1f}%])")
    print(f"Strict False Alarm Rate: {report.false_alarm_rate_strict * 100:.1f}%")
    print(f"Lenient False Alarm Rate: {report.false_alarm_rate_lenient * 100:.1f}%")
    print(f"Median Hours to Detection: {report.median_hours_to_detection} hours")
    print(f"Recovery Score ROC-AUC: {report.recovery_score_auc:.4f}")
    print(f"\nConfusion Matrix: TP={report.confusion.tp}, FN={report.confusion.fn}, FP={report.confusion.fp}, TN={report.confusion.tn}")
    print(f"\n--- Per-Group Metrics ---")
    for g in report.per_group:
        sens_str = f"{g.sensitivity * 100:.1f}%" if g.group != "stable" else "N/A"
        match_str = f"{g.flag_type_match_rate * 100:.1f}%" if g.flag_type_match_rate is not None else "N/A"
        print(f"  - {g.group:<18}: N={g.n:<3} Detected={g.detected:<3} Sensitivity={sens_str:<7} MatchRate={match_str}")

    print(f"\n--- Safety Invariants ---")
    print(f"  Max step increase <= 10%: {report.safety.max_step_increase_ok}")
    print(f"  No forbidden med terms:   {report.safety.no_forbidden_medication_terms}")
    print(f"  Urgent implies escalate:  {report.safety.urgent_implies_escalation}")
    print(f"  Deterministic rerun:      {report.safety.deterministic_rerun}")

    print(f"\nDisclaimer: {report.disclaimer}")
    print("Limitations:", ", ".join(report.limitations))


if __name__ == "__main__":
    main()
