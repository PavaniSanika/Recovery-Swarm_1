# RECOVERY-SWARM: CONTRACTS (frozen)

These contracts are frozen. Do not rename fields, change types or add fields without explicit human approval.
If something here conflicts with `SPEC.md`, this file wins for data shapes, formulas and thresholds; `SPEC.md` wins for behaviour and UI.

Everything is **synthetic data only**. Recovery Score is an illustrative prototype metric and is not a clinically validated prediction.

Sections: 1 Conventions, 2 Pydantic models, 3 Config (`thresholds.yaml`), 4 Formulas, 5 Router / debate / safety contracts, 6 Database, 7 API, 8 Scenario files, 9 Golden test vectors, 10 Clarifications beyond the SPEC, 11 TypeScript types (frontend), 12 Extensions (additive: screening flags, synthetic cohort evaluation, 3D body twin).

---

## 1. Conventions

- Language: Python 3.11, Pydantic v2. All models use `model_config = ConfigDict(extra="forbid")`.
- Scores are floats 0-10 unless stated. `recovery_score` is an int 0-100.
- Timestamps are ISO 8601 strings.
- Agent ids (used everywhere): `twin_builder`, `inflammation`, `mobility`, `medication`, `sleep`, `safety`, `coordinator`.
- Specialist agent ids (the four LLM agents): `inflammation`, `mobility`, `medication`, `sleep`.
- Action types: `mobility`, `sleep`, `swelling`, `pain_review`, `monitoring`, `escalate`.
- Directions: `increase`, `maintain`, `decrease`.
- Safety outcomes: `allow`, `modify`, `reject`, `escalate`.
- Stances: `support`, `oppose`, `revise`.
- Roles: `lead`, `supporting`, `waiting`.
- UI agent statuses: Analyzing, Waiting, Supporting, Challenging, Revising, Vetoing, Approved.

---

## 2. Pydantic models

File: `backend/app/models/schemas.py`

```python
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
    crp: float = Field(ge=0, le=10)      # prototype-scaled CRP index

class Scores(Strict):
    inflammation_score: float = Field(ge=0, le=10)
    mobility_capacity: float = Field(ge=0, le=10)
    sleep_quality: float = Field(ge=0, le=10)          # higher is better
    medication_effectiveness: float = Field(ge=0, le=10)
    complication_risk: float = Field(ge=0, le=10)
    recovery_score: int = Field(ge=0, le=100)

class Trajectory(Strict):
    overall: Literal["on_track", "slightly_below_expected",
                     "below_expected", "deteriorating"]
    inflammation: Literal["improving", "stable_high", "worsening"]
    mobility: Literal["on_track", "below_expected", "declining"]
    sleep: Literal["good", "fair", "poor"]

class Medications(Strict):
    current: list[str]
    response_score: float                # always equals scores.medication_effectiveness

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
ActionType = Literal["mobility", "sleep", "swelling",
                     "pain_review", "monitoring", "escalate"]
Direction = Literal["increase", "maintain", "decrease"]

class Proposal(Strict):
    agent: str                           # one of the specialist agent ids
    action_type: ActionType
    direction: Direction
    target_value: Optional[float] = None # e.g. steps target; None when not applicable
    confidence: float = Field(ge=0, le=1)
    evidence: list[str] = Field(min_length=1)
    rationale: str
    risks: list[str]

class Stance(Strict):
    agent: str                           # who is speaking
    target_agent: str                    # whose proposal
    stance: Literal["support", "oppose", "revise"]
    revised_confidence: float = Field(ge=0, le=1)
    message: str                         # one short sentence shown in the live debate

# ---------- Priority router ----------
class PriorityResult(Strict):
    priority_scores: dict[str, float]    # specialist id -> 0..1
    roles: dict[str, Literal["lead", "supporting", "waiting"]]

# ---------- Safety ----------
class RuleHit(Strict):
    rule_id: str                         # "R1".."R8"
    outcome: Literal["allow", "modify", "reject", "escalate"]
    detail: str

class SafetyResult(Strict):
    result: Literal["allow", "modify", "reject", "escalate"]   # strictest outcome wins
    rules_triggered: list[RuleHit] = []
    modified_plan: Optional["Plan"] = None

# ---------- Plan ----------
class PlanItem(Strict):
    action: str
    reason: str
    target: Optional[str] = None

class Plan(Strict):
    horizon_hours: int = Field(ge=6, le=12)
    high_priority: list[PlanItem]
    medium_priority: list[PlanItem]
    monitoring: list[str]
    safety_status: str                   # e.g. "No predefined safety rule triggered."
    next_reassessment: str
    expected_score_change: Optional[str] = None
    explanation: str                     # "why" text, built only from decided actions + evidence
    steps_target: Optional[int] = None   # numeric mobility target chosen by the swarm

SafetyResult.model_rebuild()

# ---------- Cycle ----------
class DebateMessage(Strict):
    round: int
    agent: str
    status: Literal["Analyzing", "Waiting", "Supporting", "Challenging",
                    "Revising", "Vetoing", "Approved"]
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
    plan: Optional[Plan]                 # None only when result == "escalate" and no plan is safe
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
    night_awakenings: Optional[int] = None                # optional, feeds sleep_quality
    flags: list[str] = []                                 # see 10.1
    scenario_overrides: Optional[dict[str, float]] = None # see 10.2

# ---------- What-if ----------
class WhatIfRequest(Strict):
    changes: dict[str, float]    # allowed keys: steps_pct, steps, pain, sleep_hours, swelling

class WhatIfResponse(Strict):
    simulated_twin: TwinState
    effects: dict[str, str]      # e.g. {"pain": "+0.6", "swelling": "+0.8"}
    simulated_plan: Optional[Plan]
    safety: SafetyResult
    comparison: dict             # {"current": {...}, "simulated": {...}} of key values
    disclaimer: str              # exact text in 9.4 (constant DISCLAIMER_WHATIF)
```

Canonical twin JSON (Meera, Post-Op Day 4). This exact object must validate against `TwinState`:

```json
{
  "patient_id": "P001",
  "profile": {"name": "Meera Sharma", "age": 62,
              "surgery": "Total Knee Replacement", "post_op_day": 4},
  "observations": {"pain": 6.0, "sleep_hours": 4.5, "steps": 1800,
                   "swelling": 6.0, "temperature": 37.1,
                   "heart_rate": 84, "crp": 6.2},
  "scores": {"inflammation_score": 6.2, "mobility_capacity": 5.0,
             "sleep_quality": 3.5, "medication_effectiveness": 5.5,
             "complication_risk": 3.2, "recovery_score": 68},
  "trajectory": {"overall": "slightly_below_expected",
                 "inflammation": "stable_high",
                 "mobility": "below_expected", "sleep": "poor"},
  "medications": {"current": ["Paracetamol", "Low-dose opioid at night"],
                  "response_score": 5.5},
  "history": []
}
```

---

## 3. Config: `backend/thresholds.yaml`

All thresholds, weights and coefficients live here. No magic numbers in code. All values are illustrative and not clinically validated.

```yaml
scoring:
  # inflammation_score = w_crp*crp + w_swelling*swelling + temp_bonus
  inflammation: {w_crp: 0.7, w_swelling: 0.3, temp_base_c: 37.0, temp_bonus_per_0_1c: 0.1}
  sleep: {target_hours: 7.5, max_disturbance_penalty: 3.0, penalty_per_awakening: 0.625}
  recovery_score_weights: {pain: 0.17, inflammation: 0.17, mobility: 0.14, sleep: 0.10, complication: 0.10}
  complication_points:
    temp_above_37_8: 1.0
    crp_rising: 1.5
    asymmetric_swelling: 1.0
    pain_rising_3_readings: 1.0
    age_above_60: 0.5

reference:            # expected recovery curve, Total Knee Replacement (approximate)
  TKR:
    pain:         {1: 7.0, 2: 6.0, 3: 5.0, 4: 4.0, 5: 3.5, 6: 3.0, 7: 2.5}
    inflammation: {1: 7.5, 2: 7.0, 3: 6.0, 4: 5.2, 5: 4.6, 6: 4.0, 7: 3.5}
    step_target:  {1: 600, 2: 1200, 3: 1800, 4: 2500, 5: 2800, 6: 3200, 7: 3500}

trajectory:
  slightly_below: {pain_dev: 1.0, inflammation_dev: 0.5, steps_frac_below: 0.90}
  below:          {pain_dev: 3.0, inflammation_dev: 2.0, steps_frac_below: 0.60, min_conditions: 2}
  slope_threshold: 0.15          # inflammation slope per reading
  sleep_bands: {good_above: 6.0, poor_below: 4.0}

deviation_check:                 # workflow component, early warning
  pain_above_expected: {points: 2.0, consecutive_readings: 2}
  worsening_consecutive_readings: 3
  inflammation_not_falling_hours: 24

router:
  base: 0.3
  scale: 0.9                     # priority = clamp(base + scale * signal, 0, 1)
  lead_count: 3
  waiting_below: 0.30
  role_multiplier: {lead: 1.5, supporting: 1.0}

safety_rules:
  R1: {pain_at_least: 8.0, pain_rise_24h: 2.0, outcome: escalate, block_activity_increase: true}
  R2: {swelling_at_least: 6.0, requires_increasing: true, outcome: modify, cap: current_steps}
  R3: {temperature_at_least: 38.0, red_flags: [chest_pain, breathlessness, calf_pain], outcome: escalate}
  R4: {max_daily_step_increase_pct: 10, outcome: modify}
  R5: {outcome: reject, forbidden_terms: [dose, dosage, increase medication, decrease medication,
       start medication, stop medication, new medication, prescribe, mg]}
  R6: {sleep_hours_below: 4.0, pain_at_least: 7.0, outcome: modify, cap: current_steps}
  R7: {min_confidence: 0.5, outcome: escalate}
  R8: {wound_flags: [wound_redness, wound_discharge, wound_opening], outcome: escalate}
  max_retry_loops: 2

whatif_effect_per_10pct_steps:   # per +10% steps; "moderate_or_higher" means swelling >= 5
  below_moderate:      {pain: 0.1, swelling: 0.1, sleep_hours: 0.0}
  moderate_or_higher:  {pain: 0.3, swelling: 0.4, sleep_hours: -0.1}

llm:
  temperature: 0.1
  max_tokens: 600
  timeout_s: 20
  retries: 2
  fallback_mode: false           # true = rule-based agents only
```

---

## 4. Formulas (reference implementation, `backend/app/twin/engine.py`)

`clamp(x, lo, hi)` bounds a value. Round scores to 1 decimal, `recovery_score` to an int.

```python
def inflammation_score(o, cfg):
    c = cfg["inflammation"]
    temp_bonus = max(0.0, (o.temperature - c["temp_base_c"]) / 0.1) * c["temp_bonus_per_0_1c"]
    return clamp(c["w_crp"] * o.crp + c["w_swelling"] * o.swelling + temp_bonus, 0, 10)

def mobility_capacity(o, step_target):
    return clamp(10 * (o.steps / step_target) * (1 - o.pain / 20), 0, 10)

def sleep_quality(o, night_awakenings, cfg):
    s = cfg["sleep"]
    penalty = min(s["max_disturbance_penalty"],
                  (night_awakenings or 0) * s["penalty_per_awakening"])
    return clamp(10 * (o.sleep_hours / s["target_hours"]) - penalty, 0, 10)

def recovery_score(o, scores, step_target, cfg):
    w = cfg["recovery_score_weights"]
    pen = (w["pain"] * o.pain / 10
         + w["inflammation"] * scores.inflammation_score / 10
         + w["mobility"] * clamp(1 - o.steps / step_target, 0, 1)
         + w["sleep"] * clamp(1 - o.sleep_hours / 7.5, 0, 1)
         + w["complication"] * scores.complication_risk / 10)
    return round(100 * (1 - pen))
```

- `medication_effectiveness` = `scenario_overrides["medication_effectiveness"]` if present, else computed from dose events if available, else default `5.0`. Also copy it to `medications.response_score`.
- `complication_risk` = `scenario_overrides["complication_risk"]` if present, else the rule points in `scoring.complication_points` (capped at 10).
- **Trajectory rules** (compare to `reference` for the post-op day; `pain_dev = pain - expected_pain`, `inflammation_dev = inflammation_score - expected_inflammation`, `steps_frac = steps / step_target`):
  - `overall = "deteriorating"` if pain, inflammation_score or steps-derived mobility worsened for 3 consecutive history readings.
  - Else `"below_expected"` if at least 2 of: `pain_dev >= 3.0`, `inflammation_dev >= 2.0`, `steps_frac < 0.60`.
  - Else `"slightly_below_expected"` if any of: `pain_dev >= 1.0`, `inflammation_dev >= 0.5`, `steps_frac < 0.90`.
  - Else `"on_track"`.
  - `inflammation`: `improving` if slope <= -0.15, `worsening` if slope >= +0.15, else `stable_high` when score >= 5.5 (otherwise `improving`). Slope = average change per reading over the last 3 to 5 history entries (0 with fewer than 2).
  - `mobility`: `declining` if steps fell for 3 consecutive readings, else `below_expected` if `steps_frac < 0.90`, else `on_track`.
  - `sleep`: `good` if sleep_quality > 6, `poor` if < 4, else `fair`.

---

## 5. Router, debate, coordinator and safety contracts

### 5.1 Priority Router (workflow component, not an agent)

```python
signals = {
  "mobility":     0.50*pain/10 + 0.25*mobility_gap + 0.25*swelling/10,
  "sleep":        0.60*(1 - sleep_quality/10) + 0.40*sleep_deficit,
  "inflammation": 0.60*inflammation_score/10 + 0.40*swelling/10,
  "medication":   0.50*(1 - medication_effectiveness/10) + 0.20*pain/10,
}
priority = clamp(0.3 + 0.9 * signal, 0, 1)      # router.base + router.scale * signal
```

`mobility_gap = clamp(1 - steps/step_target, 0, 1)`, `sleep_deficit = clamp(1 - sleep_hours/7.5, 0, 1)`.
Roles: top 3 by priority = `lead`; the rest `supporting`; any score below `waiting_below` = `waiting`. The Safety Guardian is always active and is not routed.
For Meera baseline the expected values are approximately: inflammation 0.85, sleep 0.80, mobility 0.77, medication 0.61, so leads = {inflammation, sleep, mobility}. (SPEC section 8 shows illustrative numbers; tests assert the lead set and each value within +/- 0.05 of these.)
Priority scores are prototype coordination signals and are not clinical risk probabilities.

### 5.2 Debate and coordinator

1. Round 1: each non-waiting specialist returns one `Proposal`.
2. Round 2: each specialist returns one `Stance` for each other proposal (`support` / `oppose` / `revise`, with `revised_confidence`). A `revise` stance may replace that agent's own proposal (update `direction`, `target_value`, `confidence`) for scoring.
3. Coalitions: agents whose proposals share `action_type` family and direction (or `maintain`/`decrease` vs `increase` on activity) are grouped: `coalitions: [["sleep","inflammation","medication"]]`.
4. Weight of a vote = `role_multiplier[role] x priority_score x confidence x stance_value` where `support=+1`, `oppose=-1`, `revise=0`.
5. Per topic (`action_type`), the option with the highest summed score wins. Ties (within 10%) go to the safer option using order `decrease < maintain < increase`.
6. Conservative-first: on activity (`mobility`) conflicts choose the lowest `target_value` among options whose score is at least 80% of the best.
7. Draft plan = winning option per topic. It then goes to the Safety Guardian.

### 5.3 Safety Guardian (deterministic, no LLM)

```python
def evaluate(twin, proposals, draft_plan, history, flags) -> SafetyResult
```

- Rules R1 to R8 in `thresholds.yaml` (`safety_rules`). Rules R4 and R5 also run on each proposal as soon as it is produced (`evaluate_proposal`) so unsafe options can be vetoed during the debate (UI status "Vetoing").
- Conditions:
  - R1: `pain >= 8.0` or pain rose `>= 2.0` within the last 24 hours of history. Block any activity increase (force `maintain` or `decrease`) and result = `escalate`.
  - R2: `swelling >= 6.0` and swelling slope > 0. Cap steps at the current steps value (`modify`).
  - R3: `temperature >= 38.0` or any of `flags` in `red_flags`. `escalate`.
  - R4: proposed `target_value > steps * 1.10`. `modify` to `floor(steps * 1.10)`.
  - R5: any proposal or plan text mentioning a medication start, stop, dose or new drug (see `forbidden_terms`), or any proposal by the `medication` agent whose `action_type` is not `pain_review`, `monitoring` or `escalate`. `reject`, and replace with a "clinical review" item.
  - R6: `sleep_hours < 4.0` and `pain >= 7.0`. No aggressive activity: cap steps at current (`modify`).
  - R7: a key observation is missing, or any winning proposal has `confidence < 0.5`. `escalate` (ask for missing data).
  - R8: any of `wound_flags` present. `escalate`.
- Overall `result` = strictest outcome among hits with order `escalate > reject > modify > allow`.
- If `reject`: send back to the coordinator with the violated rule as a constraint. Maximum `max_retry_loops` = 2, then `escalate`.
- Every evaluation writes one `safety_events` row per rule hit (and one `allow` row when nothing fires).

### 5.4 Medication Response Agent limits (enforced in code)

MAY: analyze medication-response patterns; correlate symptoms with medication timing in the synthetic scenario; identify reduced effectiveness; flag patterns for professional review; recommend "clinical review".
MUST NOT: recommend a dosage; increase, decrease, start or stop a medication; recommend a new medication; diagnose; make a critical clinical decision.
Enforcement: schema limits `action_type` to `pain_review`, `monitoring`, `escalate`; rule R5 scans text; a test proves a dosage request is blocked.

### 5.5 Plan Generator (workflow component)

Input: the approved decision (winning options + safety result + evidence). Output: `Plan` (6 to 12 hour horizon, default 12). It must not add actions that are not in the decision. Wording may use the LLM; a template-based fallback must exist. Include `safety_status`, `next_reassessment` and (optional) `expected_score_change`.

---

## 6. Database (SQLite default, PostgreSQL-ready, SQLAlchemy 2)

The code must be **database-neutral**: SQLAlchemy `JSON` columns, and never SQLite-specific or PostgreSQL-specific SQL or features. **SQLite is the default** for development, tests and the demo (`DATABASE_URL=sqlite:///./recovery.db`; tests use a temporary SQLite file or in-memory database). **PostgreSQL is a supported option**, switched by one line: `DATABASE_URL=postgresql+psycopg://user:pass@host/recovery`. Create tables with SQLAlchemy `create_all` at startup (no migrations tool). The test suite runs on SQLite; run it once on PostgreSQL before the demo if time allows.
Store JSON as `JSON` columns. Primary keys are string ids (`P001`, `C001`, ...) or integers where noted.

| Table | Columns |
|---|---|
| `patients` | patient_id PK, name, age, surgery, surgery_date, care_plan JSON |
| `observations` | obs_id PK int, patient_id FK, timestamp, pain, sleep_hours, steps, swelling, temperature, heart_rate, crp, night_awakenings, flags JSON |
| `twin_states` | state_id PK int, patient_id FK, timestamp, twin_json JSON, recovery_score, trajectory_overall |
| `decisions` | cycle_id PK, patient_id FK, state_id FK, priority_scores JSON, lead_agents JSON, coalitions JSON, draft_plan JSON, safety_result, escalated bool, created_at |
| `agent_proposals` | proposal_id PK int, cycle_id FK, agent, action_type, direction, target_value, confidence, evidence JSON, rationale, risks JSON, round |
| `debate_messages` | msg_id PK int, cycle_id FK, round, agent, stance, target_agent, message, revised_confidence |
| `safety_events` | event_id PK int, cycle_id FK, rule_id, outcome, detail, timestamp |
| `recovery_plans` | plan_id PK int, cycle_id FK, horizon_hours, plan_json JSON, priorities JSON, monitoring JSON, next_reassessment, score_change |
| `simulation_runs` | sim_id PK int, patient_id FK, base_state_id FK, changes JSON, sim_state_json JSON, simulated_plan JSON, verdict, timestamp |

Relations: patients 1-N observations, twin_states, decisions, simulation_runs. decisions 1-N agent_proposals, debate_messages, safety_events; decisions 1-1 recovery_plans.
What-if runs (`is_simulation = true`) write only to `simulation_runs` and never to `twin_states`, `decisions` or `recovery_plans`.

---

## 7. API

Base path `/api`. JSON in, JSON out. Errors: `{"error": {"code": "string", "message": "string"}}` with proper HTTP status.

| Method | Endpoint | Request | Response |
|---|---|---|---|
| POST | `/patients/{id}/observations` | `ObservationIn` | `TwinState` (updated) |
| GET | `/patients/{id}/twin` | - | `TwinState` |
| GET | `/patients/{id}/twin/history` | - | `list[HistoryEntry]` |
| POST | `/patients/{id}/cycle` | `{}` | `CycleResponse` |
| GET | `/patients/{id}/decisions` | - | list of `{cycle_id, created_at, safety_result, escalated, plan}` |
| GET | `/patients/{id}/plan/latest` | - | `Plan` |
| GET | `/decisions/{cycle_id}/debate` | - | `{proposals, stances, debate, safety_events}` |
| GET | `/patients/{id}/audit` | - | list of `{timestamp, cycle_id, actor, event, rule_id, outcome}` |
| POST | `/patients/{id}/whatif` | `WhatIfRequest` | `WhatIfResponse` |
| POST | `/simulator/inject` | `{"patient_id": "P001", "scenario": "poor_sleep"}` | `TwinState` |
| POST | `/simulator/advance` | `{"patient_id": "P001", "minutes": 60}` | `TwinState` |
| POST | `/simulator/reset` | `{"patient_id": "P001"}` | `TwinState` (deletes P001's twin_states, decisions and related rows, plans and simulation_runs, then restores the Meera baseline) |
| POST | `/decisions/{id}/clinician-review` | `{"note": "string", "action": "acknowledge"}` | `{ "ok": true }` |
| WS | `/ws/patients/{id}` | - | stream of `{"type": ..., "payload": ...}` |

WebSocket message types: `twin_update` (TwinState), `debate_message` (DebateMessage), `agent_status` (`{agent, status, confidence, recommendation, role}`), `plan` (Plan), `safety` (SafetyResult), `escalation` (`{cycle_id, summary}`).
Scenario names: `stable_recovery`, `poor_sleep`, `pain_spike`, `increased_inflammation`, `reduced_mobility`, `recovery_deviation`.

---

## 8. Scenario files (`data/scenarios/*.json`)

Deterministic. Fixed `seed`. Same file always yields the same observations.

```json
{
  "name": "poor_sleep",
  "description": "Sleep drops with more night awakenings",
  "seed": 42,
  "base": "meera_day4",
  "steps": [
    {"minute_offset": 0,  "observation": {"pain": 6.0, "sleep_hours": 4.0,
        "steps": 1800, "swelling": 6.0, "temperature": 37.1,
        "heart_rate": 86, "crp": 6.2, "night_awakenings": 5}},
    {"minute_offset": 60, "observation": {"pain": 6.2, "sleep_hours": 3.5,
        "steps": 1780, "swelling": 6.0, "temperature": 37.1,
        "heart_rate": 88, "crp": 6.3, "night_awakenings": 6}}
  ],
  "expect": {"lead_agent": "sleep", "escalated": false}
}
```

Required scenarios and their intent:

| Scenario | Key changes from Meera baseline | Expected result |
|---|---|---|
| `stable_recovery` | pain 6 -> 5 -> 4.5, sleep 6+, steps +5% per hour | overall `on_track` or `slightly_below_expected`, no escalation, gradual mobility increase within R4 |
| `poor_sleep` | sleep 4.5 -> 3.5, awakenings up | `sleep` is the top-priority agent |
| `pain_spike` | pain 6 -> 8 within 24h | R1 fires, activity increase blocked, escalate |
| `increased_inflammation` | crp 6.2 -> 7.8, swelling 6 -> 7.5, temp 37.4 | `inflammation` leads, R2 caps activity |
| `reduced_mobility` | steps 1800 -> 1100 | `mobility` leads, trajectory mobility `below_expected` or `declining` |
| `recovery_deviation` | pain up, inflammation up, steps down together | Deviation Check flags, R1 fires, result `escalate`, appears in Clinician View |

Baseline `meera_day4` = the canonical twin observations in section 2. Simulated wearable example: 10:00 pain 6.0 steps 1800; 10:05 pain 5.9 steps 1850; 10:10 pain 5.7 steps 1910.

---

## 9. Golden test vectors (must pass)

**9.1 Meera baseline scores** (from `observations` + `night_awakenings = 4` (penalty 4 x 0.625 = 2.5), step target 2500, `scenario_overrides` medication_effectiveness 5.5 and complication_risk 3.2):
- (use a rounding tolerance of 0.05 on floats) inflammation_score = 6.2, mobility_capacity = 5.0, sleep_quality = 3.5, recovery_score = 68
- trajectory: overall `slightly_below_expected`, inflammation `stable_high`, mobility `below_expected`, sleep `poor`

**9.2 Recovery Score arithmetic:** penalties 0.60, 0.62, 0.28, 0.40, 0.32 with weights .17, .17, .14, .10, .10 give total 0.319, so score = 68.

**9.3 Safety:**
- Proposal `mobility` target 2200 with steps 1800 -> R4 `modify` to 1980.
- Pain 8.0 -> R1 `escalate`. Temperature 38.2 -> R3 `escalate`. Flag `wound_discharge` -> R8 `escalate`.
- Medication agent proposal containing "increase dose" -> R5 `reject`.
- Sleep 3.5 h and pain 7.0 -> R6 `modify` (steps capped at current).
- Meera baseline final plan (steps target 1900) -> `allow`, `rules_triggered == []`.

**9.4 What-if (steps +20%):** steps 1800 -> 2160. Effects at swelling 6.0 (moderate or higher): pain +0.6, swelling +0.8, sleep_hours -0.2. Recompute all derived scores with the Twin Engine formulas (the mobility row of the effect table is informational; `mobility_capacity` is always recomputed). Safety: R4 flags a 20% jump, simulated plan target = 1980 (`modify`). The live twin and `twin_states` are unchanged. The response `disclaimer` is exactly:

`Illustrative simulation only. Results are based on prototype assumptions and synthetic data and are not clinical predictions.`

**9.5 Determinism:** the same scenario + seed + `fallback_mode: true` produces byte-identical `CycleResponse` JSON (except `cycle_id` and timestamps).

**9.6 Terminology:** the strings "Recovery Probability" and "probability" (as a score name) must not appear in any UI text or API field. Use "Recovery Score" and `recovery_score`. Show "Recovery Score: 68 / 100".

---

## 10. Clarifications beyond the SPEC (small additions needed to implement)

10.1 `ObservationIn.flags` (list of strings) carries red-flag and wound signs so R3 and R8 can work: `chest_pain`, `breathlessness`, `calf_pain`, `wound_redness`, `wound_discharge`, `wound_opening`. Stored in `observations.flags`. Not part of the frozen twin.

10.2 `ObservationIn.scenario_overrides` lets the simulator supply `medication_effectiveness` and `complication_risk` (as the SPEC says these come from the scenario file). Not part of the frozen twin.

10.3 `Plan.steps_target` and `Plan.horizon_hours` make the mobility decision and the 6 to 12 hour horizon machine-checkable.

10.4 Medication dose events are not modelled in detail; `medication_effectiveness` comes from the scenario or defaults to 5.0.

10.5 If any of these clarifications seems to conflict with the SPEC, stop and ask a human.

---

## 11. TypeScript types (frontend): `frontend/src/types.ts` (frozen)

These mirror the Pydantic models in section 2 and the API in section 7. Python `Optional[X]` becomes `X | null` (the API returns `null`). Field names are identical (snake_case). Do not rename fields, do not use `any`.

```ts
// ---------- ids and enums ----------
export type AgentId = "twin_builder" | "inflammation" | "mobility" |
  "medication" | "sleep" | "safety" | "coordinator";
export type SpecialistId = "inflammation" | "mobility" | "medication" | "sleep";
export type ActionType = "mobility" | "sleep" | "swelling" |
  "pain_review" | "monitoring" | "escalate";
export type Direction = "increase" | "maintain" | "decrease";
export type SafetyOutcome = "allow" | "modify" | "reject" | "escalate";
export type StanceKind = "support" | "oppose" | "revise";
export type Role = "lead" | "supporting" | "waiting";
export type AgentStatus = "Analyzing" | "Waiting" | "Supporting" |
  "Challenging" | "Revising" | "Vetoing" | "Approved";
export type ScenarioName = "stable_recovery" | "poor_sleep" | "pain_spike" |
  "increased_inflammation" | "reduced_mobility" | "recovery_deviation";

// ---------- Digital Twin (official) ----------
export interface Profile { name: string; age: number; surgery: string; post_op_day: number; }
export interface Observations {
  pain: number; sleep_hours: number; steps: number; swelling: number;
  temperature: number; heart_rate: number; crp: number;
}
export interface Scores {
  inflammation_score: number; mobility_capacity: number; sleep_quality: number;
  medication_effectiveness: number; complication_risk: number; recovery_score: number;
}
export interface Trajectory {
  overall: "on_track" | "slightly_below_expected" | "below_expected" | "deteriorating";
  inflammation: "improving" | "stable_high" | "worsening";
  mobility: "on_track" | "below_expected" | "declining";
  sleep: "good" | "fair" | "poor";
}
export interface Medications { current: string[]; response_score: number; }
export interface HistoryEntry {
  timestamp: string; observations: Observations; scores: Scores; overall: string;
}
export interface TwinState {
  patient_id: string; profile: Profile; observations: Observations; scores: Scores;
  trajectory: Trajectory; medications: Medications; history: HistoryEntry[];
}

// ---------- Agents ----------
export interface Proposal {
  agent: string; action_type: ActionType; direction: Direction;
  target_value: number | null; confidence: number;
  evidence: string[]; rationale: string; risks: string[];
}
export interface Stance {
  agent: string; target_agent: string; stance: StanceKind;
  revised_confidence: number; message: string;
}
export interface PriorityResult {
  priority_scores: Record<string, number>;
  roles: Record<string, Role>;
}
export interface DebateMessage {
  round: number; agent: string; status: AgentStatus;
  message: string; target_agent: string | null;
}

// ---------- Safety and plan ----------
export interface RuleHit { rule_id: string; outcome: SafetyOutcome; detail: string; }
export interface PlanItem { action: string; reason: string; target: string | null; }
export interface Plan {
  horizon_hours: number; high_priority: PlanItem[]; medium_priority: PlanItem[];
  monitoring: string[]; safety_status: string; next_reassessment: string;
  expected_score_change: string | null; explanation: string; steps_target: number | null;
}
export interface SafetyResult {
  result: SafetyOutcome; rules_triggered: RuleHit[]; modified_plan: Plan | null;
}

// ---------- Cycle and what-if ----------
export interface CycleResponse {
  cycle_id: string; priority: PriorityResult; proposals: Proposal[];
  stances: Stance[]; coalitions: string[][]; debate: DebateMessage[];
  safety: SafetyResult; plan: Plan | null; escalated: boolean; twin: TwinState;
}
export interface WhatIfRequest { changes: Record<string, number>; }
export interface WhatIfResponse {
  simulated_twin: TwinState; effects: Record<string, string>;
  simulated_plan: Plan | null; safety: SafetyResult;
  comparison: { current: Record<string, number>; simulated: Record<string, number> };
  disclaimer: string;
}

// ---------- API inputs ----------
export interface ObservationIn {
  timestamp: string; pain: number; sleep_hours: number; steps: number;
  swelling: number; temperature: number; heart_rate: number; crp: number;
  night_awakenings?: number | null; flags?: string[];
  scenario_overrides?: Record<string, number> | null;
}
export interface AuditEntry {
  timestamp: string; cycle_id: string; actor: string;
  event: string; rule_id: string | null; outcome: string;
}
export interface ApiError { error: { code: string; message: string } }

// ---------- WebSocket (discriminated union on "type") ----------
export interface AgentStatusPayload {
  agent: AgentId; status: AgentStatus; confidence: number | null;
  recommendation: string | null; role: Role | null;
}
export type WsMessage =
  | { type: "twin_update"; payload: TwinState }
  | { type: "debate_message"; payload: DebateMessage }
  | { type: "agent_status"; payload: AgentStatusPayload }
  | { type: "plan"; payload: Plan }
  | { type: "safety"; payload: SafetyResult }
  | { type: "escalation"; payload: { cycle_id: string; summary: string } };
```

Rules for the frontend:
- `tsconfig.json` has `"strict": true`. `npm run build` must pass with zero errors.
- `api.ts` returns these typed objects (for example `getTwin(): Promise<TwinState>`); `ws.ts` parses messages into `WsMessage` and switches on `type` (exhaustive `switch`, no default that hides new types).
- The mock API (`frontend/src/mock/`) must also satisfy these types.
- If the backend contract changes, update section 2, section 7 and this section together, in one commit.

---

## 12. Extensions (additive; sections 1 to 11 do NOT change)

The twin schema, proposal schema, rules R1-R8 and the definition of exactly 7 agents stay frozen. Extensions add new files, endpoints and one table only. Screening and evaluation are workflow components / tools, not agents. Extension TypeScript types go in `frontend/src/types.ext.ts` (`types.ts` stays untouched).

Fixed label strings (use exactly):
- `SCREENING_DISCLAIMER = "Screening flag only. Not a diagnosis. Clinician review required."`
- `EVAL_DISCLAIMER = "Technical evaluation on synthetic data. Not clinical validation."`
- `BODY_DISCLAIMER = "Visualization of prototype scores. Not an anatomical or physiological simulation."`

### 12.1 Screening flags (`backend/app/workflow/screening.py`)

```python
class ScreeningFlag(Strict):
    flag_id: Literal["SF1", "SF2", "SF3", "SF4", "SF5"]
    title: str
    severity: Literal["info", "review", "urgent"]     # "info" is reserved, unused
    evidence: list[str] = Field(min_length=1)          # real twin / observation facts
    recommendation: str                                 # clinician review wording
    disclaimer: str                                     # SCREENING_DISCLAIMER

class ScreeningResult(Strict):
    patient_id: str
    flags: list[ScreeningFlag]
    disclaimer: str                                     # SCREENING_DISCLAIMER

def screen(twin: TwinState, flags: list[str], history: list[HistoryEntry]) -> ScreeningResult
```

`thresholds.yaml` section (add; do not change other sections):

```yaml
screening:
  SF1: {title: "Possible infection pattern",
        review: {temperature_at_least: 37.8, crp_at_least: 7.0},
        urgent: {temperature_at_least: 38.0, wound_flags: [wound_redness, wound_discharge, wound_opening]}}
  SF2: {title: "Possible clot warning signs",
        review: {flag: calf_pain, swelling_at_least: 6.0},
        urgent: {flags_any: [chest_pain, breathlessness], calf_pain_swelling_at_least: 7.0}}
  SF3: {title: "Delayed healing pattern",
        review: {overall_in: [below_expected, deteriorating], consecutive_readings: 2}}
  SF4: {title: "Uncontrolled pain pattern",
        review: {pain_at_least: 7.0, consecutive_readings: 2}}
  SF5: {title: "Slow mobility progress",
        review: {steps_fraction_below: 0.60, consecutive_readings: 2}}
```

Rules:
- One flag per id, with the highest severity that applies. Order flags SF1..SF5.
- "Consecutive readings" = the current reading plus the previous N-1 `history` entries. For SF5 use the current step target for all of them.
- Wording: use "pattern", "warning signs", "clinician review recommended". Never "diagnosed", "you have", "confirmed" or a treatment instruction. `recommendation` example: "Clinician review recommended."
- Screening never changes the plan or the safety result.
- Consistency: whenever any flag has severity `urgent`, `SafetyGuardian.evaluate` on the same state must return `escalate`.

Golden vectors (must pass):
| # | State | Expected |
|---|---|---|
| S1 | Meera baseline, empty history, no flags | `flags == []` |
| S2 | temperature 38.2, observation flags `["wound_discharge"]` | SF1 `urgent` |
| S3 | temperature 37.9, crp 7.5, no flags | SF1 `review` |
| S4a | flags `["calf_pain"]`, swelling 7.5 | SF2 `urgent` |
| S4b | flags `["calf_pain"]`, swelling 6.5 | SF2 `review` |
| S5 | flags `["chest_pain"]` | SF2 `urgent` |
| S6a | pain 7.5, previous history pain 7.2 | SF4 `review` |
| S6b | pain 7.5, previous history pain 5.0 | no SF4 |
| S7a | steps 1400 (target 2500), previous steps 1300 | SF5 `review` |
| S7b | steps 1400, previous steps 2400 | no SF5 |
| S8 | trajectory.overall `below_expected` now and in the previous entry | SF3 `review` |

API: `GET /api/patients/{id}/screening` -> `ScreeningResult` (uses the current twin, its history and the flags of the latest observation).

### 12.2 Synthetic cohort evaluation (`backend/app/evaluation/`)

Purpose: a technical evaluation on a seeded synthetic cohort with ground truth. It is not clinical validation. Runs in rule-based fallback mode (no LLM).

`thresholds.yaml` section (add):

```yaml
evaluation:
  default_cohort_size: 200
  max_cohort_size: 500
  default_seed: 2026
  readings_per_day: 4            # every 6 hours
  post_op_days: [3, 4, 5, 6]
  missing_reading_rate: 0.03
  group_prevalence: {stable: 0.50, infection_like: 0.10, clot_like: 0.10,
                     delayed_healing: 0.10, uncontrolled_pain: 0.10, mobility_decline: 0.10}
  full_cycle_every_n_readings: 4
  max_runtime_s: 60
```

Generator (`generator.py`) requirements:
- Uses `numpy.random.default_rng(seed)`; identical output for the same seed and cohort size.
- Must NOT read or import the `safety_rules` or `screening` thresholds. It has its own constants (baseline curves, noise, event strengths) so ground truth is independent of the rules.
- Each patient: profile (age 45-80, Total Knee Replacement), readings every 6 hours across post-op days 3-6, measurement noise, about 3% missing readings.
- Groups and injected events (each with random `onset_index` and `strength` in 0.4-1.0; weaker events may legitimately go undetected):
  - `infection_like`: temperature rises 0.9-1.6 C over about 12 h and crp index +2 to +4; wound flag with probability 0.6.
  - `clot_like`: `calf_pain` flag with probability 0.8, swelling +1.5 to +3; `chest_pain` with probability 0.15.
  - `delayed_healing`: pain and inflammation stop falling and stay above the expected curve.
  - `uncontrolled_pain`: pain +2 to +3 above baseline, sustained.
  - `mobility_decline`: steps fall to 35-55 percent of the daily target.
  - `stable`: no event; with probability 0.2 one harmless spike (one reading with pain +1.5, or steps -25 percent).
- Group to expected flag: infection_like -> SF1, clot_like -> SF2, delayed_healing -> SF3, uncontrolled_pain -> SF4, mobility_decline -> SF5.

Definitions:
- **Detected** (deteriorating patient): after the onset reading there is at least one screening flag with severity `review` or `urgent`, or a `SafetyGuardian` result of `escalate`.
- **Strict false alarm** (stable patient): any `urgent` flag or any `escalate` at any reading. **Lenient false alarm**: any `review` flag or deviation detected.
- **Hours to detection**: (first detected reading index - onset index) x 6 hours.
- **Flag type match**: a detected patient has the expected flag id after onset.
- **Confusion matrix**: positive = deteriorating group; predicted positive = detected at any time (any severity review or urgent, or escalate).
- **95% CI**: Wilson interval for proportions.
- **AUC**: probability that a random stable patient has a higher last-reading `recovery_score` than a random deteriorating patient (ties count 0.5).

```python
class EvaluationRunRequest(Strict):
    cohort_size: int = Field(default=200, ge=20, le=500)
    seed: int = 2026

class Confusion(Strict):
    tp: int; fn: int; fp: int; tn: int

class GroupMetrics(Strict):
    group: str
    n: int
    detected: int
    sensitivity: float
    ci_low: float
    ci_high: float
    median_hours_to_detection: Optional[float] = None
    flag_type_match_rate: Optional[float] = None

class SafetyInvariants(Strict):
    max_step_increase_ok: bool          # no plan asks for more than +10% steps
    no_forbidden_medication_terms: bool # rule R5 never violated in any proposal/plan
    urgent_implies_escalation: bool
    deterministic_rerun: bool           # same seed -> same report_hash
    violations: list[str] = []

class EvaluationReport(Strict):
    run_id: str
    created_at: str
    seed: int
    cohort_size: int
    mode: Literal["fallback"]
    sensitivity_overall: float
    sensitivity_ci: tuple[float, float]
    false_alarm_rate_strict: float
    false_alarm_rate_lenient: float
    median_hours_to_detection: Optional[float] = None
    recovery_score_auc: float
    confusion: Confusion
    per_group: list[GroupMetrics]
    safety: SafetyInvariants
    report_hash: str                    # sha256 of the report excluding run_id, created_at, report_hash
    limitations: list[str]
    disclaimer: str                     # EVAL_DISCLAIMER
```

`limitations` must include at least: synthetic data designed by the team; thresholds are illustrative; results can look better than reality; not clinical validation.

Database (additive table): `evaluation_runs(run_id PK, created_at, seed, cohort_size, report_json JSON)`.
API: `POST /api/evaluation/run` (`EvaluationRunRequest` -> `EvaluationReport`, must finish within `max_runtime_s`; if needed run the full swarm cycle only every `full_cycle_every_n_readings` readings while twin, screening and safety run on every reading); `GET /api/evaluation/latest` -> `EvaluationReport` (404 error object if none).
Script: `scripts/run_evaluation.py` prints a readable summary.

Required tests:
- Same seed and size give an identical `report_hash`; a different seed gives a different one.
- All four safety invariants are `true` with an empty `violations` list.
- Report validates as `EvaluationReport` and contains the disclaimer and limitations.
- Smoke expectations (investigate, do NOT tune safety or screening thresholds to fit): events with strength 0.8 or more are detected at least 90 percent of the time; strict false alarm rate on stable patients is reported honestly. If a smoke expectation fails, adjust the generator only if it is unrealistic, and tell a human.

### 12.3 3D body twin (frontend)

Read-only visualization of the twin. Placed inside the Digital Twin screen; no new screen. Files: `frontend/src/components/body/BodyTwin3D.tsx`, `bodyMapping.ts` (pure), `BodyFallback2D.tsx`. Dependencies: `three`, `@react-three/fiber`, `@react-three/drei` (check that the versions match the installed React), `@types/three`; dev-only `vitest` for the mapping tests.

`frontend/src/types.ext.ts` (extension types; `types.ts` unchanged):

```ts
import type { TwinState } from "./types";

export type Severity = "info" | "review" | "urgent";
export type FlagId = "SF1" | "SF2" | "SF3" | "SF4" | "SF5";
export interface ScreeningFlag {
  flag_id: FlagId; title: string; severity: Severity;
  evidence: string[]; recommendation: string; disclaimer: string;
}
export interface ScreeningResult { patient_id: string; flags: ScreeningFlag[]; disclaimer: string; }

export interface EvaluationRunRequest { cohort_size: number; seed: number; }
export interface Confusion { tp: number; fn: number; fp: number; tn: number; }
export interface GroupMetrics {
  group: string; n: number; detected: number; sensitivity: number;
  ci_low: number; ci_high: number;
  median_hours_to_detection: number | null; flag_type_match_rate: number | null;
}
export interface SafetyInvariants {
  max_step_increase_ok: boolean; no_forbidden_medication_terms: boolean;
  urgent_implies_escalation: boolean; deterministic_rerun: boolean; violations: string[];
}
export interface EvaluationReport {
  run_id: string; created_at: string; seed: number; cohort_size: number; mode: "fallback";
  sensitivity_overall: number; sensitivity_ci: [number, number];
  false_alarm_rate_strict: number; false_alarm_rate_lenient: number;
  median_hours_to_detection: number | null; recovery_score_auc: number;
  confusion: Confusion; per_group: GroupMetrics[]; safety: SafetyInvariants;
  report_hash: string; limitations: string[]; disclaimer: string;
}

export type BodyRegion = "knee" | "calf" | "chest" | "legs";
export type OutlineColor = "green" | "yellow" | "orange" | "red";
export interface BodyMarker { region: BodyRegion; flag_id: FlagId; severity: Severity; }
export interface BodyParams {
  knee_scale: number; pain_hz: number; pain_intensity: number; heat: number;
  walk_speed: number; outline: OutlineColor; markers: BodyMarker[];
  site: "knee"; operated_side: "left" | "right";
}
// bodyMapping.ts:  export function twinToBodyParams(twin: TwinState, flags: ScreeningFlag[]): BodyParams
```

Mapping (inputs clamped to 0-10; no rounding; tests use a tolerance of 1e-6):

| Output | Formula |
|---|---|
| `knee_scale` | `1 + 0.06 * observations.swelling` |
| `pain_hz` | `0.5 + 0.25 * observations.pain` |
| `pain_intensity` | `observations.pain / 10` |
| `heat` | `scores.inflammation_score / 10` |
| `walk_speed` | `scores.mobility_capacity / 10`, and `0` if that is below `0.1` |
| `outline` | `on_track` green, `slightly_below_expected` yellow, `below_expected` orange, `deteriorating` red |
| `markers` | SF1, SF3, SF4 -> `knee`; SF2 -> `chest` if any evidence text contains "chest" or "breath", else `calf`; SF5 -> `legs` |
| `site`, `operated_side` | constant table: Total Knee Replacement -> knee, right |

Golden values (Meera baseline, no flags): `knee_scale 1.36`, `pain_hz 2.0`, `pain_intensity 0.6`, `heat 0.62`, `walk_speed 0.5`, `outline "yellow"`, `markers []`.
The What-If ghost body uses `twinToBodyParams(simulated_twin, ...)` at 45 percent opacity. A "Simple view" (2D SVG, same overlays) is used if WebGL is unavailable or when toggled. Always show `BODY_DISCLAIMER` and a legend with the real values.

### 12.4 Simulator status extension (additive)

`GET /api/patients/{id}/simulator/status` -> `SimulatorStatus` (validates patient existence, returns active scenario status metadata).

Pydantic / TypeScript Model (`SimulatorStatus`):
```python
class SimulatorStatus(Strict):
    scenario_name: Optional[str] = None
    step_index: int = Field(ge=0)
    total_steps: int = Field(ge=0)
    minute_offset: int = Field(ge=0)
```

### 12.5 Twin reference extension (additive)

`GET /api/patients/{id}/twin/reference` -> `TwinReference` (validates patient existence, returns expected trajectory metrics sytematically sourced from `thresholds.yaml`).

`curves` is the full expected reference table for the twin's surgery type across post-op days 1–7 (same for any patient with that surgery type), while `expected_pain`, `expected_inflammation`, and `expected_steps` are this specific twin's current-day expected values.

Pydantic / TypeScript Model (`TwinReference`):
```python
class TwinReference(Strict):
    surgery: str
    post_op_day: int = Field(ge=0)
    expected_pain: float = Field(ge=0, le=10)
    expected_inflammation: float = Field(ge=0, le=10)
    expected_steps: int = Field(ge=0)
    curves: dict[str, dict[str, float]]  # outer key: metric name ("pain", "inflammation", "step_target"), inner key: post-op day string ("1".."7")
```

### 12.6 Additions summary

| Item | Addition |
|---|---|
| Endpoints | `GET /api/patients/{id}/screening`, `POST /api/evaluation/run`, `GET /api/evaluation/latest`, `GET /api/patients/{id}/simulator/status`, `GET /api/patients/{id}/twin/reference` |
| Table | `evaluation_runs` |
| Config | `screening:` and `evaluation:` sections in `thresholds.yaml` |
| Python files | `workflow/screening.py`, `evaluation/generator.py`, `evaluation/runner.py`, `scripts/run_evaluation.py` |
| Frontend files | `types.ext.ts`, `components/body/*` |
