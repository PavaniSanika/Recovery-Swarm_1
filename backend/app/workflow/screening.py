"""Screening Workflow Component for RECOVERY-SWARM (Stage H1).

Implements deterministic early-warning screening flags (SF1-SF5) as specified in CONTRACTS Section 12.1.
This is a read-only workflow component, NOT an agent.
"""

from copy import deepcopy
from typing import List, Optional
from app.config import config
from app.models.schemas import TwinState, HistoryEntry
from app.models.extensions import (
  ScreeningFlag,
  ScreeningResult,
  SCREENING_DISCLAIMER,
)
from app.twin.reference import get_step_target


def screen(
  twin: TwinState,
  flags: Optional[List[str]] = None,
  history: Optional[List[HistoryEntry]] = None,
) -> ScreeningResult:
  """Executes deterministic screening checks across rules SF1 through SF5.

  Returns a validated ScreeningResult containing flags ordered SF1..SF5.
  Does NOT mutate input objects.
  """
  obs_flags = flags if flags is not None else twin.observations.flags
  hist = (
      history if history is not None else (twin.history if twin.history else [])
  )

  cfg = config.thresholds.get("screening", {})

  detected_flags: List[ScreeningFlag] = []

  # Current Twin Facts
  temp = twin.observations.temperature
  crp = twin.observations.crp
  swelling = twin.observations.swelling
  pain = twin.observations.pain
  steps = twin.observations.steps
  overall_traj = twin.trajectory.overall
  step_target = get_step_target(
      twin.profile.surgery, twin.profile.post_op_day
  )

  # Wound & Red flags
  sf1_cfg = cfg.get("SF1", {})
  sf1_urgent_wound = sf1_cfg.get("urgent", {}).get("wound_flags", [
      "wound_redness",
      "wound_discharge",
      "wound_opening",
  ])
  has_wound_flag = any(f in obs_flags for f in sf1_urgent_wound)

  sf2_cfg = cfg.get("SF2", {})
  sf2_urgent_any = sf2_cfg.get("urgent", {}).get(
      "flags_any", ["chest_pain", "breathlessness"]
  )
  has_urgent_clot_flag = any(f in obs_flags for f in sf2_urgent_any)
  has_calf_pain = "calf_pain" in obs_flags

  # ---------- SF1: Infection Pattern ----------
  sf1_title = sf1_cfg.get("title", "Possible infection pattern")
  sf1_severity = None
  sf1_evidence = []

  if temp >= 38.0 or has_wound_flag:
    sf1_severity = "urgent"
    if temp >= 38.0:
      sf1_evidence.append(f"Elevated body temperature: {temp:.1f}°C (>= 38.0°C)")
    for f in obs_flags:
      if f in sf1_urgent_wound:
        sf1_evidence.append(f"Wound sign observed: {f}")
  elif temp >= 37.8 and crp >= 7.0:
    sf1_severity = "review"
    sf1_evidence.append(f"Subfebrile temperature: {temp:.1f}°C (>= 37.8°C)")
    sf1_evidence.append(f"Elevated CRP index: {crp:.1f} (>= 7.0)")

  if sf1_severity:
    detected_flags.append(
        ScreeningFlag(
            flag_id="SF1",
            title=sf1_title,
            severity=sf1_severity,
            evidence=sf1_evidence,
            recommendation="Clinician review recommended.",
            disclaimer=SCREENING_DISCLAIMER,
        )
    )

  # ---------- SF2: Clot Warning Signs ----------
  sf2_title = sf2_cfg.get("title", "Possible clot warning signs")
  sf2_severity = None
  sf2_evidence = []

  if has_urgent_clot_flag or (has_calf_pain and swelling >= 7.0):
    sf2_severity = "urgent"
    for f in obs_flags:
      if f in sf2_urgent_any:
        sf2_evidence.append(f"Cardiopulmonary sign observed: {f}")
    if has_calf_pain:
      sf2_evidence.append("Calf pain reported")
    if swelling >= 7.0:
      sf2_evidence.append(f"High joint swelling: {swelling:.1f} (>= 7.0)")
  elif has_calf_pain and swelling >= 6.0:
    sf2_severity = "review"
    sf2_evidence.append("Calf pain reported")
    sf2_evidence.append(f"Moderate joint swelling: {swelling:.1f} (>= 6.0)")

  if sf2_severity:
    detected_flags.append(
        ScreeningFlag(
            flag_id="SF2",
            title=sf2_title,
            severity=sf2_severity,
            evidence=sf2_evidence,
            recommendation="Clinician review recommended.",
            disclaimer=SCREENING_DISCLAIMER,
        )
    )

  # ---------- SF3: Delayed Healing Pattern ----------
  sf3_cfg = cfg.get("SF3", {})
  sf3_title = sf3_cfg.get("title", "Delayed healing pattern")
  if hist:
    prev_entry = hist[-1]
    prev_overall = prev_entry.overall
    if (
        overall_traj in ["below_expected", "deteriorating"]
        and prev_overall in ["below_expected", "deteriorating"]
    ):
      detected_flags.append(
          ScreeningFlag(
              flag_id="SF3",
              title=sf3_title,
              severity="review",
              evidence=[
                  f"Current trajectory overall status is '{overall_traj}'",
                  f"Previous trajectory overall status was '{prev_overall}'",
              ],
              recommendation="Clinician review recommended.",
              disclaimer=SCREENING_DISCLAIMER,
          )
      )

  # ---------- SF4: Uncontrolled Pain Pattern ----------
  sf4_cfg = cfg.get("SF4", {})
  sf4_title = sf4_cfg.get("title", "Uncontrolled pain pattern")
  if hist:
    prev_entry = hist[-1]
    prev_pain = prev_entry.observations.pain
    if pain >= 7.0 and prev_pain >= 7.0:
      detected_flags.append(
          ScreeningFlag(
              flag_id="SF4",
              title=sf4_title,
              severity="review",
              evidence=[
                  f"Current pain level: {pain:.1f} (>= 7.0)",
                  f"Previous history pain level: {prev_pain:.1f} (>= 7.0)",
              ],
              recommendation="Clinician review recommended.",
              disclaimer=SCREENING_DISCLAIMER,
          )
      )

  # ---------- SF5: Slow Mobility Progress ----------
  # Rule: Evaluated against CURRENT step target for both current and previous history entry
  sf5_cfg = cfg.get("SF5", {})
  sf5_title = sf5_cfg.get("title", "Slow mobility progress")
  if hist and step_target > 0:
    prev_entry = hist[-1]
    prev_steps = prev_entry.observations.steps

    curr_frac = steps / float(step_target)
    prev_frac_current_target = prev_steps / float(step_target)

    if curr_frac < 0.60 and prev_frac_current_target < 0.60:
      detected_flags.append(
          ScreeningFlag(
              flag_id="SF5",
              title=sf5_title,
              severity="review",
              evidence=[
                  (
                      f"Current steps ({steps}) are"
                      f" {curr_frac * 100:.1f}% of current daily target"
                      f" ({step_target})"
                  ),
                  (
                      f"Previous steps ({prev_steps}) are"
                      f" {prev_frac_current_target * 100:.1f}% of current daily"
                      f" target ({step_target})"
                  ),
              ],
              recommendation="Clinician review recommended.",
              disclaimer=SCREENING_DISCLAIMER,
          )
      )

  return ScreeningResult(
      patient_id=twin.patient_id,
      flags=detected_flags,
      disclaimer=SCREENING_DISCLAIMER,
  )
