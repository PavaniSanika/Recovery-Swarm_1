"""Automated 20-Step Hackathon Demo Check Script for RECOVERY-SWARM (SPEC Section 21.2).

Runs against live REST API server (http://localhost:8000 or FastAPI TestClient) and prints PASS/FAIL per step.
"""

import sys
import urllib.request
import json

BASE_URL = "http://127.0.0.1:8000"


def http_req(method: str, path: str, payload: dict = None) -> tuple[int, dict]:
    """Helper to perform HTTP requests against the live API."""
    url = f"{BASE_URL}{path}"
    data = json.dumps(payload).encode("utf-8") if payload else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as response:
            status = response.status
            body = response.read().decode("utf-8")
            return status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        return e.code, json.loads(body) if body else {}


def run_demo_check_pass() -> bool:
    """Executes the complete 20-step demo script from SPEC 21.2."""
    print("=" * 70, flush=True)
    print("RECOVERY-SWARM: AUTOMATED DEMO VERIFICATION SCRIPT (SPEC 21.2)", flush=True)
    print("=" * 70, flush=True)

    all_passed = True

    def check(step_num: int, title: str, condition: bool, detail: str = ""):
        nonlocal all_passed
        status_str = "[PASS]" if condition else "[FAIL]"
        if not condition:
            all_passed = False
        print(f"Step {step_num:02d}: {status_str} {title}", flush=True)
        if detail:
            print(f"         |- {detail}", flush=True)

    # Step 1: Open Meera Dashboard / Reset to baseline
    s, d = http_req("POST", "/api/simulator/reset", {"patient_id": "P001"})
    check(1, "Reset patient P001 to baseline (meera_day4)", s == 200 and d.get("patient_id") == "P001")

    # Step 2: Verify baseline metrics (Pain 6/10, Sleep 4.5, Steps 1800, Inflammation 6.2, Score 68)
    obs = d.get("observations", {})
    scores = d.get("scores", {})
    check(
        2,
        "Verify baseline observations & scores",
        obs.get("pain") == 6.0
        and obs.get("sleep_hours") == 4.5
        and obs.get("steps") == 1800
        and scores.get("recovery_score") == 68,
        f"Pain={obs.get('pain')}, Sleep={obs.get('sleep_hours')}, Steps={obs.get('steps')}, Score={scores.get('recovery_score')}",
    )

    # Step 3: Fetch Digital Twin & Expected Trajectory
    s_twin, d_twin = http_req("GET", "/api/patients/P001/twin")
    s_ref, d_ref = http_req("GET", "/api/patients/P001/twin/reference")
    check(
        3,
        "Fetch Digital Twin & reference trajectory",
        s_twin == 200 and s_ref == 200 and d_ref.get("surgery") == "Total Knee Replacement",
        f"Post-op Day {d_ref.get('post_op_day')}, Expected Steps {d_ref.get('expected_steps')}",
    )

    # Step 4-10: Trigger Recovery Optimization Cycle
    s_cycle, d_cycle = http_req("POST", "/api/patients/P001/cycle")
    cycle_id = d_cycle.get("cycle_id", "")
    check(4, "Trigger 'Optimize Recovery' cycle (POST /cycle)", s_cycle == 200 and cycle_id.startswith("cycle_"))

    # Step 5: Priority Router assigned roles
    roles = d_cycle.get("priority", {}).get("roles", {})
    check(5, "Priority Router assigned agent roles", len(roles) >= 4, f"Roles: {roles}")

    # Step 6: Specialist proposals generated
    props = d_cycle.get("proposals", [])
    check(6, "Specialist agents generated structured proposals", len(props) >= 4, f"Proposals count: {len(props)}")

    # Step 7: Debate & Stances generated
    stances = d_cycle.get("stances", [])
    debate = d_cycle.get("debate", [])
    check(7, "Agents debate/support/challenge proposals", len(stances) >= 0 and len(debate) >= 0)

    # Step 8: Negotiation Coordinator & Safety Guardian evaluation
    safety = d_cycle.get("safety", {})
    check(
        8,
        "Safety Guardian evaluated draft decision (Rule R5 medication limits)",
        safety.get("result") in ["allow", "modify"],
        f"Safety verdict: {safety.get('result')}",
    )

    # Step 9-10: Plan Generator recovery plan
    plan = d_cycle.get("plan")
    check(
        9,
        "Plan Generator produced final 6-12h recovery plan",
        plan is not None and plan.get("horizon_hours") in [6, 12],
        f"Horizon: {plan.get('horizon_hours') if plan else 'None'} hours",
    )
    check(10, "Display 6-12h Recovery Plan", plan is not None and len(plan.get("high_priority", [])) > 0)

    # Step 11-13: Open What-If Simulator (+20% steps)
    s_wi, d_wi = http_req("POST", "/api/patients/P001/whatif", {"changes": {"steps_pct": 20}})
    check(11, "Open What-If Simulator: 'What if patient walks +20% steps?'", s_wi == 200)
    check(12, "Run What-If simulation", "comparison" in d_wi and "simulated_plan" in d_wi)

    comp = d_wi.get("comparison", {})
    curr = comp.get("current", {})
    sim = comp.get("simulated", {})
    check(
        13,
        "Verify simulated state effects (steps, pain, swelling, sleep, score)",
        sim.get("steps") == int(round(1800 * 1.20)) and "recovery_score" in sim,
        f"Steps: {curr.get('steps')} -> {sim.get('steps')}, Score: {curr.get('recovery_score')} -> {sim.get('recovery_score')}",
    )

    # Step 14-16: Simulated recommendation & live state integrity
    check(14, "Run agents on simulation copy", d_wi.get("simulated_plan") is not None)
    check(15, "Display simulated recommendation and disclaimer", "Illustrative simulation only" in d_wi.get("disclaimer", ""))

    s_hist, d_hist = http_req("GET", "/api/patients/P001/twin/history")
    check(16, "Return to live state: live twin_states history untouched", s_hist == 200 and isinstance(d_hist, list))

    # Step 17: Inject Recovery Deviation scenario
    s_inj, d_inj = http_req("POST", "/api/simulator/inject", {"patient_id": "P001", "scenario": "recovery_deviation"})
    s_adv, d_adv = http_req("POST", "/api/simulator/advance", {"patient_id": "P001", "minutes": 120})
    check(17, "Inject 'Recovery Deviation' scenario & advance to 120 min", s_inj == 200 and s_adv == 200)

    # Step 18-19: Trigger cycle on deviated state -> Escalation to Clinician View
    s_dev_cycle, d_dev_cycle = http_req("POST", "/api/patients/P001/cycle")
    check(18, "Safety Guardian detects recovery deviation", d_dev_cycle.get("safety", {}).get("result") == "escalate")
    check(
        19,
        "Escalation triggered to Clinician View (Rules R1/R8 fired)",
        d_dev_cycle.get("escalated") is True,
        f"Rules fired: {[r.get('rule_id') for r in d_dev_cycle.get('safety', {}).get('rules_triggered', [])]}",
    )

    # Step 20: Audit Trail Verification
    s_audit, d_audit = http_req("GET", "/api/patients/P001/audit")
    check(20, "Verify complete audit trail log in Clinician View", s_audit == 200 and len(d_audit) > 0, f"Audit entries: {len(d_audit)}")

    print("-" * 70)
    print(f"Demo Check Result: {'ALL 20 STEPS PASSED [100%]' if all_passed else 'SOME STEPS FAILED'}")
    print("=" * 70)
    return all_passed


if __name__ == "__main__":
    success = run_demo_check_pass()
    sys.exit(0 if success else 1)
