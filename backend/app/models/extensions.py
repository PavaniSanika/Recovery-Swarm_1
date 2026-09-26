"""Additive Extension Models for RECOVERY-SWARM (Stage H).

Includes screening flags, cohort evaluation models, and extension disclaimers.
"""

from typing import Literal, Optional, Tuple
from pydantic import Field
from app.models.schemas import Strict

SCREENING_DISCLAIMER = "Screening flag only. Not a diagnosis. Clinician review required."
EVAL_DISCLAIMER = "Technical evaluation on synthetic data. Not clinical validation."
BODY_DISCLAIMER = "Visualization of prototype scores. Not an anatomical or physiological simulation."


class ScreeningFlag(Strict):
    flag_id: Literal["SF1", "SF2", "SF3", "SF4", "SF5"]
    title: str
    severity: Literal["info", "review", "urgent"]  # "info" is reserved, unused
    evidence: list[str] = Field(min_length=1)      # real twin / observation facts
    recommendation: str                            # clinician review wording
    disclaimer: str                                # SCREENING_DISCLAIMER


class ScreeningResult(Strict):
    patient_id: str
    flags: list[ScreeningFlag]
    disclaimer: str                                # SCREENING_DISCLAIMER


class EvaluationRunRequest(Strict):
    cohort_size: int = Field(default=200, ge=20, le=500)
    seed: int = 2026


class Confusion(Strict):
    tp: int
    fn: int
    fp: int
    tn: int


class GroupMetrics(Strict):
    group: str
    n: int
    detected: int
    sensitivity: float
    ci_low: float
    ci_high: float
    median_hours_to_detection: Optional[float] = None
    flag_type_match_rate: Optional[float] = None


class SafetyInvariants(Strict):
    max_step_increase_ok: bool          # no plan asks for more than +10% steps
    no_forbidden_medication_terms: bool # rule R5 never violated in any proposal/plan
    urgent_implies_escalation: bool
    deterministic_rerun: bool           # same seed -> same report_hash
    violations: list[str] = []


class EvaluationReport(Strict):
    run_id: str
    created_at: str
    seed: int
    cohort_size: int
    mode: Literal["fallback"]
    sensitivity_overall: float
    sensitivity_ci: Tuple[float, float]
    false_alarm_rate_strict: float
    false_alarm_rate_lenient: float
    median_hours_to_detection: Optional[float] = None
    recovery_score_auc: float
    confusion: Confusion
    per_group: list[GroupMetrics]
    safety: SafetyInvariants
    report_hash: str                    # sha256 of the report excluding run_id, created_at, report_hash
    limitations: list[str]
    disclaimer: str                     # EVAL_DISCLAIMER


class HospitalPatientSummary(Strict):
    patient_id: str
    name: str
    recovery_score: int
    trajectory_overall: str
    escalated: bool
    top_screening_severity: Optional[Literal["info", "review", "urgent"]] = None

