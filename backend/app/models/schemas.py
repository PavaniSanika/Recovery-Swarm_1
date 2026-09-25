"""Frozen Pydantic contracts for RECOVERY-SWARM.

Do not rename, remove, or add fields without explicit approval.
Contracts frozen in docs/CONTRACTS.md.
"""

from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------- Digital Twin (OFFICIAL, frozen) ----------
class Profile(Strict):
    name: str
    age: int
    surgery: str
    post_op_day: int = Field(ge=0)


class Observations(Strict):
    pain: float = Field(ge=0, le=10)
    sleep_hours: float = Field(ge=0, le=14)
    steps: int = Field(ge=0)
    swelling: float = Field(ge=0, le=10)
    temperature: float
    heart_rate: int
    crp: float = Field(ge=0, le=10)  # prototype-scaled CRP index
    night_awakenings: Optional[int] = None
    flags: list[str] = []


class Scores(Strict):
    inflammation_score: float = Field(ge=0, le=10)
    mobility_capacity: float = Field(ge=0, le=10)
    sleep_quality: float = Field(ge=0, le=10)  # higher is better
    medication_effectiveness: float = Field(ge=0, le=10)
    complication_risk: float = Field(ge=0, le=10)
    recovery_score: int = Field(ge=0, le=100)


class Trajectory(Strict):
    overall: Literal[
        "on_track", "slightly_below_expected", "below_expected", "deteriorating"
    ]
    inflammation: Literal["improving", "stable_high", "worsening"]
    mobility: Literal["on_track", "below_expected", "declining"]
    sleep: Literal["good", "fair", "poor"]


class Medications(Strict):
    current: list[str]
    response_score: float  # always equals scores.medication_effectiveness


class HistoryEntry(Strict):
    timestamp: str
    observations: Observations
    scores: Scores
    overall: str


class TwinState(Strict):
    patient_id: str
    profile: Profile
    observations: Observations
    scores: Scores
    trajectory: Trajectory
    medications: Medications
    history: list[HistoryEntry] = []


# ---------- Agent proposal (OFFICIAL, frozen) ----------
ActionType = Literal[
    "mobility", "sleep", "swelling", "pain_review", "monitoring", "escalate"
]
Direction = Literal["increase", "maintain", "decrease"]


class Proposal(Strict):
    agent: str  # one of the specialist agent ids
    action_type: ActionType
    direction: Direction
    target_value: Optional[float] = None  # e.g. steps target; None when not applicable
    confidence: float = Field(ge=0, le=1)
    evidence: list[str] = Field(min_length=1)
    rationale: str
    risks: list[str]


class Stance(Strict):
    agent: str  # who is speaking
    target_agent: str  # whose proposal
    stance: Literal["support", "oppose", "revise"]
    revised_confidence: float = Field(ge=0, le=1)
    message: str  # one short sentence shown in the live debate


# ---------- Priority router ----------
class PriorityResult(Strict):
    priority_scores: dict[str, float]  # specialist id -> 0..1
    roles: dict[str, Literal["lead", "supporting", "waiting"]]


# ---------- Safety ----------
class RuleHit(Strict):
    rule_id: str  # "R1".."R8"
    outcome: Literal["allow", "modify", "reject", "escalate"]
    detail: str


class PlanItem(Strict):
    action: str
    reason: str
    target: Optional[str] = None


class Plan(Strict):
    horizon_hours: int = Field(ge=6, le=12)
    high_priority: list[PlanItem]
    medium_priority: list[PlanItem]
    monitoring: list[str]
    safety_status: str  # e.g. "No predefined safety rule triggered."
    next_reassessment: str
    expected_score_change: Optional[str] = None
    explanation: str  # "why" text, built only from decided actions + evidence
    steps_target: Optional[int] = None  # numeric mobility target chosen by the swarm


class SafetyResult(Strict):
    result: Literal["allow", "modify", "reject", "escalate"]  # strictest outcome wins
    rules_triggered: list[RuleHit] = []
    modified_plan: Optional[Plan] = None


# ---------- Cycle ----------
class DebateMessage(Strict):
    round: int
    agent: str
    status: Literal[
        "Analyzing",
        "Waiting",
        "Supporting",
        "Challenging",
        "Revising",
        "Vetoing",
        "Approved",
    ]
    message: str
    target_agent: Optional[str] = None


class CycleResponse(Strict):
    cycle_id: str
    priority: PriorityResult
    proposals: list[Proposal]
    stances: list[Stance]
    coalitions: list[list[str]]
    debate: list[DebateMessage]
    safety: SafetyResult
    plan: Optional[Plan]  # None only when result == "escalate" and no plan is safe
    escalated: bool
    twin: TwinState


# ---------- Input ----------
class ObservationIn(Strict):
    timestamp: str
    pain: float
    sleep_hours: float
    steps: int
    swelling: float
    temperature: float
    heart_rate: int
    crp: float
    night_awakenings: Optional[int] = None  # optional, feeds sleep_quality
    flags: list[str] = []  # see CONTRACTS 10.1
    scenario_overrides: Optional[dict[str, float]] = None  # see CONTRACTS 10.2


# ---------- What-if ----------
class WhatIfRequest(Strict):
    changes: dict[
        str, float
    ]  # allowed keys: steps_pct, steps, pain, sleep_hours, swelling


class WhatIfResponse(Strict):
    simulated_twin: TwinState
    effects: dict[str, str]  # e.g. {"pain": "+0.6", "swelling": "+0.8"}
    simulated_plan: Optional[Plan]
    safety: SafetyResult
    comparison: dict  # {"current": {...}, "simulated": {...}} of key values
    disclaimer: str  # exact text in CONTRACTS 9.4


# ---------- Extension: Simulator Status ----------
class SimulatorStatus(Strict):
    scenario_name: Optional[str] = None
    step_index: int = Field(ge=0)
    total_steps: int = Field(ge=0)
    minute_offset: int = Field(ge=0)
    max_minute_offset: int = Field(default=0, ge=0)


# ---------- Extension: Twin Reference Curves ----------
class TwinReference(Strict):
    surgery: str
    post_op_day: int = Field(ge=0)
    expected_pain: float = Field(ge=0, le=10)
    expected_inflammation: float = Field(ge=0, le=10)
    expected_steps: int = Field(ge=0)
    curves: dict[str, dict[str, float]]


