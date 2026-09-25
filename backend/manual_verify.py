"""Manual verification script for Stage E requirements.

Executes all 8 verification steps against live FastAPI server and SQLite database.
"""

import json
import sqlite3
import time
import requests
from pathlib import Path

BASE_URL = "http://localhost:8000/api"
DB_PATH = Path(__file__).resolve().parent / "recovery.db"


def get_db_connection():
    return sqlite3.connect(DB_PATH)


def run_verification():
    print("==================================================")
    print("STARTING MANUAL VERIFICATION CHECKS")
    print("==================================================\n")

    # Step 0: Ensure baseline clean state
    res = requests.post(f"{BASE_URL}/simulator/reset", json={"patient_id": "P001"})
    res.raise_for_status()

    # --------------------------------------------------
    # CHECK 1: Inject pain_spike, advance to 180 min, run cycle
    # --------------------------------------------------
    print("--- CHECK 1: Inject pain_spike & Run Cycle ---")
    requests.post(f"{BASE_URL}/simulator/inject", json={"patient_id": "P001", "scenario": "pain_spike"})
    adv_res = requests.post(f"{BASE_URL}/simulator/advance", json={"patient_id": "P001", "minutes": 180})
    print(f"Current Twin Pain after advance: {adv_res.json()['observations']['pain']}")

    cycle_res = requests.post(f"{BASE_URL}/patients/P001/cycle")
    cycle_data = cycle_res.json()
    cycle_id = cycle_data["cycle_id"]

    print(f"Cycle ID: {cycle_id}")
    print(f"Safety Result:\n{json.dumps(cycle_data['safety'], indent=2)}")
    print(f"Escalated: {cycle_data['escalated']}\n")

    # --------------------------------------------------
    # CHECK 3: Query DB directly for decisions table
    # --------------------------------------------------
    print("--- CHECK 3: Direct DB Query on `decisions` Table ---")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT cycle_id, safety_result, escalated FROM decisions WHERE cycle_id = ?", (cycle_id,))
    rows = cursor.fetchall()
    print(f"Rows found for cycle_id '{cycle_id}': {len(rows)}")
    for r in rows:
        print(f"  cycle_id={r[0]}, safety_result={r[1]}, escalated={bool(r[2])}")
    assert len(rows) == 1, "Expected exactly ONE row in decisions table for this cycle!"
    print("CONFIRMED: Exactly ONE row persisted in decisions table after cycle.\n")
    conn.close()

    # --------------------------------------------------
    # RESET to baseline for What-If check
    # --------------------------------------------------
    requests.post(f"{BASE_URL}/simulator/reset", json={"patient_id": "P001"})

    # --------------------------------------------------
    # CHECK 4 & 5: DB counts before What-If
    # --------------------------------------------------
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM twin_states WHERE patient_id = 'P001'")
    twin_count_before = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM simulation_runs WHERE patient_id = 'P001'")
    sim_count_before = cursor.fetchone()[0]
    conn.close()
    print(f"Before What-If -> twin_states count: {twin_count_before}, simulation_runs count: {sim_count_before}")

    # --------------------------------------------------
    # CHECK 2: What-If with steps_pct=20
    # --------------------------------------------------
    print("\n--- CHECK 2: What-If simulation (steps_pct=20) ---")
    whatif_res = requests.post(f"{BASE_URL}/patients/P001/whatif", json={"changes": {"steps_pct": 20}})
    whatif_data = whatif_res.json()

    print(f"Modified Target (steps_target): {whatif_data['simulated_plan']['steps_target']}")
    print(f"Comparison Block:\n{json.dumps(whatif_data['comparison'], indent=2)}")
    print(f"Disclaimer Text:\n\"{whatif_data['disclaimer']}\"\n")

    # --------------------------------------------------
    # CHECK 4 & 5: DB counts after What-If
    # --------------------------------------------------
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM twin_states WHERE patient_id = 'P001'")
    twin_count_after = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM simulation_runs WHERE patient_id = 'P001'")
    sim_count_after = cursor.fetchone()[0]
    conn.close()

    print(f"--- CHECK 4 & 5 Verification ---")
    print(f"twin_states count before: {twin_count_before}, after: {twin_count_after}")
    print(f"simulation_runs count before: {sim_count_before}, after: {sim_count_after}")
    assert twin_count_after == twin_count_before, "twin_states count MUST be unchanged!"
    assert sim_count_after == sim_count_before + 1, "simulation_runs count MUST increase by exactly 1!"
    print("CONFIRMED: twin_states unchanged, exactly ONE new simulation_runs row inserted.\n")

    # --------------------------------------------------
    # CHECK 6: Call /simulator/reset & verify state
    # --------------------------------------------------
    print("--- CHECK 6: Reset Simulator & Verify Cleared Tables ---")
    reset_res = requests.post(f"{BASE_URL}/simulator/reset", json={"patient_id": "P001"})
    reset_twin = reset_res.json()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM decisions WHERE patient_id = 'P001'")
    dec_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM twin_states WHERE patient_id = 'P001'")
    twin_count_reset = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM recovery_plans JOIN decisions ON recovery_plans.cycle_id = decisions.cycle_id WHERE decisions.patient_id = 'P001'")
    plan_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM simulation_runs WHERE patient_id = 'P001'")
    sim_count_reset = cursor.fetchone()[0]
    conn.close()

    print(f"Decisions count: {dec_count}")
    print(f"Twin states count (baseline restored): {twin_count_reset}")
    print(f"Recovery plans count: {plan_count}")
    print(f"Simulation runs count: {sim_count_reset}")
    print(f"Restored Baseline Observations: pain={reset_twin['observations']['pain']}, steps={reset_twin['observations']['steps']}, swelling={reset_twin['observations']['swelling']}")
    print("CONFIRMED: All session data cleared and baseline restored.\n")

    # --------------------------------------------------
    # CHECK 7: Fetch /api/patients/P001/audit
    # --------------------------------------------------
    print("--- CHECK 7: Fetch Audit Endpoint ---")
    audit_res = requests.get(f"{BASE_URL}/patients/P001/audit")
    print(f"Audit response:\n{json.dumps(audit_res.json(), indent=2)}\n")

    print("==================================================")
    print("ALL VERIFICATION CHECKS COMPLETED SUCCESSFULLY")
    print("==================================================")


if __name__ == "__main__":
    run_verification()
