"""What-If Simulation Engine for RECOVERY-SWARM (Stage E).

Executes what-if simulations on a deep-copied twin state, applying thresholds.yaml effect model.
Persists ONLY to simulation_runs table; live twin and twin_states are untouched.
"""

from datetime import datetime, timezone
import json
from typing import Any, Dict, Optional

from app.config import config
from app.db import SimulationRunModel, TwinStateModel
from app.graph import run_cycle
from app.models.schemas import (
    ObservationIn,
    SafetyResult,
    TwinState,
    WhatIfRequest,
    WhatIfResponse,
)
from app.twin.engine import TwinEngine

WHATIF_DISCLAIMER = (
    "Illustrative simulation only. Results are based on prototype assumptions and synthetic data and are not clinical predictions."
)


def run_whatif(
    twin: TwinState,
    request: WhatIfRequest,
    db_session: Optional[Any] = None,
) -> WhatIfResponse:
    """Runs a What-If simulation on a copy of the twin state."""
    twin_copy = twin.model_copy(deep=True)
    orig_obs = twin.observations.model_copy(deep=True)
    orig_recovery_score = twin.scores.recovery_score

    changes = request.changes or {}

    # 1. Determine baseline step change percentage
    old_steps = float(twin_copy.observations.steps)
    new_steps = old_steps

    if "steps_pct" in changes:
        pct = float(changes["steps_pct"])
        new_steps = old_steps * (1.0 + pct / 100.0)
    elif "steps" in changes:
        new_steps = float(changes["steps"])

    pct_chunks = ((new_steps - old_steps) / (old_steps * 0.10)) if old_steps > 0 else 0.0

    # 2. Apply effect model from thresholds.yaml
    effect_cfg = config.thresholds.get("whatif_effect_per_10pct_steps", {})
    is_moderate = twin_copy.observations.swelling >= 5.0
    eff_rates = effect_cfg.get("moderate_or_higher" if is_moderate else "below_moderate", {})

    d_pain = float(eff_rates.get("pain", 0.3 if is_moderate else 0.1)) * pct_chunks
    d_swelling = float(eff_rates.get("swelling", 0.4 if is_moderate else 0.1)) * pct_chunks
    d_sleep = float(eff_rates.get("sleep_hours", -0.1 if is_moderate else 0.0)) * pct_chunks

    # Direct change overrides if specified
    if "pain" in changes:
        twin_copy.observations.pain = float(changes["pain"])
    else:
        twin_copy.observations.pain = max(0.0, min(10.0, twin_copy.observations.pain + d_pain))

    if "swelling" in changes:
        twin_copy.observations.swelling = float(changes["swelling"])
    else:
        twin_copy.observations.swelling = max(0.0, min(10.0, twin_copy.observations.swelling + d_swelling))

    if "sleep_hours" in changes:
        twin_copy.observations.sleep_hours = float(changes["sleep_hours"])
    else:
        twin_copy.observations.sleep_hours = max(0.0, min(24.0, twin_copy.observations.sleep_hours + d_sleep))

    twin_copy.observations.steps = int(round(new_steps))

    night_awakenings = (
        int(changes["night_awakenings"])
        if "night_awakenings" in changes
        else twin_copy.observations.night_awakenings
    )

    # 3. Create synthetic observation to trigger TwinEngine recomputation
    obs_in = ObservationIn(
        timestamp=datetime.now(timezone.utc).isoformat(),
        pain=twin_copy.observations.pain,
        sleep_hours=twin_copy.observations.sleep_hours,
        steps=twin_copy.observations.steps,
        swelling=twin_copy.observations.swelling,
        temperature=twin_copy.observations.temperature,
        heart_rate=twin_copy.observations.heart_rate,
        crp=twin_copy.observations.crp,
        night_awakenings=night_awakenings,
        flags=twin_copy.observations.flags,
    )

    # 4. Recompute derived scores on simulation copy
    simulated_twin = TwinEngine.update(twin_copy, obs_in)

    # 5. Run cycle in simulation mode
    cycle_res = run_cycle(simulated_twin, fallback=False, is_simulation=True)

    # 6. Format comparison dictionary
    comparison = {
        "current": {
            "pain": round(orig_obs.pain, 1),
            "swelling": round(orig_obs.swelling, 1),
            "sleep_hours": round(orig_obs.sleep_hours, 1),
            "steps": orig_obs.steps,
            "recovery_score": orig_recovery_score,
        },
        "simulated": {
            "pain": round(simulated_twin.observations.pain, 1),
            "swelling": round(simulated_twin.observations.swelling, 1),
            "sleep_hours": round(simulated_twin.observations.sleep_hours, 1),
            "steps": simulated_twin.observations.steps,
            "recovery_score": simulated_twin.scores.recovery_score,
        },
    }

    # Format effect text summaries
    effects = {
        "pain": f"{d_pain:+.1f} points",
        "swelling": f"{d_swelling:+.1f} points",
        "sleep_hours": f"{d_sleep:+.1f} hours",
        "steps": f"{new_steps - old_steps:+.0f} steps",
    }

    # 7. Persist ONLY to simulation_runs table
    from app.db import SessionLocal
    db = db_session or SessionLocal()
    try:
        base_state = db.query(TwinStateModel).filter_by(patient_id=twin.patient_id).order_by(TwinStateModel.state_id.desc()).first()
        sim_run = SimulationRunModel(
            patient_id=twin.patient_id,
            base_state_id=base_state.state_id if base_state else None,
            changes=changes,
            sim_state_json=simulated_twin.model_dump(),
            simulated_plan=cycle_res.plan.model_dump() if cycle_res.plan else None,
            verdict=cycle_res.safety.result,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        db.add(sim_run)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        if not db_session:
            db.close()

    return WhatIfResponse(
        simulated_twin=simulated_twin,
        effects=effects,
        simulated_plan=cycle_res.plan,
        safety=cycle_res.safety,
        comparison=comparison,
        disclaimer=WHATIF_DISCLAIMER,
    )
