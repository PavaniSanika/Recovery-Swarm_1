"""Script to record LLM responses for all demo scenarios into data/cache/.

Usage:
  python scripts/record_demo_cache.py
"""

import os
import sys
from pathlib import Path

# Add backend directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

import json
from app.agents.cache import get_today_usage_count, reset_last_run_stats
from app.graph import run_cycle
from app.models.schemas import ObservationIn, TwinState
from app.simulator import Simulator


def main():
    os.environ["CACHE_MODE"] = "record"
    os.environ["FALLBACK_MODE"] = "false"

    print(f"Today's LLM calls so far: {get_today_usage_count()} (from data/llm_usage.json)", flush=True)
    print("Recording demo scenario responses to data/cache/...", flush=True)

    scenarios_dir = PROJECT_ROOT / "data" / "scenarios"
    with open(scenarios_dir / "meera_day4.json", "r", encoding="utf-8") as f:
        meera_base = TwinState(**json.load(f))

    scenarios = [
        "stable_recovery",
        "poor_sleep",
        "pain_spike",
        "increased_inflammation",
        "reduced_mobility",
        "recovery_deviation",
    ]

    sim = Simulator()

    for sc in scenarios:
        try:
            sc_data = sim.load(sc)
            twin = meera_base.model_copy(deep=True)
            obs = sim.get_current_observation()
            print(f"--- Recording scenario: {sc} ---", flush=True)
            reset_last_run_stats()
            res = run_cycle(twin, observation=obs, fallback=False)
            print(f"  Cycle ID: {res.cycle_id}, Steps Target: {res.plan.steps_target if res.plan else 'Escalated'}", flush=True)
        except Exception as e:
            print(f"  Error recording {sc}: {e}", flush=True)

    print("\nRecording complete! Responses cached in data/cache/.", flush=True)
    print(f"Updated today's LLM call count: {get_today_usage_count()}", flush=True)


if __name__ == "__main__":
    main()
