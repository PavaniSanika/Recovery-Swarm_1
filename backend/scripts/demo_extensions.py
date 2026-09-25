"""Automated 4-Step Extension Demo Verification Script for RECOVERY-SWARM (SPEC Section 21.3).

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


def run_extension_demo_pass() -> bool:
    """Executes the 4-step extension demo script from SPEC Section 21.3."""
    print("=" * 70, flush=True)
    print("RECOVERY-SWARM: EXTENSION DEMO VERIFICATION SCRIPT (SPEC 21.3)", flush=True)
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

    # Reset patient P001 to baseline first
    http_req("POST", "/api/simulator/reset", {"patient_id": "P001"})

    # Step 1: Digital Twin Baseline Meera (P001) & Screening Endpoint
    s_twin, d_twin = http_req("GET", "/api/patients/P001/twin")
    s_scr, d_scr = http_req("GET", "/api/patients/P001/screening")
    scr_disclaimer = d_scr.get("disclaimer", "")
    step1_cond = (
        s_twin == 200
        and s_scr == 200
        and d_twin.get("patient_id") == "P001"
        and "Screening flag only. Not a diagnosis. Clinician review required." in scr_disclaimer
    )
    check(
        1,
        "Digital Twin baseline & screening API with mandatory disclaimer",
        step1_cond,
        f"Patient ID={d_twin.get('patient_id')}, Post-Op Day={d_twin.get('profile', {}).get('post_op_day')}, Disclaimer verified",
    )

    # Step 2: Interactive State Change (Inject Increased Inflammation & Advance 120m)
    s_inj1, d_inj1 = http_req("POST", "/api/simulator/inject", {"patient_id": "P001", "scenario": "increased_inflammation"})
    s_adv1, d_adv1 = http_req("POST", "/api/simulator/advance", {"patient_id": "P001", "minutes": 120})
    s_twin2, d_twin2 = http_req("GET", "/api/patients/P001/twin")
    obs2 = d_twin2.get("observations", {})
    scores2 = d_twin2.get("scores", {})
    step2_cond = s_inj1 == 200 and s_adv1 == 200 and s_twin2 == 200 and (obs2.get("crp", 0) >= 6.5 or scores2.get("inflammation_score", 0) >= 6.5)
    check(
        2,
        "Inject 'increased_inflammation' & verify digital twin telemetry change",
        step2_cond,
        f"CRP={obs2.get('crp')}, Inflammation Score={scores2.get('inflammation_score')}",
    )

    # Step 3: Inject Recovery Deviation, Advance 120m & Verify Active Screening Flags with Honest Wording
    s_inj2, d_inj2 = http_req("POST", "/api/simulator/inject", {"patient_id": "P001", "scenario": "recovery_deviation"})
    s_adv2, d_adv2 = http_req("POST", "/api/simulator/advance", {"patient_id": "P001", "minutes": 120})
    s_scr3, d_scr3 = http_req("GET", "/api/patients/P001/screening")
    flags3 = d_scr3.get("flags", [])
    disclaimer3 = d_scr3.get("disclaimer", "")
    step3_cond = (
        s_inj2 == 200
        and s_adv2 == 200
        and s_scr3 == 200
        and len(flags3) > 0
        and disclaimer3 == "Screening flag only. Not a diagnosis. Clinician review required."
    )
    check(
        3,
        "Inject 'recovery_deviation' & verify active screening flags + mandatory disclaimer",
        step3_cond,
        f"Flags count={len(flags3)}, Flag titles={[f.get('title') for f in flags3]}, Disclaimer exact match verified",
    )

    # Step 4: Technical Synthetic Cohort Evaluation Panel (200 Patients)
    s_eval, d_eval = http_req("POST", "/api/evaluation/run", {"cohort_size": 200, "seed": 2026})
    s_latest, d_latest = http_req("GET", "/api/evaluation/latest")
    sens_overall = d_latest.get("sensitivity_overall", 0)
    fa_lenient = d_latest.get("false_alarm_rate_lenient", 1.0)
    safety_obj = d_latest.get("safety", {})
    eval_disclaimer = d_latest.get("disclaimer", "")
    safety_ok = (
        safety_obj.get("max_step_increase_ok") is True
        and safety_obj.get("no_forbidden_medication_terms") is True
        and safety_obj.get("urgent_implies_escalation") is True
        and safety_obj.get("deterministic_rerun") is True
    )
    step4_cond = (
        s_eval == 200
        and s_latest == 200
        and sens_overall >= 0.80
        and fa_lenient < 0.50
        and safety_ok
        and eval_disclaimer == "Technical evaluation on synthetic data. Not clinical validation."
    )
    check(
        4,
        "Run synthetic cohort evaluation (200 patients) & verify benchmark metrics & safety invariants",
        step4_cond,
        f"Strict Sensitivity={sens_overall*100:.1f}%, Lenient False Alarm={fa_lenient*100:.1f}%, Safety Invariants Passed={safety_ok}, Mandatory Disclaimer verified",
    )

    print("-" * 70, flush=True)
    print(f"Extension Demo Check Result: {'ALL 4 STEPS PASSED [100%]' if all_passed else 'SOME STEPS FAILED'}", flush=True)
    print("=" * 70, flush=True)
    return all_passed


if __name__ == "__main__":
    success = run_extension_demo_pass()
    sys.exit(0 if success else 1)
