"""Database models and session management for RECOVERY-SWARM (Stage E).

Database-neutral SQLAlchemy 2 configuration using JSON columns.
Default engine derived from DATABASE_URL (sqlite:///./recovery.db).
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from app.config import config
from app.models.schemas import TwinState

# Database engine setup with production connection pooling
database_url = config.database_url
if database_url.startswith("sqlite"):
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_size=10,
        max_overflow=20,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ---------- SQLAlchemy 2 Models (CONTRACTS Section 6) ----------

class PatientModel(Base):
    __tablename__ = "patients"

    patient_id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    surgery = Column(String(100), nullable=False)
    surgery_date = Column(String(50), nullable=False)
    care_plan = Column(JSON, nullable=True)

    observations = relationship("ObservationModel", back_populates="patient", cascade="all, delete-orphan")
    twin_states = relationship("TwinStateModel", back_populates="patient", cascade="all, delete-orphan")
    decisions = relationship("DecisionModel", back_populates="patient", cascade="all, delete-orphan")
    simulation_runs = relationship("SimulationRunModel", back_populates="patient", cascade="all, delete-orphan")


class ObservationModel(Base):
    __tablename__ = "observations"

    obs_id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String(50), ForeignKey("patients.patient_id"), nullable=False)
    timestamp = Column(String(50), nullable=False)
    pain = Column(Float, nullable=False)
    sleep_hours = Column(Float, nullable=False)
    steps = Column(Integer, nullable=False)
    swelling = Column(Float, nullable=False)
    temperature = Column(Float, nullable=False)
    heart_rate = Column(Integer, nullable=False)
    crp = Column(Float, nullable=False)
    night_awakenings = Column(Integer, nullable=True)
    flags = Column(JSON, nullable=True)

    patient = relationship("PatientModel", back_populates="observations")


class TwinStateModel(Base):
    __tablename__ = "twin_states"

    state_id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String(50), ForeignKey("patients.patient_id"), nullable=False)
    timestamp = Column(String(50), nullable=False)
    twin_json = Column(JSON, nullable=False)
    recovery_score = Column(Integer, nullable=False)
    trajectory_overall = Column(String(50), nullable=False)

    patient = relationship("PatientModel", back_populates="twin_states")
    decisions = relationship("DecisionModel", back_populates="twin_state")
    simulation_runs = relationship("SimulationRunModel", back_populates="base_twin_state")


class DecisionModel(Base):
    __tablename__ = "decisions"

    cycle_id = Column(String(50), primary_key=True)
    patient_id = Column(String(50), ForeignKey("patients.patient_id"), nullable=False)
    state_id = Column(Integer, ForeignKey("twin_states.state_id"), nullable=True)
    priority_scores = Column(JSON, nullable=True)
    lead_agents = Column(JSON, nullable=True)
    coalitions = Column(JSON, nullable=True)
    draft_plan = Column(JSON, nullable=True)
    safety_result = Column(String(50), nullable=False)
    escalated = Column(Boolean, nullable=False, default=False)
    created_at = Column(String(50), nullable=False)

    patient = relationship("PatientModel", back_populates="decisions")
    twin_state = relationship("TwinStateModel", back_populates="decisions")
    agent_proposals = relationship("AgentProposalModel", back_populates="decision", cascade="all, delete-orphan")
    debate_messages = relationship("DebateMessageModel", back_populates="decision", cascade="all, delete-orphan")
    safety_events = relationship("SafetyEventModel", back_populates="decision", cascade="all, delete-orphan")
    recovery_plan = relationship("RecoveryPlanModel", back_populates="decision", uselist=False, cascade="all, delete-orphan")


class AgentProposalModel(Base):
    __tablename__ = "agent_proposals"

    proposal_id = Column(Integer, primary_key=True, autoincrement=True)
    cycle_id = Column(String(50), ForeignKey("decisions.cycle_id"), nullable=False)
    agent = Column(String(50), nullable=False)
    action_type = Column(String(50), nullable=False)
    direction = Column(String(50), nullable=False)
    target_value = Column(Float, nullable=True)
    confidence = Column(Float, nullable=False)
    evidence = Column(JSON, nullable=True)
    rationale = Column(Text, nullable=False)
    risks = Column(JSON, nullable=True)
    round = Column(Integer, nullable=False, default=1)

    decision = relationship("DecisionModel", back_populates="agent_proposals")


class DebateMessageModel(Base):
    __tablename__ = "debate_messages"

    msg_id = Column(Integer, primary_key=True, autoincrement=True)
    cycle_id = Column(String(50), ForeignKey("decisions.cycle_id"), nullable=False)
    round = Column(Integer, nullable=False)
    agent = Column(String(50), nullable=False)
    status = Column(String(50), nullable=True)
    message = Column(Text, nullable=False)
    target_agent = Column(String(50), nullable=True)
    revised_confidence = Column(Float, nullable=True)

    decision = relationship("DecisionModel", back_populates="debate_messages")


class SafetyEventModel(Base):
    __tablename__ = "safety_events"

    event_id = Column(Integer, primary_key=True, autoincrement=True)
    cycle_id = Column(String(50), ForeignKey("decisions.cycle_id"), nullable=False)
    rule_id = Column(String(50), nullable=False)
    outcome = Column(String(50), nullable=False)
    detail = Column(Text, nullable=False)
    timestamp = Column(String(50), nullable=False)

    decision = relationship("DecisionModel", back_populates="safety_events")


class RecoveryPlanModel(Base):
    __tablename__ = "recovery_plans"

    plan_id = Column(Integer, primary_key=True, autoincrement=True)
    cycle_id = Column(String(50), ForeignKey("decisions.cycle_id"), nullable=False)
    horizon_hours = Column(Integer, nullable=False)
    plan_json = Column(JSON, nullable=False)
    priorities = Column(JSON, nullable=True)
    monitoring = Column(JSON, nullable=True)
    next_reassessment = Column(String(50), nullable=True)
    score_change = Column(String(100), nullable=True)

    decision = relationship("DecisionModel", back_populates="recovery_plan")


class SimulationRunModel(Base):
    __tablename__ = "simulation_runs"

    sim_id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String(50), ForeignKey("patients.patient_id"), nullable=False)
    base_state_id = Column(Integer, ForeignKey("twin_states.state_id"), nullable=True)
    changes = Column(JSON, nullable=False)
    sim_state_json = Column(JSON, nullable=False)
    simulated_plan = Column(JSON, nullable=True)
    verdict = Column(String(50), nullable=False)
    timestamp = Column(String(50), nullable=False)

    patient = relationship("PatientModel", back_populates="simulation_runs")
    base_twin_state = relationship("TwinStateModel", back_populates="simulation_runs")


class EvaluationRunModel(Base):
    __tablename__ = "evaluation_runs"

    run_id = Column(String(50), primary_key=True)
    created_at = Column(String(50), nullable=False)
    seed = Column(Integer, nullable=False)
    cohort_size = Column(Integer, nullable=False)
    report_json = Column(JSON, nullable=False)



# ---------- Database Initialization & Seeding ----------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Creates all tables and seeds canonical patient P001 (Meera Sharma) if missing."""
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        patient = db.query(PatientModel).filter_by(patient_id="P001").first()
        scenarios_dir = Path(__file__).resolve().parent.parent.parent / "data" / "scenarios"
        meera_file = scenarios_dir / "meera_day4.json"

        if not patient and meera_file.exists():
            with open(meera_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            twin = TwinState(**data)
            patient = PatientModel(
                patient_id=twin.patient_id,
                name=twin.profile.name,
                age=twin.profile.age,
                surgery=twin.profile.surgery,
                surgery_date="2026-09-17",
                care_plan={"target": "Post-Op TKR Recovery"},
            )
            db.add(patient)

            # Seed baseline twin state
            state_row = TwinStateModel(
                patient_id=twin.patient_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                twin_json=twin.model_dump(),
                recovery_score=twin.scores.recovery_score,
                trajectory_overall=twin.trajectory.overall,
            )
            db.add(state_row)

            # Seed initial observation row
            obs_row = ObservationModel(
                patient_id=twin.patient_id,
                timestamp="2026-09-21T08:00:00Z",
                pain=twin.observations.pain,
                sleep_hours=twin.observations.sleep_hours,
                steps=twin.observations.steps,
                swelling=twin.observations.swelling,
                temperature=twin.observations.temperature,
                heart_rate=twin.observations.heart_rate,
                crp=twin.observations.crp,
                night_awakenings=4,
                flags=[],
            )
            db.add(obs_row)
            db.commit()
    finally:
        db.close()
