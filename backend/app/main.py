"""FastAPI Application for RECOVERY-SWARM (Stage E).

Implements all REST and WebSocket contracts from CONTRACTS Section 7.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import config
from app.db import (
    AgentProposalModel,
    DebateMessageModel,
    DecisionModel,
    ObservationModel,
    PatientModel,
    RecoveryPlanModel,
    SafetyEventModel,
    SimulationRunModel,
    TwinStateModel,
    EvaluationRunModel,
    get_db,
    init_db,
)
from app.graph import astream_cycle, persist_cycle_data, run_cycle
from app.models.schemas import (
    CycleResponse,
    DebateMessage,
    HistoryEntry,
    ObservationIn,
    Plan,
    SafetyResult,
    TwinState,
    WhatIfRequest,
    WhatIfResponse,
    SimulatorStatus,
    TwinReference,
)
from app.models.extensions import ScreeningResult, EvaluationRunRequest, EvaluationReport
from app.workflow.screening import screen
from app.evaluation.runner import run_evaluation
from app.simulator import Simulator
from app.twin.engine import TwinEngine
from app.twin.reference import (
    get_surgery_reference,
    get_expected_pain,
    get_expected_inflammation,
    get_step_target,
)
from app.whatif import run_whatif
from app.ws import ws_manager

# Active simulator instance
simulator = Simulator()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables and seed Meera baseline
    init_db()
    yield


app = FastAPI(
    title="RECOVERY-SWARM API",
    description="Multi-Agent Recovery System API for Post-Op Knee Recovery",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Pydantic Input Schemas for Simulator/Review Endpoints ----------

class InjectRequest(BaseModel):
    patient_id: str = "P001"
    scenario: str


class AdvanceRequest(BaseModel):
    patient_id: str = "P001"
    minutes: int = 60


class ResetRequest(BaseModel):
    patient_id: str = "P001"


class ClinicianReviewRequest(BaseModel):
    note: str
    action: str = "acknowledge"


# ---------- Helper to get current TwinState from DB ----------

def get_patient_current_twin(patient_id: str, db: Session) -> TwinState:
    state_row = (
        db.query(TwinStateModel)
        .filter_by(patient_id=patient_id)
        .order_by(TwinStateModel.state_id.desc())
        .first()
    )
    if not state_row:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "PATIENT_NOT_FOUND", "message": f"Patient '{patient_id}' not found."}},
        )
    return TwinState(**state_row.twin_json)


# ---------- REST Endpoints (CONTRACTS Section 7) ----------

@app.post("/api/patients/{patient_id}/observations", response_model=TwinState)
def add_observation(patient_id: str, obs_in: ObservationIn, db: Session = Depends(get_db)):
    """Receives observation, updates Digital Twin using TwinEngine, persists state, and returns updated TwinState."""
    patient = db.query(PatientModel).filter_by(patient_id=patient_id).first()
    if not patient:
        patient = PatientModel(
            patient_id=patient_id,
            name="Meera Sharma",
            age=62,
            surgery="Total Knee Replacement",
            surgery_date="2026-09-17",
            care_plan={},
        )
        db.add(patient)

    current_twin = get_patient_current_twin(patient_id, db)
    updated_twin = TwinEngine.update(current_twin, obs_in)

    # Save observation row
    obs_row = ObservationModel(
        patient_id=patient_id,
        timestamp=obs_in.timestamp,
        pain=obs_in.pain,
        sleep_hours=obs_in.sleep_hours,
        steps=obs_in.steps,
        swelling=obs_in.swelling,
        temperature=obs_in.temperature,
        heart_rate=obs_in.heart_rate,
        crp=obs_in.crp,
        night_awakenings=obs_in.night_awakenings,
        flags=obs_in.flags,
    )
    db.add(obs_row)

    # Save new twin state row
    state_row = TwinStateModel(
        patient_id=patient_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        twin_json=updated_twin.model_dump(),
        recovery_score=updated_twin.scores.recovery_score,
        trajectory_overall=updated_twin.trajectory.overall,
    )
    db.add(state_row)
    db.commit()

    return updated_twin


@app.get("/api/patients/{patient_id}/twin", response_model=TwinState)
def get_twin(patient_id: str, db: Session = Depends(get_db)):
    """Returns current TwinState for patient_id."""
    return get_patient_current_twin(patient_id, db)


@app.get("/api/patients/{patient_id}/twin/history", response_model=List[HistoryEntry])
def get_twin_history(patient_id: str, db: Session = Depends(get_db)):
    """Returns history list from current TwinState."""
    twin = get_patient_current_twin(patient_id, db)
    return twin.history


@app.get("/api/patients/{patient_id}/twin/reference", response_model=TwinReference)
def get_twin_reference(patient_id: str, db: Session = Depends(get_db)):
    """Returns expected reference trajectory metrics sourced directly from thresholds.yaml."""
    twin = get_patient_current_twin(patient_id, db)
    surgery = twin.profile.surgery
    day = twin.profile.post_op_day

    ref_data = get_surgery_reference(surgery)

    return TwinReference(
        surgery=surgery,
        post_op_day=day,
        expected_pain=get_expected_pain(surgery, day),
        expected_inflammation=get_expected_inflammation(surgery, day),
        expected_steps=get_step_target(surgery, day),
        curves={
            "pain": {str(k): float(v) for k, v in ref_data.get("pain", {}).items()},
            "inflammation": {str(k): float(v) for k, v in ref_data.get("inflammation", {}).items()},
            "step_target": {str(k): float(v) for k, v in ref_data.get("step_target", {}).items()},
        },
    )


@app.get("/api/patients/{patient_id}/screening", response_model=ScreeningResult)
def get_patient_screening(patient_id: str, db: Session = Depends(get_db)):
    """Returns ScreeningResult for current patient twin state, history, and latest observation flags."""
    twin = get_patient_current_twin(patient_id, db)
    latest_obs = (
        db.query(ObservationModel)
        .filter_by(patient_id=patient_id)
        .order_by(ObservationModel.obs_id.desc())
        .first()
    )
    flags = latest_obs.flags if (latest_obs and latest_obs.flags) else twin.observations.flags
    return screen(twin=twin, flags=flags, history=twin.history)


@app.post("/api/evaluation/run", response_model=EvaluationReport)
def run_evaluation_endpoint(req: EvaluationRunRequest = EvaluationRunRequest(), db: Session = Depends(get_db)):
    """Executes synthetic cohort technical evaluation, persists to DB, and returns EvaluationReport."""
    report = run_evaluation(req)
    
    # Save to evaluation_runs DB table
    run_row = EvaluationRunModel(
        run_id=report.run_id,
        created_at=report.created_at,
        seed=report.seed,
        cohort_size=report.cohort_size,
        report_json=report.model_dump(),
    )
    db.add(run_row)
    db.commit()
    
    return report


@app.get("/api/evaluation/latest", response_model=EvaluationReport)
def get_latest_evaluation(db: Session = Depends(get_db)):
    """Returns the most recent EvaluationReport from evaluation_runs database table."""
    row = (
        db.query(EvaluationRunModel)
        .order_by(EvaluationRunModel.created_at.desc())
        .first()
    )
    if not row:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "EVALUATION_NOT_FOUND", "message": "No evaluation runs found in database."}},
        )
    return EvaluationReport(**row.report_json)


@app.post("/api/patients/{patient_id}/cycle", response_model=CycleResponse)
async def run_recovery_cycle(
    patient_id: str,
    fallback: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Executes a full recovery optimization cycle, streams WebSocket updates in real-time as LangGraph nodes complete, persists results, and returns CycleResponse."""
    try:
        twin = get_patient_current_twin(patient_id, db)
        if fallback is None:
            fallback_setting = config.fallback_mode or os.getenv("FALLBACK_MODE", "false").lower() == "true"
        else:
            fallback_setting = fallback

        cycle_id = None
        accumulated_state: Dict[str, Any] = {}
        priority_res = None
        sent_debate_count = 0

        async for cid, step in astream_cycle(twin, fallback=fallback_setting, is_simulation=False):
            cycle_id = cid
            for node_name, node_update in step.items():
                accumulated_state.update(node_update)

                if node_name == "twin_builder" and "twin" in node_update:
                    await ws_manager.broadcast(patient_id, "twin_update", node_update["twin"].model_dump())

                elif node_name == "priority_router" and "priority_result" in node_update:
                    priority_res = node_update["priority_result"]
                    for agent_id, role in priority_res.roles.items():
                        await ws_manager.broadcast(
                            patient_id,
                            "agent_status",
                            {
                                "agent": agent_id,
                                "status": "Analyzing",
                                "confidence": priority_res.priority_scores.get(agent_id, 0.5),
                                "recommendation": "Analyzing twin observations...",
                                "role": role,
                            },
                        )

                elif node_name in ["mobility", "inflammation", "medication", "sleep"] and "r1_proposals" in node_update:
                    for p in node_update["r1_proposals"]:
                        role = priority_res.roles.get(p.agent, "supporting") if priority_res else "supporting"
                        await ws_manager.broadcast(
                            patient_id,
                            "agent_status",
                            {
                                "agent": p.agent,
                                "status": "Analyzing",
                                "confidence": p.confidence,
                                "recommendation": f"{p.action_type} ({p.direction})",
                                "role": role,
                            },
                        )

                elif node_name == "debate_round":
                    if "debate_messages" in node_update:
                        all_messages = node_update["debate_messages"]
                        new_messages = all_messages[sent_debate_count:]
                        sent_debate_count = len(all_messages)
                        for msg in new_messages:
                            await ws_manager.broadcast(patient_id, "debate_message", msg.model_dump())

                    if "proposals" in node_update:
                        for p in node_update["proposals"]:
                            role = priority_res.roles.get(p.agent, "supporting") if priority_res else "supporting"
                            status_val = "Revising" if p.agent == "mobility" else "Supporting"
                            await ws_manager.broadcast(
                                patient_id,
                                "agent_status",
                                {
                                    "agent": p.agent,
                                    "status": status_val,
                                    "confidence": p.confidence,
                                    "recommendation": f"{p.action_type} ({p.direction})",
                                    "role": role,
                                },
                            )

                elif node_name == "coordinator":
                    if "debate_messages" in node_update:
                        all_messages = node_update["debate_messages"]
                        new_messages = all_messages[sent_debate_count:]
                        sent_debate_count = len(all_messages)
                        for msg in new_messages:
                            await ws_manager.broadcast(patient_id, "debate_message", msg.model_dump())

                elif node_name == "safety_guardian":
                    if "safety_result" in node_update:
                        s_res = node_update["safety_result"]
                        await ws_manager.broadcast(patient_id, "safety", s_res.model_dump())
                        if s_res.result == "escalate" or node_update.get("escalated"):
                            await ws_manager.broadcast(
                                patient_id,
                                "escalation",
                                {"cycle_id": cycle_id, "summary": "Clinician escalation triggered by Safety Guardian."},
                            )
                    if "debate_messages" in node_update:
                        all_messages = node_update["debate_messages"]
                        new_messages = all_messages[sent_debate_count:]
                        sent_debate_count = len(all_messages)
                        for msg in new_messages:
                            await ws_manager.broadcast(patient_id, "debate_message", msg.model_dump())

                elif node_name == "plan_generator":
                    if "final_plan" in node_update and node_update["final_plan"]:
                        await ws_manager.broadcast(patient_id, "plan", node_update["final_plan"].model_dump())
                        if "proposals" in accumulated_state:
                            for p in accumulated_state["proposals"]:
                                role = priority_res.roles.get(p.agent, "supporting") if priority_res else "supporting"
                                await ws_manager.broadcast(
                                    patient_id,
                                    "agent_status",
                                    {
                                        "agent": p.agent,
                                        "status": "Approved",
                                        "confidence": p.confidence,
                                        "recommendation": f"{p.action_type} ({p.direction})",
                                        "role": role,
                                    },
                                )

        # Persist non-simulation cycle data to SQLite DB
        if cycle_id:
            persist_cycle_data(accumulated_state, cycle_id)

        from app.models.schemas import PriorityResult as PRModel
        response = CycleResponse(
            cycle_id=cycle_id or "cycle_0000",
            priority=accumulated_state.get("priority_result")
            or PRModel(
                priority_scores={"mobility": 0.5, "inflammation": 0.5, "medication": 0.5, "sleep": 0.5},
                roles={"mobility": "supporting", "inflammation": "supporting", "medication": "supporting", "sleep": "supporting"},
            ),
            proposals=accumulated_state.get("proposals") or [],
            stances=accumulated_state.get("stances") or [],
            coalitions=accumulated_state.get("coalitions") or [],
            debate=accumulated_state.get("debate_messages") or [],
            safety=accumulated_state.get("safety_result")
            or SafetyResult(result="allow", rules_triggered=[], modified_plan=None),
            plan=accumulated_state.get("final_plan"),
            escalated=accumulated_state.get("escalated", False),
            twin=accumulated_state.get("twin", twin),
        )
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "CYCLE_EXECUTION_ERROR", "message": f"Optimization cycle failed: {str(e)}"}},
        ) from e


@app.get("/api/patients/{patient_id}/decisions")
def get_patient_decisions(patient_id: str, db: Session = Depends(get_db)):
    """Returns past decision summaries for patient_id."""
    decisions = (
        db.query(DecisionModel)
        .filter_by(patient_id=patient_id)
        .order_by(DecisionModel.created_at.desc())
        .all()
    )
    result = []
    for d in decisions:
        result.append(
            {
                "cycle_id": d.cycle_id,
                "created_at": d.created_at,
                "safety_result": d.safety_result,
                "escalated": d.escalated,
                "plan": d.recovery_plan.plan_json if d.recovery_plan else None,
            }
        )
    return result


@app.get("/api/patients/{patient_id}/plan/latest", response_model=Plan)
def get_latest_plan(patient_id: str, db: Session = Depends(get_db)):
    """Returns the latest active Plan for patient_id."""
    plan_row = (
        db.query(RecoveryPlanModel)
        .join(DecisionModel)
        .filter(DecisionModel.patient_id == patient_id)
        .order_by(RecoveryPlanModel.plan_id.desc())
        .first()
    )
    if not plan_row:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "PLAN_NOT_FOUND", "message": "No active plan found."}},
        )
    return Plan(**plan_row.plan_json)


@app.get("/api/decisions/{cycle_id}/debate")
def get_decision_debate(cycle_id: str, db: Session = Depends(get_db)):
    """Returns proposals, stances, debate messages, and safety events for a cycle."""
    decision = db.query(DecisionModel).filter_by(cycle_id=cycle_id).first()
    if not decision:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "CYCLE_NOT_FOUND", "message": f"Cycle '{cycle_id}' not found."}},
        )

    props = [p.__dict__ for p in decision.agent_proposals]
    for p in props:
        p.pop("_sa_instance_state", None)

    msgs = [m.__dict__ for m in decision.debate_messages]
    for m in msgs:
        m.pop("_sa_instance_state", None)

    events = [e.__dict__ for e in decision.safety_events]
    for e in events:
        e.pop("_sa_instance_state", None)

    return {
        "proposals": props,
        "stances": [],
        "debate": msgs,
        "safety_events": events,
    }


@app.get("/api/patients/{patient_id}/audit")
def get_patient_audit(patient_id: str, db: Session = Depends(get_db)):
    """Returns audit log list of safety events and decisions for Clinician View."""
    decisions = (
        db.query(DecisionModel)
        .filter_by(patient_id=patient_id)
        .order_by(DecisionModel.created_at.asc())
        .all()
    )
    audit = []
    for d in decisions:
        for ev in d.safety_events:
            audit.append(
                {
                    "timestamp": ev.timestamp,
                    "cycle_id": d.cycle_id,
                    "actor": "SafetyGuardian",
                    "event": f"Safety evaluation result: {ev.outcome}",
                    "rule_id": ev.rule_id if ev.rule_id != "R_ALLOW" else None,
                    "outcome": ev.outcome,
                }
            )
        audit.append(
            {
                "timestamp": d.created_at,
                "cycle_id": d.cycle_id,
                "actor": "NegotiationCoordinator",
                "event": f"Coordinator decision reached (steps target: {d.draft_plan.get('steps_target') if d.draft_plan else 'Escalated'})",
                "rule_id": None,
                "outcome": d.safety_result,
            }
        )
    return audit


@app.post("/api/patients/{patient_id}/whatif", response_model=WhatIfResponse)
def simulate_whatif(patient_id: str, request: WhatIfRequest, db: Session = Depends(get_db)):
    """Runs a What-If simulation and returns WhatIfResponse (persisting only to simulation_runs)."""
    twin = get_patient_current_twin(patient_id, db)
    return run_whatif(twin, request, db_session=db)


# ---------- Demo Mode / Simulator Endpoints ----------

@app.post("/api/simulator/inject", response_model=TwinState)
def simulator_inject(req: InjectRequest, db: Session = Depends(get_db)):
    """Injects a scenario file into patient observations."""
    simulator.load(req.scenario)
    obs = simulator.get_current_observation()

    current_twin = get_patient_current_twin(req.patient_id, db)
    updated_twin = TwinEngine.update(current_twin, obs)

    # Save new twin state row
    state_row = TwinStateModel(
        patient_id=req.patient_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        twin_json=updated_twin.model_dump(),
        recovery_score=updated_twin.scores.recovery_score,
        trajectory_overall=updated_twin.trajectory.overall,
    )
    db.add(state_row)
    db.commit()

    return updated_twin


@app.post("/api/simulator/advance", response_model=TwinState)
def simulator_advance(req: AdvanceRequest, db: Session = Depends(get_db)):
    """Advances simulated time by specified minutes and updates Digital Twin."""
    if not simulator.scenario_data:
        simulator.load("stable_recovery")

    obs = simulator.advance(req.minutes)
    current_twin = get_patient_current_twin(req.patient_id, db)
    updated_twin = TwinEngine.update(current_twin, obs)

    state_row = TwinStateModel(
        patient_id=req.patient_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        twin_json=updated_twin.model_dump(),
        recovery_score=updated_twin.scores.recovery_score,
        trajectory_overall=updated_twin.trajectory.overall,
    )
    db.add(state_row)
    db.commit()

    return updated_twin


@app.post("/api/simulator/reset", response_model=TwinState)
def simulator_reset(req: ResetRequest, db: Session = Depends(get_db)):
    """Resets patient P001 data: deletes all twin_states, decisions, plans, simulations, and restores baseline Meera Day 4."""
    pid = req.patient_id

    # Get decision cycle_ids for child deletions
    decision_ids = [d.cycle_id for d in db.query(DecisionModel.cycle_id).filter_by(patient_id=pid).all()]
    if decision_ids:
        db.query(RecoveryPlanModel).filter(RecoveryPlanModel.cycle_id.in_(decision_ids)).delete(synchronize_session=False)
        db.query(SafetyEventModel).filter(SafetyEventModel.cycle_id.in_(decision_ids)).delete(synchronize_session=False)
        db.query(DebateMessageModel).filter(DebateMessageModel.cycle_id.in_(decision_ids)).delete(synchronize_session=False)
        db.query(AgentProposalModel).filter(AgentProposalModel.cycle_id.in_(decision_ids)).delete(synchronize_session=False)

    db.query(DecisionModel).filter_by(patient_id=pid).delete(synchronize_session=False)
    db.query(SimulationRunModel).filter_by(patient_id=pid).delete(synchronize_session=False)
    db.query(ObservationModel).filter_by(patient_id=pid).delete(synchronize_session=False)
    db.query(TwinStateModel).filter_by(patient_id=pid).delete(synchronize_session=False)
    db.commit()

    # Re-seed Meera baseline from meera_day4.json
    scenarios_dir = Path(__file__).resolve().parent.parent.parent / "data" / "scenarios"
    with open(scenarios_dir / "meera_day4.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    baseline_twin = TwinState(**data)

    state_row = TwinStateModel(
        patient_id=pid,
        timestamp=datetime.now(timezone.utc).isoformat(),
        twin_json=baseline_twin.model_dump(),
        recovery_score=baseline_twin.scores.recovery_score,
        trajectory_overall=baseline_twin.trajectory.overall,
    )
    db.add(state_row)
    db.commit()

    simulator.scenario_data = None
    return baseline_twin


@app.get("/api/patients/{patient_id}/simulator/status", response_model=SimulatorStatus)
def get_simulator_status(patient_id: str, db: Session = Depends(get_db)):
    """Returns active scenario status metadata (scenario_name, step_index, total_steps, minute_offset, max_minute_offset)."""
    # Validate patient exists (same as get_twin)
    get_patient_current_twin(patient_id, db)

    if not simulator.scenario_name or not simulator.scenario_data:
        return SimulatorStatus(
            scenario_name=None,
            step_index=0,
            total_steps=0,
            minute_offset=0,
            max_minute_offset=0,
        )

    steps = simulator.scenario_data.get("steps", [])
    total_steps = len(steps)
    max_minute_offset = steps[-1].get("minute_offset", 0) if steps else 0

    step_index = 1
    for idx, s in enumerate(steps, start=1):
        if s.get("minute_offset", 0) <= simulator.current_minute:
            step_index = idx
        else:
            break

    return SimulatorStatus(
        scenario_name=simulator.scenario_name,
        step_index=step_index if total_steps > 0 else 0,
        total_steps=total_steps,
        minute_offset=simulator.current_minute,
        max_minute_offset=max_minute_offset,
    )


@app.post("/api/decisions/{cycle_id}/clinician-review")
def clinician_review(cycle_id: str, req: ClinicianReviewRequest, db: Session = Depends(get_db)):
    """Acknowledges or records clinician review note."""
    decision = db.query(DecisionModel).filter_by(cycle_id=cycle_id).first()
    if not decision:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "CYCLE_NOT_FOUND", "message": f"Cycle '{cycle_id}' not found."}},
        )
    return {"ok": True}


# ---------- Real-time WebSocket Endpoint ----------

@app.websocket("/ws/patients/{patient_id}")
async def websocket_endpoint(websocket: WebSocket, patient_id: str):
    """WebSocket streaming endpoint for patient cycle events."""
    await ws_manager.connect(websocket, patient_id)
    try:
        while True:
            # Keep connection open and receive optional messages
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, patient_id)
