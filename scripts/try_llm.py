"""Manual script to test Meera baseline and scenarios with real LLM calls (Stage D).

Usage:
  python scripts/try_llm.py
"""

import os
import sys
from pathlib import Path

# Add backend directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

import json
from app.agents.cache import LAST_RUN_STATS, get_today_usage_count
from app.graph import run_cycle
from app.models.schemas import TwinState


def main():
    # 1. Print today's count BEFORE making any calls
    today_count = get_today_usage_count()
    print(f"==================================================")
    print(f"Today's LLM calls so far: {today_count} (from data/llm_usage.json)")
    print(f"==================================================\n")

    os.environ["FALLBACK_MODE"] = "false"

    scenarios_dir = PROJECT_ROOT / "data" / "scenarios"
    with open(scenarios_dir / "meera_day4.json", "r", encoding="utf-8") as f:
        twin_data = json.load(f)
    twin = TwinState(**twin_data)

    print(f"Running cycle for Meera baseline ({twin.patient_id}, Day {twin.profile.post_op_day})...")
    res = run_cycle(twin, fallback=False)

    print("\n--- SWARM PROPOSALS ---")
    for p in res.proposals:
        print(f"[{p.agent.upper()}] Action: {p.action_type} (target: {p.target_value}) | Direction: {p.direction}")
        print(f"  Rationale: {p.rationale}")
        print(f"  Evidence: {', '.join(p.evidence)}")

    print("\n--- DEBATE STANCES ---")
    for s in res.stances:
        print(f"[{s.agent.upper()} -> {s.target_agent.upper()}] Stance: {s.stance.upper()} (conf: {s.revised_confidence})")
        print(f"  Message: {s.message}")

    print("\n--- SAFETY GUARDIAN RESULT ---")
    print(f"Result: {res.safety.result.upper()}")
    if res.safety.rules_triggered:
        for r in res.safety.rules_triggered:
            print(f"  Rule Triggered: {r.rule_id} -> {r.detail}")

    print("\n--- FINAL RECOVERY PLAN ---")
    if res.plan:
        print(f"Steps Target: {res.plan.steps_target}")
        print(f"Explanation: {res.plan.explanation}")
        print("High Priority:")
        for hp in res.plan.high_priority:
            print(f"  - {hp.action}: {hp.reason} (Target: {hp.target})")
    else:
        print("Plan: Escalated to clinician review.")

    print("\n--- CYCLE RUN STATS ---")
    print(f"LLM Calls: {LAST_RUN_STATS['llm_calls']}")
    print(f"Cached Calls: {LAST_RUN_STATS['cached_calls']}")
    print(f"Fallback Calls: {LAST_RUN_STATS['fallback_calls']}")
    print(f"Error Calls: {LAST_RUN_STATS['error_calls']}")

    new_today_count = get_today_usage_count()
    print(f"\nUpdated Today's LLM calls: {new_today_count} (from data/llm_usage.json)")


if __name__ == "__main__":
    main()
