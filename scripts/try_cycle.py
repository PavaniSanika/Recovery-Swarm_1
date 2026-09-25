"""Script to run recovery optimization cycles across all 7 synthetic scenario files.

Can be run from root or backend directory:
    .\\.venv\\Scripts\\python.exe ..\\scripts\\try_cycle.py
"""

import json
from pathlib import Path
import sys

# Ensure backend package is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.graph import run_cycle
from app.models.schemas import ObservationIn, TwinState
from app.twin.engine import TwinEngine

SCENARIOS_DIR = PROJECT_ROOT / "data" / "scenarios"
SCENARIO_NAMES = [
    "meera_day4",
    "stable_recovery",
    "poor_sleep",
    "increased_inflammation",
    "reduced_mobility",
    "pain_spike",
    "recovery_deviation",
]


def load_scenario_twin(scenario_name: str, meera_base: TwinState) -> TwinState:
    file_path = SCENARIOS_DIR / f"{scenario_name}.json"
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "steps" not in data:
        return TwinState(**data)

    twin = meera_base.model_copy(deep=True)
    for idx, step_item in enumerate(data["steps"]):
        obs_dict = step_item["observation"].copy()
        if "timestamp" not in obs_dict:
            obs_dict["timestamp"] = f"2026-09-21T08:{(idx * 15) % 60:02d}:00Z"
        obs = ObservationIn(**obs_dict)
        twin = TwinEngine.update(twin, obs)
    return twin


def main():
    print("=" * 80)
    print("RECOVERY-SWARM: Stage C2 Swarm Workflow Verification (All 7 Scenarios)")
    print("=" * 80)

    # Load baseline Meera twin
    meera_file = SCENARIOS_DIR / "meera_day4.json"
    with open(meera_file, "r", encoding="utf-8") as f:
        meera_base = TwinState(**json.load(f))

    for sc_name in SCENARIO_NAMES:
        print("\n" + "-" * 80)
        print(f"SCENARIO: {sc_name}")
        print("-" * 80)

        twin = load_scenario_twin(sc_name, meera_base)
        response = run_cycle(twin, fallback=True)

        print(f"Cycle ID:      {response.cycle_id}")
        print(f"Patient ID:    {response.twin.patient_id} ({response.twin.profile.name})")
        print(f"Recovery Score:{response.twin.scores.recovery_score}/100")
        print(f"Escalated:     {response.escalated}")
        print(f"Safety Result: {response.safety.result}")
        print(f"Rules Triggered: {[r.rule_id for r in response.safety.rules_triggered] or 'None'}")

        print("\nPriority Scores & Roles:")
        for agent_id, score in response.priority.priority_scores.items():
            role = response.priority.roles.get(agent_id, "supporting")
            print(f"  - {agent_id:15s}: {score:.4f} ({role})")

        print("\nProposals:")
        for p in response.proposals:
            tgt = f" target={int(p.target_value)}" if p.target_value is not None else ""
            print(f"  - [{p.agent.capitalize()}] {p.action_type} ({p.direction}){tgt} | Conf: {p.confidence:.2f}")
            print(f"    Rationale: {p.rationale}")

        print("\nDebate Log Summary:")
        for msg in response.debate:
            target_str = f" -> {msg.target_agent}" if msg.target_agent else ""
            print(f"  [Round {msg.round}] [{msg.agent.capitalize()} - {msg.status}{target_str}]: {msg.message}")

        if response.plan:
            print("\nFinal Plan:")
            print(f"  Horizon: {response.plan.horizon_hours} hours | Steps Target: {response.plan.steps_target}")
            print(f"  Safety Status: {response.plan.safety_status}")
            print(f"  High Priority Actions:")
            for hp in response.plan.high_priority:
                print(f"    * {hp.action}: {hp.reason} (Target: {hp.target})")
            print(f"  Medium Priority Actions:")
            for mp in response.plan.medium_priority:
                print(f"    * {mp.action}: {mp.reason}")
            print(f"  Monitoring: {', '.join(response.plan.monitoring)}")
        else:
            print("\nFinal Plan: NONE (Escalated to Clinician)")
            if response.safety and response.safety.modified_plan:
                interim = response.safety.modified_plan
                print("Interim guidance (not a final plan):")
                print(f"  Safety Status: {interim.safety_status}")
                print(f"  Actions:")
                for hp in interim.high_priority:
                    print(f"    * {hp.action}: {hp.reason} (Target: {hp.target})")
                print(f"  Monitoring: {', '.join(interim.monitoring)}")

    print("\n" + "=" * 80)
    print("Verification Completed Successfully.")
    print("=" * 80)


if __name__ == "__main__":
    main()
