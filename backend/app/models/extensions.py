"""Additive Extension Models for RECOVERY-SWARM (Stage H).

Includes screening flags, cohort evaluation models, and extension disclaimers.
"""

from typing import Literal
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
