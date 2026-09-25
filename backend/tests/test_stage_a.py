"""Unit tests for Stage A of RECOVERY-SWARM.

Tests:
1. Configuration loading and thresholds (R1-R8 safety rules, required keys).
2. Canonical twin validation against TwinState and extra field rejection.
3. Scenario validation as ObservationIn with valid expect blocks.
4. Simulator load, advance, reset, and exact determinism.
"""

import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from app.config import config
from app.models.schemas import ObservationIn, TwinState
from app.simulator import Simulator

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "scenarios"


def test_config_loads():
    """Verify thresholds.yaml loads and contains R1-R8 and required top-level keys."""
    t = config.thresholds
    assert "scoring" in t
    assert "reference" in t
    assert "trajectory" in t
    assert "router" in t
    assert "safety_rules" in t
    assert "llm" in t

    rules = t["safety_rules"]
    for r_id in ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8"]:
        assert r_id in rules, f"Missing safety rule {r_id} in thresholds.yaml"


def test_canonical_twin_validates():
    """Verify canonical Meera twin JSON validates against TwinState and rejects extra fields."""
    meera_path = DATA_DIR / "meera_day4.json"
    assert meera_path.exists()

    with open(meera_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Validates cleanly
    twin = TwinState(**data)
    assert twin.patient_id == "P001"
    assert twin.profile.name == "Meera Sharma"
    assert twin.scores.recovery_score == 68

    # Extra field rejection check (extra="forbid")
    invalid_data = data.copy()
    invalid_data["extra_field"] = "should_fail"
    with pytest.raises(ValidationError):
        TwinState(**invalid_data)


def test_scenarios_validate():
    """Verify every scenario file validates observation steps against ObservationIn and has an expect block."""
    scenario_files = [
        "stable_recovery.json",
        "poor_sleep.json",
        "pain_spike.json",
        "increased_inflammation.json",
        "reduced_mobility.json",
        "recovery_deviation.json",
    ]

    for fname in scenario_files:
        fpath = DATA_DIR / fname
        assert fpath.exists(), f"Missing scenario file {fname}"

        with open(fpath, "r", encoding="utf-8") as f:
            sc_data = json.load(f)

        assert "name" in sc_data
        assert "description" in sc_data
        assert "seed" in sc_data
        assert "expect" in sc_data, f"Scenario {fname} missing 'expect' block"
        assert "steps" in sc_data, f"Scenario {fname} missing 'steps' array"

        for step in sc_data["steps"]:
            assert "minute_offset" in step
            obs_dict = step["observation"]
            if "timestamp" not in obs_dict:
                obs_dict["timestamp"] = "2026-09-21T08:00:00Z"
            # Should validate cleanly as ObservationIn
            obs = ObservationIn(**obs_dict)
            assert isinstance(obs.pain, float) or isinstance(obs.pain, int)


def test_simulator_advance_and_reset():
    """Verify simulator load, advance, reset, and determinism."""
    sim1 = Simulator(scenarios_dir=DATA_DIR)
    sim1.load("poor_sleep")

    obs_0 = sim1.reset()
    assert obs_0.sleep_hours == 4.0

    obs_60 = sim1.advance(60)
    assert obs_60.sleep_hours == 3.5

    # Reset returns to minute 0
    obs_reset = sim1.reset()
    assert obs_reset.sleep_hours == 4.0

    # Determinism test across 2 separate instances
    sim2 = Simulator(scenarios_dir=DATA_DIR)
    sim2.load("poor_sleep")

    obs1_adv = sim1.advance(60)
    obs2_adv = sim2.advance(60)
    assert obs1_adv.model_dump() == obs2_adv.model_dump()
