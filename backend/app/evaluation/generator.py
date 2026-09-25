"""Synthetic Cohort Generator for RECOVERY-SWARM (Stage H2).

Generates reproducible synthetic patient trajectories with seeded ground truth events.
Must NOT read or import safety_rules or screening thresholds.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np


@dataclass
class SyntheticReading:
    reading_index: int
    post_op_day: int
    hour_offset: int
    timestamp: str
    pain: float
    sleep_hours: float
    steps: int
    swelling: float
    temperature: float
    heart_rate: int
    crp: float
    flags: List[str] = field(default_factory=list)
    is_missing: bool = False


@dataclass
class SyntheticPatient:
    patient_id: str
    name: str
    age: int
    surgery: str
    group: str  # "stable", "infection_like", "clot_like", "delayed_healing", "uncontrolled_pain", "mobility_decline"
    onset_index: Optional[int]
    strength: Optional[float]
    readings: List[SyntheticReading]


# Base baseline curve for TKR (days 3, 4, 5, 6)
BASELINE_TKR = {
    3: {"pain": 5.0, "crp": 6.0, "swelling": 6.5, "steps": 1800, "sleep": 5.0, "temp": 37.1},
    4: {"pain": 4.0, "crp": 5.2, "swelling": 6.0, "steps": 2500, "sleep": 6.0, "temp": 37.0},
    5: {"pain": 3.5, "crp": 4.6, "swelling": 5.0, "steps": 2800, "sleep": 6.5, "temp": 36.9},
    6: {"pain": 3.0, "crp": 4.0, "swelling": 4.2, "steps": 3200, "sleep": 7.0, "temp": 36.8},
}

GROUPS = [
    "stable",
    "infection_like",
    "clot_like",
    "delayed_healing",
    "uncontrolled_pain",
    "mobility_decline",
]

GROUP_TO_EXPECTED_FLAG = {
    "infection_like": "SF1",
    "clot_like": "SF2",
    "delayed_healing": "SF3",
    "uncontrolled_pain": "SF4",
    "mobility_decline": "SF5",
}


def generate_cohort(cohort_size: int = 200, seed: int = 2026) -> List[SyntheticPatient]:
    """Generates N synthetic patient trajectories using numpy.random.default_rng(seed)."""
    rng = np.random.default_rng(seed)

    # Group counts according to prevalence (50% stable, 10% each for 5 event groups)
    n_groups = len(GROUPS) - 1  # 5 event groups
    n_per_event = int(np.floor(cohort_size * 0.10))
    n_stable = cohort_size - (n_per_event * n_groups)

    group_assignments = ["stable"] * n_stable
    for grp in ["infection_like", "clot_like", "delayed_healing", "uncontrolled_pain", "mobility_decline"]:
        group_assignments.extend([grp] * n_per_event)

    # Shuffle deterministic assignment order
    rng.shuffle(group_assignments)

    patients: List[SyntheticPatient] = []
    days = [3, 4, 5, 6]
    readings_per_day = 4

    for p_idx in range(cohort_size):
        patient_id = f"SYNTH_{p_idx + 1:04d}"
        name = f"Cohort Patient {p_idx + 1}"
        age = int(rng.integers(45, 81))
        surgery = "Total Knee Replacement"
        grp = group_assignments[p_idx]

        onset_index = None
        strength = None
        if grp != "stable":
            onset_index = int(rng.integers(2, 10))  # Onset between reading 2 and 9
            strength = float(rng.uniform(0.4, 1.0))

        # Harmless spike for stable patient (20% probability)
        stable_spike_index = None
        stable_spike_type = None
        if grp == "stable" and rng.random() < 0.20:
            stable_spike_index = int(rng.integers(4, 12))
            stable_spike_type = "pain" if rng.random() < 0.5 else "steps"

        # Pre-determine boolean event flags for the patient trajectory
        has_wound_flag = (grp == "infection_like") and (rng.random() < 0.60)
        has_calf_pain = (grp == "clot_like") and (rng.random() < 0.80)
        has_chest_pain = (grp == "clot_like") and (rng.random() < 0.15)

        readings: List[SyntheticReading] = []
        r_counter = 0

        for d_idx, day in enumerate(days):
            base_ref = BASELINE_TKR[day]
            step_target = base_ref["steps"]

            for r_day in range(readings_per_day):
                hour_offset = (d_idx * 24) + (r_day * 6)
                timestamp = f"2026-09-{20 + d_idx:02d}T{r_day * 6:02d}:00:00Z"

                # Measurement noise
                n_pain = float(rng.normal(0, 0.15))
                n_crp = float(rng.normal(0, 0.2))
                n_swelling = float(rng.normal(0, 0.2))
                n_temp = float(rng.normal(0, 0.05))
                n_steps = float(rng.normal(0, 50))

                val_pain = base_ref["pain"] + n_pain
                val_crp = base_ref["crp"] + n_crp
                val_swelling = base_ref["swelling"] + n_swelling
                val_temp = base_ref["temp"] + n_temp
                val_steps = int(base_ref["steps"] + n_steps)
                val_sleep = base_ref["sleep"]
                val_hr = int(72 + rng.integers(-4, 5))
                obs_flags: List[str] = []

                # Apply group event modifications if onset reached
                if grp != "stable" and onset_index is not None and r_counter >= onset_index:
                    rel_step = r_counter - onset_index

                    if grp == "infection_like":
                        # Temp rises +0.9 to +1.6 C over ~12h (2 readings)
                        temp_rise = min((0.9 + 0.7 * strength), (0.45 + 0.35 * strength) * (rel_step + 1))
                        val_temp += temp_rise
                        val_crp += (2.0 + 2.0 * strength)
                        if has_wound_flag:
                            obs_flags.append("wound_discharge")

                    elif grp == "clot_like":
                        val_swelling += (1.5 + 1.5 * strength)
                        if has_calf_pain:
                            obs_flags.append("calf_pain")
                        if has_chest_pain:
                            obs_flags.append("chest_pain")

                    elif grp == "delayed_healing":
                        # Plateau pain (capped < 7.0 to avoid SF4 overlap) and CRP/steps to sustain below_expected trajectory
                        val_pain += (2.5 + 0.5 * strength)
                        val_pain = float(np.clip(val_pain, 0.0, 6.8))
                        val_crp += (2.5 + 1.5 * strength)
                        val_steps = int(val_steps * (0.55 - 0.15 * strength))

                    elif grp == "uncontrolled_pain":
                        # Pain rises +0.8 to +4.4 above baseline scaled by strength
                        val_pain += (0.8 + 3.6 * strength)

                    elif grp == "mobility_decline":
                        # Steps fall to 35% - 55% of target
                        target_frac = 0.35 + 0.20 * (1.0 - strength)
                        val_steps = int(step_target * target_frac)

                # Apply harmless single-reading spike for stable cohort
                if grp == "stable" and stable_spike_index is not None and r_counter == stable_spike_index:
                    if stable_spike_type == "pain":
                        val_pain += 1.5
                    elif stable_spike_type == "steps":
                        val_steps = int(val_steps * 0.75)

                # Clamp values to valid ranges
                val_pain = float(np.clip(val_pain, 0.0, 10.0))
                val_crp = float(np.clip(val_crp, 0.0, 10.0))
                val_swelling = float(np.clip(val_swelling, 0.0, 10.0))
                val_temp = float(np.clip(val_temp, 35.0, 41.0))
                val_steps = int(max(0, val_steps))

                # Missing reading simulation (~3%)
                is_missing = bool(rng.random() < 0.03)

                readings.append(
                    SyntheticReading(
                        reading_index=r_counter,
                        post_op_day=day,
                        hour_offset=hour_offset,
                        timestamp=timestamp,
                        pain=val_pain,
                        sleep_hours=val_sleep,
                        steps=val_steps,
                        swelling=val_swelling,
                        temperature=val_temp,
                        heart_rate=val_hr,
                        crp=val_crp,
                        flags=obs_flags,
                        is_missing=is_missing,
                    )
                )

                r_counter += 1

        patients.append(
            SyntheticPatient(
                patient_id=patient_id,
                name=name,
                age=age,
                surgery=surgery,
                group=grp,
                onset_index=onset_index,
                strength=strength,
                readings=readings,
            )
        )

    return patients
