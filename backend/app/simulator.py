"""Synthetic patient data & wearable stream simulator for RECOVERY-SWARM.

Guarantees byte-identical output for a given scenario + seed.
"""

import json
import random
from pathlib import Path
from typing import Any, Dict, Optional
from app.models.schemas import ObservationIn

SCENARIOS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "scenarios"


class Simulator:
    def __init__(self, scenarios_dir: Optional[Path] = None):
        self.scenarios_dir = scenarios_dir or SCENARIOS_DIR
        self.scenario_name: Optional[str] = None
        self.scenario_data: Optional[Dict[str, Any]] = None
        self.current_minute: int = 0
        self.rng: random.Random = random.Random(42)

    def load(self, scenario_name: str) -> Dict[str, Any]:
        """Loads a scenario file by name (e.g., 'poor_sleep' or 'meera_day4')."""
        file_path = self.scenarios_dir / f"{scenario_name}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Scenario '{scenario_name}' not found at {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            self.scenario_data = json.load(f)

        self.scenario_name = scenario_name
        self.current_minute = 0
        seed = self.scenario_data.get("seed", 42)
        self.rng = random.Random(seed)
        return self.scenario_data

    def reset(self) -> ObservationIn:
        """Resets the simulator to minute 0 and re-seeds the generator."""
        if not self.scenario_data:
            raise ValueError("No scenario loaded. Call load() first.")
        self.current_minute = 0
        seed = self.scenario_data.get("seed", 42)
        self.rng = random.Random(seed)
        return self.get_current_observation()

    def get_current_observation(self) -> ObservationIn:
        """Builds ObservationIn for the current minute_offset."""
        if not self.scenario_data:
            raise ValueError("No scenario loaded. Call load() first.")

        # Canonical baseline twin JSON format support (e.g. meera_day4)
        if "observations" in self.scenario_data and "steps" not in self.scenario_data:
            obs = self.scenario_data["observations"].copy()
            obs["timestamp"] = obs.get("timestamp", "2026-09-21T08:00:00Z")
            return ObservationIn(**obs)

        steps = self.scenario_data.get("steps", [])
        if not steps:
            raise ValueError(f"Scenario '{self.scenario_name}' has no steps defined.")

        # Find step matching current_minute or last available step before/at current_minute
        active_step = steps[0]
        for step in steps:
            if step["minute_offset"] <= self.current_minute:
                active_step = step
            else:
                break

        obs_dict = active_step["observation"].copy()
        if "timestamp" not in obs_dict:
            obs_dict["timestamp"] = f"2026-09-21T08:{self.current_minute % 60:02d}:00Z"

        return ObservationIn(**obs_dict)

    def advance(self, minutes: int = 60) -> ObservationIn:
        """Advances simulated time by specified minutes and returns ObservationIn."""
        if not self.scenario_data:
            raise ValueError("No scenario loaded. Call load() first.")

        self.current_minute += minutes
        return self.get_current_observation()
