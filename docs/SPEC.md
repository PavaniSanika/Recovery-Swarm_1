# RECOVERY-SWARM: Technical Design Document (SPEC)

> Source of truth for the build. Frozen schemas are in `CONTRACTS.md`. Rules for the coding agent are in `../AGENTS.md`.

A Self-Organizing Multi-Agent System for Personalized Post-Surgical Recovery Optimization Using Real-Time Physiological Digital Twins

*Tech stack  |  AI models  |  Agent design  |  Digital twin  |  System architecture  |  System design  |  Technical requirements  |  Implementation plan*

**Prototype for an Agentic AI Hackathon (24–48 hours)**

Final architecture revision. Positioned as clinical decision-support, not an autonomous doctor. Uses synthetic data only.

# Contents

1. Project Overview (final architecture, scope)
2. The Idea in Simple Words
3. Technology Stack
4. AI Models: What We Use and What We Do Not
5. Core Design Principle: LLMs Reason, Deterministic Rules Decide Safety
6. The Physiological Digital Twin (official state)
7. The 7 Agents, Workflow Components and Proposal Schema
8. Self-Organizing Agent Swarm and Priority Router
9. Negotiation, Safety Veto and Escalation
10. What-If Simulator
11. Early Warning System
12. Synthetic Data and Real-Time Simulator
13. Demo Mode / Scenario Controller
14. System Architecture
15. System Design (flows, workflow, sequence)
16. Data Model and API Design
17. User Interface Design (six screens)
18. Technical Requirements
19. Step-by-Step Implementation Plan, Team Division and PPT Workflow
20. Project Folder Structure
21. Testing Plan and Official Demo Flow
22. Risks, Limitations and Safety Positioning
23. Final Summary
24. Appendix A: Approved Extensions (screening flags, synthetic cohort evaluation, 3D body twin)

# 1. Project Overview

**RECOVERY-SWARM** is a self-organizing multi-agent system built around a continuously updated **Physiological Digital Twin**. It is designed for people recovering from major surgery (orthopedic, cardiac, abdominal). After surgery every patient recovers differently, but today most patients receive the same static discharge instructions and get help only after something goes wrong.

RECOVERY-SWARM keeps a continuously updated digital picture of the patient (the Digital Twin), lets a team of specialized AI agents study it, lets those agents **debate** what to do next, applies a deterministic **safety check**, and produces a personalized plan for the **next 6–12 hours**. When new data arrives the cycle repeats.

### One-line description

**RECOVERY-SWARM is a self-organizing multi-agent AI system that continuously maintains a lightweight physiological digital twin of a post-surgical patient, dynamically coordinates specialized agents, and safely optimizes the patient’s next 6–12 hours of recovery using synthetic real-time data.**

### Final architecture and flow

This is the final flow of the system. Every later section follows it.

```
Synthetic Patient Data / Wearable Simulator
↓
Data Ingestion
↓
Physiological Digital Twin
↓
Deviation Check
↓
Priority Router
↓
Specialist Agent Swarm
↓
Agent Debate / Coalition Formation
↓
Negotiation Coordinator
↓
Rule-Based Safety Guardian
↓
Plan Generator
↓
Final 6–12 Hour Recovery Optimization Plan
↓
Persistence + Visualization
↓
New Patient Data  →  Digital Twin Update  →  Repeat
```

The system has **exactly 7 conceptual agents** (Section 7). Data Ingestion, Deviation Check, Priority Router, Plan Generator and Persistence / History are **workflow components** (graph nodes), not agents.

The **What-If Simulator** branches from the current Digital Twin state, modifies one or more parameters, simulates the resulting state, runs the agent swarm again, performs the safety check and shows an illustrative outcome (Section 10). The live twin is never changed by a simulation.

**Guiding principle: LLMs reason; deterministic rules decide safety.**

### The core loop

**MONITOR → UNDERSTAND → DEBATE → SAFETY CHECK → OPTIMIZE → FEEDBACK → REPEAT**

### What makes it different

- **Self-organizing agent swarm:** the agents that lead, support or wait change with the patient’s current twin state (defined precisely in Section 8).
- **Structured agent debate:** agents support, oppose or revise each other’s structured proposals.
- **Deterministic safety veto:** a rule-based Safety Guardian that LLM agents cannot override.
- **What-if simulation** on a copy of the twin, with the same swarm and safety rules.
- **Closed loop:** new data updates the twin, which changes the next recommendation.

### What we will build

- Synthetic patient data and a simulated wearable stream, controlled by a deterministic Demo Mode
- A JSON-based Digital Twin with transparent scoring formulas (official schema in Section 6)
- 7 agents: Twin Builder, 4 specialists, Safety Guardian, Negotiation Coordinator, plus the workflow components around them
- Agent negotiation with structured proposals, confidence scores and stances
- A rule-based Safety Guardian that can allow, modify, reject or escalate
- What-if simulation, early-warning detection, recovery charts and a decision history
- Six screens: Dashboard, Digital Twin, Agent Swarm, Recovery Plan, What-If, Clinician View
- Approved extensions (Appendix A): screening flags for clinician review, a synthetic cohort technical evaluation and a read-only 3D body twin

### HACKATHON PROTOTYPE SCOPE

The prototype **will use**:

- Synthetic patient data.
- Simulated wearable streams.
- Illustrative recovery scoring.
- Prototype rule-based safety logic.
- LLM-based agent reasoning.
- Simulated medication-response patterns.

The prototype **will NOT perform**:

- Real diagnosis.
- Real medication prescribing.
- Autonomous medication changes.
- Real clinical decision-making.
- Real patient treatment.
- Clinical validation.
- Real hospital integration.

These may be future extensions. Also out of scope for the 24–48 hour build: a complex physiological simulation and training our own medical AI model. **Approved extensions (Appendix A)** add simulated screening flags (not a diagnosis), a technical evaluation on a synthetic cohort (not clinical validation) and a read-only 3D body visualization. They do not change the list above: the prototype still does not diagnose, prescribe, change medication, treat patients or claim clinical validation.

# 2. The Idea in Simple Words

Imagine a small recovery team sitting beside the patient 24 hours a day. One member watches pain and walking. One watches swelling and healing. One watches medicine effects. One watches sleep. A safety officer can say “no” to anything risky. A team leader listens to everyone and writes one plan.

RECOVERY-SWARM is that team, made of software. Three ideas make it different from a normal monitoring app:

1. **It builds a Digital Twin.** The patient is represented as a live data object that changes every time new readings arrive.
2. **The agents disagree on purpose.** A mobility agent may say “walk more” while the sleep agent says “rest first”. The disagreement is resolved by a transparent scoring method and then checked by safety rules.
3. **It optimizes instead of only alerting.** It keeps asking: “What is the safest and most useful adjustment for the next 6–12 hours?”

### Running example used in this document

**Mrs. Meera Sharma**, age 62, Total Knee Replacement, Post-Operative Day 4. Pain 6/10, sleep 4.5 hours, 1,800 steps against a target of 2,500, moderate swelling, elevated CRP, paracetamol plus a low-dose opioid at night. Digital Twin: inflammation score 6.2/10, healing slightly below expected, **Recovery Score 68 / 100**.

# 3. Technology Stack

The stack is deliberately simple and popular, so every team member can find help quickly and nothing needs special hardware. This is the **final stack**.

| Layer | Technology | Why we chose it |
|---|---|---|
| Frontend framework | React + Vite + TypeScript (strict) | Fast to build; the compiler checks every screen against the frozen data contracts |
| Frontend types | types.ts (TypeScript interfaces) | One frozen set of types that mirrors the backend Pydantic models and the WebSocket messages |
| Styling | Tailwind CSS | Clean UI quickly without writing custom CSS |
| Charts | Recharts | Simple line and area charts for trends |
| Agent graph view | React Flow (optional) | Draws the swarm and live message flow if time remains |
| 3D body twin (extension) | three + React Three Fiber + drei | Read-only 3D body driven by the twin, inside the Digital Twin screen |
| Frontend tests (extension) | vitest (dev only) | Unit tests for the pure body-mapping function |
| Backend language | Python 3.11 | Best ecosystem for AI agents and data |
| Backend framework | FastAPI + Uvicorn | Fast, async, automatic API docs |
| Validation | Pydantic v2 | Typed schemas for the twin, proposals and plans |
| AI orchestration | LangGraph | Explicit graph, parallel nodes, conditional routing, loops |
| LLM | One selected LLM provider, structured JSON output | Reasoning, debate stances and plan wording |
| Database | SQLite by default; PostgreSQL supported | Zero setup for dev, tests and the demo; switch to PostgreSQL with one DATABASE_URL line |
| ORM | SQLAlchemy 2 | Clean models for twin states, decisions and safety events |
| Data / simulation | Python, NumPy, Pandas | Synthetic patients, wearable simulator, trends |
| Real-time | WebSocket (FastAPI) | Streams twin updates and the agent debate live to the UI |
| Testing | pytest | Unit tests for safety rules and scoring |
| Tooling | Git, VS Code | Version control and development |

### Why LangGraph and not CrewAI?

Our swarm needs three behaviours: agents that run in parallel, a router that changes which agents matter, and a loop where a rejected plan goes back for revision. LangGraph models exactly this as a graph with a shared state and conditional edges, and gives us full control. We use **LangGraph as the only orchestration framework**. CrewAI is not used unless there is a specific implementation reason.

# 4. AI Models: What We Use and What We Do Not

### Do we train any model?

**No.** We do not train or fine-tune anything. Training a medical model needs real patient data and clinical validation, which is impossible and unsafe for a hackathon. We use one pre-trained Large Language Model (LLM) through an API, and plain Python for everything else.

### Which parts use a model and which do not

| Component | Technique | LLM needed? |
|---|---|---|
| Digital Twin scoring | Weighted formulas in Python | No |
| Trend and deviation detection (Deviation Check) | Slopes and reference curves (NumPy) | No |
| Priority Router (who leads) | Heuristic scoring on twin values | No |
| Specialist agent reasoning | LLM with structured output | **Yes** |
| Debate stances (support / oppose / revise) | LLM with structured output | **Yes** |
| Negotiation Coordinator scoring and conflict resolution | Weighted arithmetic + rules | No |
| Safety Guardian | Deterministic rules R1 to R8 | **No (on purpose)** |
| Plan Generator (wording and explanation) | LLM, given the already-decided actions | **Yes** |
| What-if effects | Coefficient table | No |
| Synthetic data and wearable stream | Python generator | No |

### Recommended LLM

- **Primary: Claude Sonnet via the Anthropic API.** Strong at following instructions and returning clean JSON, which our structured debate depends on.
- **Alternatives:** Gemini Flash (free tier), GPT-4o-mini, or a local Llama 3.1 8B through Ollama as an offline fallback (lower quality).
- **Select one provider and use it for the whole prototype.** The four specialist agents share the same model but each has its own system prompt, its own slice of the twin, and its own output role.

### LLM settings

| Setting | Value | Reason |
|---|---|---|
| Temperature | 0.0 to 0.2 | Stable, repeatable demo behaviour |
| Output format | JSON validated by Pydantic | Debate must be data, not free text |
| Max tokens per agent call | About 600 | Keeps latency and cost low |
| Timeout and retries | 20 seconds, 2 retries | Avoid a frozen demo |
| Fallback | Rule-based proposals if the LLM fails | Demo never crashes |
| Cost | About 6 to 10 short calls per cycle | A few cents per cycle; low for the whole hackathon |

# 5. Core Design Principle: LLMs Reason, Deterministic Rules Decide Safety

The biggest risk in a medical multi-agent demo is that it looks like one language model role-playing five characters. It is also unsafe to let an LLM decide alone. We avoid both problems with a **hybrid design**.

**“LLMs reason; deterministic rules decide safety.”**

| LLMs are used for | Plain code and rules are used for |
|---|---|
| Reading the twin and proposing an action with evidence | Computing every score and trend |
| Responding to other agents (support, oppose, revise) | Priority Router scoring and lead / support roles |
| Writing the final plan in friendly language (Plan Generator) | Weighted scoring and conflict resolution |
| Explaining why the plan was chosen | **Safety veto and escalation triggers** |

Four rules follow from this:

1. **Agents talk in structured data.** Every proposal follows the official Agent Proposal Schema (Section 7). The Coordinator can score data; it cannot score a paragraph. We never rely on parsing arbitrary natural-language agent responses.
2. **The LLM never has the last word on safety.** The Safety Guardian is deterministic code with final veto authority. It can be unit tested and it cannot hallucinate. LLM agents cannot override it.
3. **Every claim is traceable.** Each recommendation is stored with the agent, the evidence and the rule that allowed or changed it.
4. **One shared state.** All components read from and write through the single Digital Twin state (Section 6).

# 6. The Physiological Digital Twin

### What it is

The Digital Twin is a structured JSON object that describes the patient’s **current recovery state** and is updated whenever new information arrives. It is not a 3D model. For this project, a well-designed state object with history is exactly what a lightweight twin should be.

## OFFICIAL DIGITAL TWIN STATE

**The Digital Twin is the single shared patient state used by all agents.** All components must read from and write updates through this common state rather than maintaining independent, incompatible patient states. The structure below is the **canonical prototype schema** and is frozen.

```
{
  "patient_id": "P001",

  "profile": {
    "name": "Meera Sharma",
    "age": 62,
    "surgery": "Total Knee Replacement",
    "post_op_day": 4
  },

  "observations": {
    "pain": 6.0,
    "sleep_hours": 4.5,
    "steps": 1800,
    "swelling": 6.0,
    "temperature": 37.1,
    "heart_rate": 84,
    "crp": 6.2
  },

  "scores": {
    "inflammation_score": 6.2,
    "mobility_capacity": 5.0,
    "sleep_quality": 3.5,
    "medication_effectiveness": 5.5,
    "complication_risk": 3.2,
    "recovery_score": 68
  },

  "trajectory": {
    "overall": "slightly_below_expected",
    "inflammation": "stable_high",
    "mobility": "below_expected",
    "sleep": "poor"
  },

  "medications": {
    "current": [
      "Paracetamol",
      "Low-dose opioid at night"
    ],
    "response_score": 5.5
  },

  "history": []
}
```

### Notes on the schema

- **Recovery Score** is a prototype heuristic score from 0 to 100. It must NOT be described as a clinically validated probability. Recovery Score is an illustrative prototype metric and is not a clinically validated prediction.
- **crp** is a prototype-scaled CRP index (0 to 10) in the synthetic data, not a laboratory unit.
- **medications.response_score** is the medication-response detail used by the Medication Response Agent and is kept equal to scores.medication_effectiveness.
- **history** holds compact earlier snapshots (timestamp, observations, scores, overall trajectory). Trends and slopes are computed from history on demand by the Twin Engine and handed to agents as a derived helper; they are not extra stored fields.
- The daily step target (2,500 on day 4) and the expected recovery curves live in a reference table in the config file, not in the frozen twin.
- Optional simulator-only fields such as night_awakenings are stored with the raw observation record in the database and feed the derived scores; they are not part of the frozen twin structure.

### How the twin is updated (Twin Builder Agent)

1. New readings arrive from the Python simulator (or patient entry) through Data Ingestion.
2. Validate them (ranges, missing values). Missing values are marked, never invented.
3. Store the raw observation in the database.
4. Recompute every score with the formulas below.
5. Compute trends from the last 3 to 5 history snapshots.
6. Compare with the reference recovery curve for that surgery and post-operative day.
7. Set the trajectory labels, append the previous state to history and save a new twin state.

### Transparent scoring formulas

All formulas are simple heuristics with weights stored in a config file. We state openly that they are **illustrative and not clinically validated**. This honesty is a strength when judges ask “where does 68 come from?”. The sample values in the canonical schema are the outputs of these formulas for Meera’s synthetic data (medication_effectiveness and complication_risk come from the scenario file).

| Twin value | How it is computed |
|---|---|
| inflammation_score (0-10) | 0.7 x crp + 0.3 x swelling, plus 0.1 for every 0.1 C above 37.0 (Meera: 4.34 + 1.80 + 0.10 = 6.2) |
| mobility_capacity (0-10) | 10 x (steps / step target) x (1 - pain / 20) (Meera: 7.2 x 0.70 = 5.0) |
| sleep_quality (0-10, higher is better) | 10 x (sleep_hours / 7.5) minus a disturbance penalty (0 to 3) from night awakenings (Meera: 6.0 - 2.5 = 3.5) |
| medication_effectiveness (0-10) | 10 x (0.6 x average pain drop after a dose + 0.4 x how long relief lasts vs the dosing interval) |
| complication_risk (0-10) | Rule points: temp above 37.8 (+1), CRP rising (+1.5), asymmetric swelling (+1), pain rising 3 readings (+1), age above 60 (+0.5) |
| recovery_score (0-100) | 100 - 100 x weighted sum of penalties (below) |

### Recovery Score worked example

Each penalty is scaled between 0 and 1. The weights add up to 0.68, so the score never falls below 32. For Mrs. Meera:

| Factor | Penalty (0-1) | Weight | Contribution |
|---|---|---|---|
| Pain (6 / 10) | 0.60 | 0.17 | 0.102 |
| Inflammation score (6.2 / 10) | 0.62 | 0.17 | 0.105 |
| Mobility gap (1 - 1800/2500) | 0.28 | 0.14 | 0.039 |
| Sleep deficit (1 - 4.5/7.5) | 0.40 | 0.10 | 0.040 |
| Complication risk (3.2 / 10) | 0.32 | 0.10 | 0.032 |
| **Total penalty** |  | 0.68 | **0.319** |

Recovery Score = 100 x (1 - 0.319) = **about 68 / 100**. The weights can be tuned so that synthetic “good” and “bad” patients produce sensible ranges. **Recovery Score is an illustrative prototype metric and is not a clinically validated prediction.**

### Trajectory labels (twin.trajectory)

| Field | Allowed values | Rule |
|---|---|---|
| overall | on_track | Pain, inflammation and mobility all within tolerance of the reference curve |
|  | slightly_below_expected | One or two metrics worse than expected by a small margin |
|  | below_expected | Two or more metrics clearly worse, or improvement stalled for 24 hours |
|  | deteriorating | Any key metric getting worse for 2 to 3 consecutive readings |
| inflammation | improving / stable_high / worsening | Slope of inflammation_score over recent history |
| mobility | on_track / below_expected / declining | Steps and mobility_capacity against the reference curve |
| sleep | good / fair / poor | sleep_quality above 6 / 4 to 6 / below 4 |

# 7. The 7 Agents, Workflow Components and Proposal Schema

The final system has **exactly 7 conceptual agents**. Only four of them need LLM reasoning; the others are deterministic code, but they still act as members of the swarm.

| # | Agent | Implementation |
|---|---|---|
| 1 | Twin Builder Agent | Deterministic code (no LLM) |
| 2 | Inflammation & Healing Agent | LLM with structured output + rule fallback |
| 3 | Mobility & Pain Agent | LLM with structured output + rule fallback |
| 4 | Medication Response Agent | LLM with structured output + rule fallback (restricted scope) |
| 5 | Sleep & Recovery Agent | LLM with structured output + rule fallback |
| 6 | Risk & Safety Guardian | Deterministic rules R1 to R8 (no LLM) |
| 7 | Negotiation Coordinator | Weighted scoring and conflict rules in code |

### Workflow components (NOT agents)

The following are workflow components or graph nodes, not independent specialist agents, and they are never counted as agents:

| Component | What it does | Implemented as |
|---|---|---|
| Data Ingestion | Validates and stores each new observation | FastAPI route + graph node |
| Deviation Check | Compares the twin with the expected recovery curve and looks for red flags | Rule-based graph node |
| Priority Router | Reads the twin and assigns relevance scores to specialist agents (Section 8) | Heuristic graph node |
| Plan Generator | Turns the approved decision into the user-facing 6-12 hour plan and explanation | Graph node using the LLM for wording only |
| Persistence / History | Saves twin states, proposals, debate, decisions and safety events | SQLAlchemy + SQLite (PostgreSQL-ready) |

### What is an agent in our code?

An agent is one **LangGraph node**: a Python function that reads the shared state, calls the LLM (or uses rules), and writes a structured result back to the state. Every LLM agent is made of four parts:

- **A system prompt** that defines the specialty, the limits and the output format
- **An input slice** of the twin (only what this agent needs)
- **An output schema** (Pydantic) so the reply is validated data
- **A fallback** rule so the agent still returns something if the LLM fails

## OFFICIAL AGENT PROPOSAL SCHEMA

Every specialist agent must return a **structured proposal** rather than unrestricted free-form text. The LLM is responsible for the reasoning and for producing the structured proposal. The Coordinator, the Safety Guardian and all other components operate on this structured data. **We do not rely on parsing arbitrary natural-language agent responses.**

Example (the Mobility & Pain Agent’s revised proposal for Meera after the stance round):

```
{
  "agent": "mobility",
  "action_type": "mobility",
  "direction": "maintain",
  "target_value": 1900,
  "confidence": 0.82,
  "evidence": [
    "Pain = 6",
    "Steps = 1800",
    "Swelling = moderate"
  ],
  "rationale": "Mobility is below target but pain and swelling
                limit aggressive increase.",
  "risks": [
    "Increased pain",
    "Increased swelling"
  ]
}
```

**Required fields:** agent, action_type, direction, target_value (where applicable), confidence, evidence, rationale, risks.

### Pydantic model

```
class Proposal(BaseModel):
    agent: str
    action_type: Literal["mobility", "sleep", "swelling",
                         "pain_review", "monitoring", "escalate"]
    direction: Literal["increase", "maintain", "decrease"]
    target_value: float | None      # e.g. steps target
    confidence: float               # 0.0 to 1.0
    evidence: list[str]             # facts used from the twin
    rationale: str                  # short reasoning
    risks: list[str]                # what could go wrong
```

### Example agent function (Mobility & Pain)

```
def mobility_agent(state: SwarmState) -> dict:
    twin = state["twin"]
    prompt = MOBILITY_PROMPT.format(
        twin=twin.slice(["pain", "steps", "swelling",
                         "mobility_capacity", "trends"]))
    try:
        out = llm.with_structured_output(Proposal).invoke(prompt)
    except Exception:
        out = rule_based_mobility(twin)   # fallback
    return {"proposals": [out]}
```

### Example system prompt (shortened)

```
You are the Mobility & Pain agent in a post-surgical recovery
team. You receive the patient's digital twin. Propose ONE action
for the next 6-12 hours about walking and exercise.
Rules:
- Never recommend medication changes.
- Use only facts from the twin; list them in `evidence`.
- Give a confidence between 0 and 1.
- Prefer gradual changes (10% or less per day).
Return JSON matching the Proposal schema and nothing else.
```

## The seven agents

### 7.1 Twin Builder Agent (code, no LLM)

- **Role:** builds and updates the Digital Twin.
- **Inputs:** patient entries, simulated wearable data, medication log, lab values.
- **Logic:** validation, formulas from Section 6, slopes from history, curve comparison.
- **Output:** new twin state and a list of changes (for example “pain 5 to 7, sleep 6 to 4 hours: possible deterioration”).

### 7.2 Inflammation & Healing Agent (LLM)

- **Role:** studies inflammation, swelling and the healing trend.
- **Inputs:** inflammation_score and slope, swelling, crp, expected curve.
- **Typical output:** “Inflammation is stable and high, slower than expected. Recommend conservative activity and swelling control.”

### 7.3 Mobility & Pain Agent (LLM)

- **Role:** balances movement, pain and rest.
- **Inputs:** steps, target, pain, swelling, mobility_capacity.
- **Typical output:** “Hold 1,800 to 2,000 steps until pain and swelling improve.” Gradual increases only.

### 7.4 Medication Response Agent (LLM, restricted scope)

- **Role:** analyzes how well medication controls pain in the synthetic scenario: pain before, pain after, how long relief lasts, sleep effect.
- **Inputs:** the medication log and pain readings around each dose.

The Medication Response Agent **MAY**:

- Analyze medication-response patterns.
- Identify whether observed symptoms appear to correlate with medication timing in the synthetic scenario.
- Identify possible reduced effectiveness.
- Identify patterns that may require professional review.
- Recommend “clinical review” when appropriate.

The Medication Response Agent **MUST NOT**:

- Recommend a medication dosage.
- Increase a dosage.
- Decrease a dosage.
- Start a medication.
- Stop a medication.
- Recommend a new medication.
- Make a diagnosis.
- Independently make a critical clinical decision.

Any medication-related change must remain under qualified healthcare professional oversight. **Typical output:** “Relief wears off before bedtime. Clinical review of pain-management timing is recommended.”

**How the limit is enforced (not just requested in the prompt):**

- The agent may only return action_type pain_review, monitoring or escalate, enforced by schema validation.
- Safety rule R5 rejects any medication start, stop or dose change coming from any agent and converts it into “review with clinician”.
- **The prototype demonstrates this limitation explicitly:** during the demo the presenter shows the Medication Response Agent recommending clinical review, and the Safety Guardian blocking a dosage-change request (Section 21).

### 7.5 Sleep & Recovery Agent (LLM)

- **Role:** links sleep with recovery.
- **Inputs:** sleep_hours, sleep_quality, night awakenings, night pain, daytime activity.
- **Typical output:** “Sleep quality is poor and night pain is high. Prioritize sleep-supportive actions tonight.”

### 7.6 Risk & Safety Guardian (deterministic rules, no LLM)

- **Role:** safety layer with **final veto authority** over unsafe prototype recommendations. Details in Section 9.
- **Logic:** rules R1 to R8, each a small tested Python function.
- **Output:** one of four results: ALLOW, MODIFY, REJECT or ESCALATE (to clinician review), with the rule that fired.
- The Safety Guardian is not an LLM-only safety layer, and LLM agents cannot override it.

### 7.7 Negotiation Coordinator (code, no LLM)

- **Role:** collects proposals, runs the debate rounds, applies weighted scoring, resolves conflicts and produces the draft decision that goes to the Safety Guardian.
- **Logic:** weighted scoring and conflict rules in code. After the Safety Guardian approves, the Plan Generator (a workflow component) turns the decision into the user-facing plan.

# 8. Self-Organizing Agent Swarm and Priority Router

## SELF-ORGANIZING AGENT SWARM

In RECOVERY-SWARM, “self-organizing” does **not** mean that agents arbitrarily rewrite their own code or architecture. Instead, the system **dynamically reorganizes agent participation based on the patient’s current Digital Twin state**. The self-organizing behavior consists of:

1. Dynamic agent activation and prioritization.
2. Dynamic assignment of lead and supporting roles.
3. Temporary coalitions between relevant agents.
4. Agents supporting, opposing or revising other agents’ proposals.
5. Dynamic proposal weighting based on the current patient state.
6. Reconfiguration of the debate according to the current recovery problem.

### Example A: pain and swelling are high

- The Mobility & Pain Agent becomes highly relevant.
- The Inflammation & Healing Agent becomes highly relevant.
- The Sleep & Recovery Agent may become a supporting agent.
- The Medication Response Agent may analyze the relationship between pain and sleep.
- The Safety Guardian remains active as a mandatory safety layer.

### Example B: sleep becomes the dominant issue

- The Sleep & Recovery Agent can become the lead specialist.
- The Mobility and Inflammation agents can become supporting agents.

This is the primary mechanism that makes the swarm self-organizing. It is implemented with simple, explainable math (below) rather than anything opaque.

## Priority Router mechanism

The **Priority Router** is a workflow component (not an agent). It reads the current Digital Twin and assigns a relevance (priority) score between 0 and 1 to each specialist agent.

| Specialist agent | Main signals read from the twin | Example priority score |
|---|---|---|
| Mobility & Pain | pain, steps against target, swelling, mobility_capacity | 0.90 |
| Sleep & Recovery | sleep_hours, sleep_quality, night pain | 0.88 |
| Inflammation & Healing | inflammation_score, swelling, crp, trajectory.inflammation | 0.85 |
| Medication Response | medication_effectiveness, pain relief timing around doses | 0.70 |

Example current state: pain high, sleep poor, inflammation elevated, mobility below target. The exact scoring is heuristic for the prototype. **Priority scores are prototype coordination signals and are not clinical risk probabilities.**

### Lead, supporting and coalition

- The highest-relevance agents (the **top 3** by priority score) become **lead participants** (vote weight x1.5). Other agents remain **supporting participants** when relevant (x1.0). An agent whose score is below 0.30 simply waits this round.
- The Safety Guardian is **always active** and is never outvoted.
- Agents whose proposals push in the same direction on the same topic form a **temporary coalition** and their scores add up. For Meera, the Sleep, Inflammation and Medication agents all favour a conservative night, so they form a coalition against a walking increase.
- In the Agent Swarm screen each agent shows its role in the current round: Analyzing, Waiting, Supporting, Challenging, Revising, Vetoing or Approved.

### The focus changes with the patient

| Situation | Who leads, who supports |
|---|---|
| Pain and swelling high | Mobility & Pain and Inflammation & Healing lead; Sleep supports; Medication analyzes pain-sleep link; Safety always on |
| Sleep dominant | Sleep & Recovery leads; Mobility and Inflammation support |
| Severe pain | Mobility & Pain, Medication Response, Sleep, then Safety |
| Rising inflammation | Inflammation & Healing, Safety, Mobility, then Sleep |
| Meera today (Section 2) | Mobility & Pain, Sleep, Inflammation lead; Medication supports; Safety always on |

# 9. Negotiation, Safety Veto and Escalation

### The negotiation, step by step

1. **Round 1, proposals.** The active specialist agents run in parallel and each returns one structured proposal.
2. **Round 2, stances.** Each agent sees the other proposals and returns one stance per proposal: support, oppose or revise, with a new confidence. This is the visible debate, and it is where coalitions form.
3. **Scoring.** For each topic (activity, sleep, swelling, pain review), the Negotiation Coordinator calculates: score = agent weight x priority score x confidence x stance (+1 support, -1 oppose, 0 neutral). Weights change with the patient state because the priority scores do.
4. **Conflict resolution.** The **conservative-first rule**: when the top options on activity conflict, choose the safer one unless the safety rules allow more.
5. **Safety check.** The draft plan goes to the Safety Guardian. Rules R4 and R5 are also applied to each proposal as soon as it is produced, so an unsafe option can be vetoed during the debate; the full rule set R1 to R8 runs on the draft plan.
6. **Result.** ALLOW: continue. MODIFY: use the corrected plan. REJECT: return to step 4 with the new constraint (maximum two loops). ESCALATE: send to clinician review and stop optimizing.
7. **Plan writing.** The Plan Generator writes the 6–12 hour plan and “why” explanation using only the decided actions and the evidence.

### Safety Guardian authority

The Safety Guardian is **not** an LLM-only safety layer. It uses deterministic prototype rules to:

1. **ALLOW** a recommendation.
2. **MODIFY** a recommendation.
3. **REJECT** a recommendation.
4. **ESCALATE** to clinician review.

The Safety Guardian has **final veto authority** over unsafe prototype recommendations. The LLM agents cannot override it. Principle: **“LLMs reason; deterministic rules decide safety.”**

### Safety Guardian rules

Thresholds are examples for a prototype and are stored in one config file so a clinician could review them.

| ID | Rule | Action |
|---|---|---|
| R1 | Pain 8 or more, or rising by 2 or more points in 24 hours | Block any activity increase; escalate |
| R2 | Swelling moderate-to-severe and increasing | Cap activity at current level |
| R3 | Red flags: temperature 38.0 or more, chest pain, breathlessness, one-sided calf pain or swelling | Immediate clinician escalation |
| R4 | Step target increase above 10% per day | Modify to 10% maximum |
| R5 | Any medication start, stop or dose change | Reject; convert to “review with clinician” |
| R6 | Sleep under 4 hours and pain 7 or more | No aggressive activity |
| R7 | Missing key data or agent confidence under 0.5 | Ask for data or escalate |
| R8 | Wound warning signs (redness, discharge, opening) | Escalate for clinical review |

### Safety rule schema (thresholds.yaml)

Each rule is one small entry, so all four developers can read and extend the rules in the same format:

```
- id: R4
  name: step_increase_cap
  applies_to: [proposal, plan]
  condition: "mobility.target_value > steps * 1.10"
  outcome: modify          # allow | modify | reject | escalate
  modify_to: "steps * 1.10"
  message: "Activity increase capped at 10 percent per day"
```

### Escalation to a clinician

When a rule requires escalation, the system sends a clinician summary: what changed, which data was used, what the agents concluded, which rule fired and what action is recommended for human review. The system recommends escalation or review; it does not diagnose the patient or replace a clinician. Medication changes, diagnosis and critical decisions always remain with qualified healthcare professionals.

### Worked example (Mrs. Meera)

- Round 1: Mobility proposes increasing to 2,200 steps (confidence 0.70). Sleep: prioritize sleep tonight (0.85). Inflammation: conservative activity, control swelling (0.80). Medication: recommend clinical review of pain timing (0.75).
- Safety screening: R4 flags the 2,200-step proposal (an increase of about 22 percent, above the 10 percent daily cap) and would modify it to 1,980. This is the “Safety Guardian: reject aggressive activity increase” moment in the debate.
- Round 2: Sleep, Inflammation and Medication oppose the increase and form a coalition. Mobility revises to maintain about 1,900 steps (confidence 0.82), which is the proposal shown in the schema example.
- Final check: the revised plan passes R4, any medication change would be blocked by R5, and no escalation rule (R1, R3, R8) is triggered.
- Final plan: prioritize sleep, keep about 1,800 to 2,000 steps, monitor swelling, monitor pain and inflammation, and recommend clinical review of pain-management timing.

![Figure 1: Negotiation and safety decision flow (example: Mrs. Meera)](img/negotiation.png)

*Figure 1: Negotiation and safety decision flow (example: Mrs. Meera)*

# 10. What-If Simulator

The user asks a question such as “What if the patient walks 20% more today?”. The system tests the idea on a **simulation copy** of the twin. The live twin is never changed.

![Figure 2: What-If Simulator flow (branches from the current Digital Twin)](img/whatif.png)

*Figure 2: What-If Simulator flow (branches from the current Digital Twin)*

1. **Current Digital Twin:** take the latest twin state.
2. **Create simulation copy:** deep-copy the twin.
3. **Change selected parameter:** for example steps 1,800 x 1.2 = 2,160. More than one parameter can be changed.
4. **Recalculate derived state:** apply the effect model (below) and re-run the Twin Engine formulas.
5. **Run Priority Router** on the simulated twin.
6. **Run specialist agents** on the simulated twin.
7. **Debate:** stance round and Coordinator scoring as normal.
8. **Safety Guardian** checks the simulated plan.
9. **Simulated recovery plan** is produced and **compared with the current state**.

For the 20 percent example, rule R4 flags the jump because it exceeds 10 percent per day, so the simulated plan recommends a gradual increase of about 10 percent (around 1,980 steps) and continued monitoring of pain and swelling.

### Effect model (configurable, illustrative)

| Per +10% steps | Swelling below moderate | Swelling moderate or higher |
|---|---|---|
| Pain change | +0.1 | +0.3 |
| Swelling change | +0.1 | +0.4 |
| Sleep change (hours) | 0.0 | -0.1 |
| Mobility capacity change | +0.05 x capacity | +0.03 x capacity |

**Important:** the What-If result is an illustrative simulation based on prototype assumptions. It is NOT a clinical prediction. The UI shows this visible disclaimer next to every simulation:

**“Illustrative simulation only. Results are based on prototype assumptions and synthetic data and are not clinical predictions.”**

# 11. Early Warning System

The Deviation Check (a workflow component) compares the **expected recovery curve** with the **actual curve**. Reference curves are small JSON tables per surgery type, based on typical published recovery patterns and marked as approximate.

| Day | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| Expected pain | 7 | 6 | 5 | 4 |
| Actual pain (deviation case) | 7 | 6 | 7 | 8 |

### Deviation rules

- Actual pain is 2 or more points above expected for 2 consecutive readings.
- Any key metric worsens for 3 consecutive readings.
- Inflammation stops falling for 24 hours.

Output shown on the dashboard and in the Clinician View:

```
RECOVERY DEVIATION DETECTED
Pain is rising instead of following the expected trajectory.
Further clinical assessment is recommended.
```

In the Recovery Deviation demo scenario (pain up, inflammation up, mobility down) the Deviation Check flags the pattern, rule R1 fires, and the Safety Guardian escalates to clinician review.

# 12. Synthetic Data and Real-Time Simulator

The synthetic wearable simulator is kept from the original design. **Physical sensors are NOT required** for the hackathon prototype. Everything is produced by a Python simulator:

```
Python Simulator
↓
Synthetic Observation
↓
FastAPI
↓
Digital Twin
↓
Agents
```

### Simulated fields

- Pain, steps, sleep, heart rate, temperature
- Swelling and inflammation / CRP
- Medication response (pain before and after a dose, how long relief lasts)

### Time advancement

The simulator supports time advancement. Each tick creates one synthetic observation that passes through Data Ingestion and updates the Digital Twin. The WebSocket pushes the updated twin to the dashboard. Example:

| Time | Pain | Steps |
|---|---|---|
| 10:00 | 6.0 | 1800 |
| 10:05 | 5.9 | 1850 |
| 10:10 | 5.7 | 1910 |

A full optimization cycle (Priority Router, agents, debate, safety, plan) runs when the user clicks “Optimize Recovery”, and optionally every N ticks (configurable). Simulator values are generated from scripted scenario files with a fixed random seed, so the same scenario always produces the same data.

# 13. Demo Mode / Scenario Controller

The prototype includes a deterministic **Demo Mode** so the team can reliably demonstrate the system during the hackathon. It uses **synthetic data only**. Its purpose is to make the demonstration deterministic and repeatable.

```
[ Stable Recovery ]   [ Poor Sleep ]   [ Pain Spike ]

[ Increased Inflammation ]   [ Reduced Mobility ]

[ Recovery Deviation ]   [ Advance 1 Hour ]

[ Optimize Recovery ]   [ Run What-If ]
```

| Control | What it does | What to expect |
|---|---|---|
| Stable Recovery | Feeds readings that follow the expected curve | Trajectory on_track; gradual mobility increase allowed |
| Poor Sleep | Sleep drops to about 3.5 hours with more night awakenings | Sleep & Recovery becomes the lead specialist |
| Pain Spike | Pain rises by 2 or more points within 24 hours | R1 blocks activity increase; escalation |
| Increased Inflammation | CRP and swelling rise, temperature slightly up | Inflammation & Healing leads; R2 caps activity |
| Reduced Mobility | Steps fall to about 1,100 | Mobility & Pain leads; conservative recovery of walking |
| Recovery Deviation | Pain up, inflammation up, mobility down together | Deviation flagged; R1 fires; ESCALATE to Clinician View |
| Advance 1 Hour | Moves the simulated clock and creates new observations | Twin updates; charts move |
| Optimize Recovery | Runs the full swarm cycle (POST /cycle) | Debate, safety result, Recovery Plan |
| Run What-If | Runs the simulation copy flow (POST /whatif) | Simulated plan compared with current state |

### How determinism is achieved

- Scenarios are scripted JSON files with a fixed random seed.
- LLM temperature is near 0, and responses for the scripted scenarios can be cached.
- A “Reset to baseline” action clears the demo patient’s saved twin states, decisions, plans and simulation runs, and restores Meera’s Day 4 state.
- A fallback toggle runs the agents in rule-only mode if the internet fails.
- The buttons call the same API endpoints (Section 16) that the rest of the app uses.

# 14. System Architecture

RECOVERY-SWARM is a self-organizing multi-agent system built around a continuously updated Physiological Digital Twin. The system is built in five layers. Each layer talks only to its neighbours, which keeps the design simple to build and to explain. The final flow is shown in Section 1. Solid borders in the diagram are agents; dashed borders are workflow components.

![Figure 3: RECOVERY-SWARM layered system architecture](img/architecture.png)

*Figure 3: RECOVERY-SWARM layered system architecture*

| Layer | Responsibility |
|---|---|
| 1. Presentation | React dashboard with six screens: Dashboard, Digital Twin, Agent Swarm, Recovery Plan, What-If, Clinician View |
| 2. API | FastAPI: REST endpoints, WebSocket stream, request validation, Demo Mode controller |
| 3. Agent swarm | LangGraph graph: 7 agents (Twin Builder, 4 specialists, Safety Guardian, Negotiation Coordinator) plus workflow components (Data Ingestion, Deviation Check, Priority Router, Plan Generator) |
| 4. Deterministic engines | Plain Python: twin scoring, safety rules, deviation detection, what-if model |
| 5. Data | SQLite by default (PostgreSQL-ready); synthetic patients and a wearable simulator; persistence and history |
| External | One LLM API used by the specialist agents and the Plan Generator for reasoning, stances and wording |

### Architecture rules

- **One shared state:** all components read from and write through the official Digital Twin state.
- **LLMs reason; deterministic rules decide safety:** the Safety Guardian has final veto and LLM agents cannot override it.
- **Structured data between agents:** the official Agent Proposal Schema.
- **What-If uses the same swarm and rules** on a simulation copy of the twin.

# 15. System Design

## 15.1 Closed-loop recovery optimization

The heart of the design is a loop. New data updates the twin, the twin drives the agents, the agents produce a plan, and the patient’s next data shows the effect of that plan.

![Figure 4: Closed-loop recovery optimization](img/loop.png)

*Figure 4: Closed-loop recovery optimization*

## 15.2 Agent workflow (LangGraph graph)

Each numbered box is a LangGraph node. Solid borders are agents and dashed borders are workflow components. Dashed lines are the escalation path. The loop on the left is the reject-and-retry cycle, limited to two rounds.

![Figure 5: Agent workflow with parallel agents, safety loop and escalation](img/workflow.png)

*Figure 5: Agent workflow with parallel agents, safety loop and escalation*

### Shared state (what every node reads and writes)

```
class SwarmState(TypedDict):
    patient_id: str
    twin: Twin                          # official digital twin
    is_simulation: bool                 # true for what-if runs
    priority_scores: dict[str, float]   # from Priority Router
    lead_agents: list[str]
    proposals: Annotated[list, add]     # merged from parallel nodes
    stances: list[Stance]               # debate round
    coalitions: list[list[str]]
    draft_plan: Plan | None
    safety_result: Literal["allow","modify","reject","escalate"]
    retry_count: int
    final_plan: Plan | None
    debate_log: list[LogEntry]          # shown in the UI
```

### How the graph is wired (simplified)

```
g = StateGraph(SwarmState)
for name, fn in NODES.items():          # ingest, twin_builder ...
    g.add_node(name, fn)
g.add_edge(START, "ingest")
g.add_edge("ingest", "twin_builder")
g.add_edge("twin_builder", "deviation_check")
g.add_conditional_edges("deviation_check", route_red_flag,
    {"red_flag": "escalate", "normal": "priority_router"})
# router fans out to the 4 specialists in parallel
for a in SPECIALISTS:
    g.add_edge("priority_router", a)
    g.add_edge(a, "debate_round")
g.add_edge("debate_round", "coordinator")
g.add_edge("coordinator", "safety_guardian")
g.add_conditional_edges("safety_guardian", route_after_safety,
    {"ok": "plan_generator", "retry": "coordinator",
     "escalate": "persist"})
g.add_edge("plan_generator", "persist")
g.add_edge("persist", END)
swarm = g.compile()
```

For What-If runs the same compiled graph is invoked with is_simulation set to true on a copy of the twin. In that mode the persist node writes to simulation_runs and never to twin_states.

## 15.3 Request sequence for one cycle

![Figure 6: Sequence of one recovery cycle](img/sequence.png)

*Figure 6: Sequence of one recovery cycle*

## 15.4 Design decisions in brief

| Decision | Choice | Reason |
|---|---|---|
| State sharing | One official Digital Twin state object | Simple; every component reads the same facts |
| Agent output | Validated JSON (official Proposal schema) | Debate can be scored, stored and displayed |
| Safety | Deterministic rules with final veto | Testable; LLMs reason, rules decide safety |
| Concurrency | Specialists run in parallel | Lower latency (about one LLM call time) |
| Failure handling | Rule-based fallback per agent | Demo works even if the API fails |
| Explainability | Debate log + audit log (safety events) | Every recommendation can be traced |
| What-if | Same graph on a simulation copy | No duplicate logic; live twin untouched |

# 16. Data Model and API Design

## 16.1 Database design (SQLite default, PostgreSQL-ready)

The code is **database-neutral**: it uses SQLAlchemy 2 with the JSON column type and never uses SQLite-specific or PostgreSQL-specific features. **SQLite is the default** for development, tests and the demo. **PostgreSQL is a supported option**: switching is one line, DATABASE_URL=postgresql+psycopg://user:pass@host/recovery. Tests run on SQLite; if time allows, run them once on PostgreSQL before the demo. Pitch line: “SQLite for the prototype, PostgreSQL-ready through a single config change.” Entities:

| Table | Purpose |
|---|---|
| patients | Patient profile and care plan |
| observations | Every raw synthetic observation that enters through Data Ingestion |
| twin_states | Saved Digital Twin snapshots (full twin JSON) for history and charts |
| agent_proposals | Structured proposals from each agent, per round |
| debate_messages | Stances (support, oppose, revise) shown in the live debate |
| decisions | One row per cycle: priority scores, lead agents, coalitions, draft plan, safety result, escalation flag |
| safety_events | Every rule check and outcome (ALLOW, MODIFY, REJECT, ESCALATE); the audit trail |
| recovery_plans | The final 6-12 hour plan, priorities, monitoring and next reassessment |
| simulation_runs | What-if runs: changes, simulated state, simulated plan and verdict (references patients and twin_states) |
| evaluation_runs (extension) | Synthetic cohort evaluation reports: run id, seed, cohort size, report JSON |

![Figure 7: Database entity relationships](img/datamodel.png)

*Figure 7: Database entity relationships*

**Why it matters:** twin_states gives the recovery history and charts. agent_proposals and debate_messages store the debate. decisions and recovery_plans store the outcome. safety_events gives full traceability for the audit trail. simulation_runs keeps what-if results separate from the live twin.

## 16.2 API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | /api/patients/{id}/observations | Add new readings; triggers twin update |
| GET | /api/patients/{id}/twin | Current digital twin (official schema) |
| GET | /api/patients/{id}/twin/history | Snapshots for trend charts |
| POST | /api/patients/{id}/cycle | Run one swarm cycle (Optimize Recovery) |
| GET | /api/patients/{id}/decisions | Recovery plan history |
| GET | /api/patients/{id}/plan/latest | Latest Recovery Plan |
| GET | /api/decisions/{cycle_id}/debate | Proposals, stances, rules triggered |
| GET | /api/patients/{id}/audit | Audit trail (safety events and decisions) |
| POST | /api/patients/{id}/whatif | Run a what-if scenario on a simulation copy |
| POST | /api/simulator/inject | Inject a Demo Mode scenario (for example poor_sleep) |
| POST | /api/simulator/advance | Advance simulated time by one step |
| POST | /api/decisions/{id}/clinician-review | Clinician note or override |
| GET | /api/patients/{id}/screening | Screening flags for the current twin (extension) |
| POST | /api/evaluation/run | Run the synthetic cohort evaluation (extension) |
| GET | /api/evaluation/latest | Latest evaluation report (extension) |
| WS | /ws/patients/{id} | Live twin, debate and plan updates |

## 16.3 Frozen request and response formats

These formats are frozen in Phase 1 so frontend and backend can work in parallel. Twin, Proposal and safety objects always use the official schemas.

**POST /api/patients/P001/observations** (request):

```
{
  "timestamp": "2026-09-20T10:05:00",
  "pain": 5.9, "sleep_hours": 4.5, "steps": 1850,
  "swelling": 6.0, "temperature": 37.1,
  "heart_rate": 84, "crp": 6.2,
  "night_awakenings": 4
}
```

**POST /api/patients/P001/cycle** (response):

```
{
  "cycle_id": "C001",
  "priority_scores": {"mobility": 0.90, "sleep": 0.88,
                      "inflammation": 0.85, "medication": 0.70},
  "lead_agents": ["mobility", "sleep", "inflammation"],
  "proposals": [ ...official Proposal objects... ],
  "debate": [ {"agent": "sleep", "stance": "oppose", ...} ],
  "safety": {"result": "allow", "rules_triggered": []},
  "plan": { ...Recovery Plan object... },
  "twin": { ...official Digital Twin state... }
}
```

**POST /api/patients/P001/whatif** (request and response):

```
// request
{ "changes": {"steps_pct": 20} }
// response
{
  "simulated_twin": { ... },
  "effects": {"pain": "+0.6", "swelling": "+0.8", ...},
  "simulated_plan": { ... },
  "safety": {"result": "modify", "rules_triggered": ["R4"]},
  "comparison": { ...current vs simulated... },
  "disclaimer": "Illustrative simulation only. ..."
}
```

# 17. User Interface Design (Six Screens)

## 17.1 Official navigation

The official prototype navigation has exactly six screens:

```
RECOVERY-SWARM

  - Dashboard
  - Digital Twin
  - Agent Swarm
  - Recovery Plan
  - What-If
  - Clinician View
```

We do **not** add separate Login, Signup, Settings, Notifications, Patient Management or other non-essential screens to the hackathon scope, unless time remains after the core system is complete. The Demo Mode controls (Section 13) live in a small control bar, not in a separate screen.

The frontend is written in **TypeScript (strict mode)**. All API and WebSocket data use the interfaces in frontend/src/types.ts, which mirror the backend contracts and are frozen. This catches wrong field names and missing fields at build time instead of during the demo.

## 17.2 Screens overview

| Screen | What it shows | Main components |
|---|---|---|
| 1. Dashboard (Patient Dashboard) | Meera, Day 4; pain, sleep, steps, inflammation, swelling, Recovery Score (68 / 100) | Stat cards, status badge, latest plan |
| 2. Digital Twin | Pain, inflammation, mobility and sleep trends, the recovery trajectory against the expected curve, and the 3D body twin (Appendix A.4) | Recharts line charts, deviation banner, 3D body twin panel (extension) |
| 3. Agent Swarm | Agent status cards and the live debate on one page | Agent cards, chat-style debate log, optional React Flow graph |
| 4. Recovery Plan (Final Decision) | The simple 6-12 hour plan with reasons and safety status | Priority checklist, rule badges, explanation panel |
| 5. What-If | Input such as “walk 20% more”; current versus simulated state; simulated plan | Input or slider, comparison table, disclaimer |
| 6. Clinician View | Patient summary, twin, deviation, safety rule, recommendation and audit trail; screening flags and the evaluation panel (Appendix A) | Alert panel, audit table, flag list, evaluation panel |

Everywhere the score is shown the UI uses **Recovery Score: 68 / 100** with the note: Recovery Score is an illustrative prototype metric and is not a clinically validated prediction.

## 17.3 Agent Swarm screen

This page combines agent status and debate visualization instead of using separate screens. It should make the multi-agent nature of the project immediately visible to judges.

### Agent status

One card each for: Twin Builder, Mobility & Pain, Inflammation & Healing, Sleep & Recovery, Medication Response, Safety Guardian and Negotiation Coordinator. Each card shows:

- Current status
- Confidence
- Current recommendation
- Relevant evidence
- Role in the current round (lead or supporting, from the Priority Router)

Possible statuses: Analyzing, Waiting, Supporting, Challenging, Revising, Vetoing, Approved.

### Live debate (below the cards)

```
Mobility Agent:
  "Increase activity gradually."
Sleep Agent:
  "Prioritize sleep because sleep quality is currently poor."
Inflammation Agent:
  "Control swelling before increasing activity."
Safety Guardian:
  "Reject aggressive activity increase."
Coordinator:
  "Prioritize sleep and swelling control while maintaining
   conservative mobility."
```

## 17.4 Recovery Plan screen

The Recovery Plan converts complex agent reasoning into a simple user-facing plan. It contains: the next 6–12 hour plan, high-priority actions, medium-priority actions, monitoring instructions, the reason for each recommendation, the safety status, the next reassessment time and the expected prototype score change where applicable. Example:

```
RECOVERY PLAN - NEXT 12 HOURS

HIGH PRIORITY:
Improve sleep quality.
Reason:
Current sleep duration is only 4.5 hours.

MEDIUM PRIORITY:
Maintain conservative mobility.
Target:
1,800-2,000 steps.

HIGH PRIORITY:
Monitor swelling.

MONITOR:
Pain and inflammation.

SAFETY:
No predefined safety rule triggered.

NEXT REASSESSMENT:
Tomorrow morning.
```

## 17.5 Clinician View

The Clinician View is an important prototype screen. It shows: patient summary, current Digital Twin, recovery trajectory, recent changes, triggered deviation, agent recommendations, the safety rule triggered, the final system recommendation and the audit trail. Example:

```
RECOVERY DEVIATION DETECTED

Changes:
Pain up
Inflammation up
Mobility down

Triggered rule:
R1 (pain rising by 2 or more points in 24 hours)

Agent recommendation:
Hold activity; review pain and swelling with the clinical team.

Safety Guardian:
ESCALATE TO CLINICIAN REVIEW
```

The system recommends escalation or review. It does not diagnose the patient or replace a clinician.

## 17.6 What-If screen

Shows the input, the current versus simulated values for pain, swelling, sleep and mobility, the simulated recovery plan from the swarm, and always the visible disclaimer: “Illustrative simulation only. Results are based on prototype assumptions and synthetic data and are not clinical predictions.”

# 18. Technical Requirements

## 18.1 Hardware

| Item | Minimum | Recommended |
|---|---|---|
| Laptop CPU | Dual core | Quad core or better |
| RAM | 8 GB | 16 GB |
| Storage | 5 GB free | 10 GB free |
| GPU | Not required | Not required (LLM runs in the cloud) |
| Internet | Stable connection for LLM API | Mobile hotspot as backup |

## 18.2 Software and versions

| Software | Version | Use |
|---|---|---|
| Python | 3.11 or newer | Backend and agents |
| Node.js | 20 LTS or newer | Frontend build |
| FastAPI, Uvicorn | Latest stable | API server |
| LangGraph | Latest stable | Agent workflow |
| LLM SDK (one provider) | Latest stable | LLM calls |
| Pydantic | 2.x | Schemas |
| SQLAlchemy + SQLite | 2.x | Database access (default) |
| PostgreSQL + psycopg 3 | 14 or newer (optional) | Optional database, one DATABASE_URL line |
| NumPy, Pandas | Latest stable | Trends, data and simulation |
| pytest | Latest stable | Tests |
| React, Vite, TypeScript, Tailwind, Recharts | Latest stable | UI |
| Git, VS Code | Latest | Development |

## 18.3 Accounts and configuration

- An LLM API key for the one selected provider, stored in a .env file and never committed to Git.
- Environment variables: LLM_API_KEY, LLM_MODEL, DATABASE_URL (default sqlite:///./recovery.db; optional postgresql+psycopg://user:pass@host/recovery), FALLBACK_MODE, TEMPERATURE.
- Database: nothing to install for SQLite. Optional PostgreSQL check before the demo: create a database, set DATABASE_URL to the postgresql+psycopg line, run the tests once, then switch back. Tables are created by SQLAlchemy at startup; no manual SQL is required.
- One config file (thresholds.yaml) for safety rules, scoring weights, reference curves, step targets and what-if coefficients.

## 18.4 Python packages (requirements.txt)

```
fastapi
uvicorn[standard]
pydantic>=2
langgraph
langchain-anthropic   # or the SDK of the chosen provider
sqlalchemy>=2
psycopg[binary]>=3   # only needed for the optional PostgreSQL run
numpy
pandas
pyyaml
python-dotenv
websockets
pytest
```

## 18.5 Non-functional requirements

| Requirement | Target |
|---|---|
| Response time for one full cycle | Under 15 seconds (specialists in parallel) |
| Reliability | Fallback rules mean the demo never shows an error screen |
| Safety | No plan reaches the user without passing the Safety Guardian |
| Explainability | Every plan shows evidence, debate summary and the rules applied |
| Privacy | Synthetic data only; no real patient information |
| Auditability | Every decision and rule check is stored with a timestamp |
| Type safety | Frontend in TypeScript strict mode; types.ts matches the backend contracts; npm run build has zero type errors |
| Repeatability | Fixed seeds, temperature near 0 and scripted scenarios give the same demo each time |

# 19. Step-by-Step Implementation Plan, Team Division and PPT Workflow

Total effort is about 50 to 60 person-hours. With 4 people that is roughly 14 to 18 working hours, so a 24 to 48 hour hackathon is comfortable. Freeze new features at about 75% of the time and use the rest for testing and rehearsal. The order below is the official implementation order; contracts are frozen first so that four developers can start coding without re-deciding the architecture.

## 19.1 Official implementation order

| Phase | Steps | Lead |
|---|---|---|
| 1. Contracts | 1. Freeze Digital Twin schema.<br>2. Freeze Agent Proposal schema.<br>3. Freeze API request/response formats.<br>4. Freeze Safety Rule schema. | All four |
| 2. Data | 5. Create synthetic patient dataset.<br>6. Create wearable/sensor simulator.<br>7. Create deterministic demo scenarios. | Member 4 |
| 3. Digital Twin | 8. Implement Digital Twin.<br>9. Implement derived scores.<br>10. Implement recovery trajectory.<br>11. Implement history. | Member 2 |
| 4. Safety | 12. Implement deterministic Safety Guardian.<br>13. Implement deviation detection.<br>14. Implement escalation logic. | Member 2 + 1 |
| 5. Agents | 15. Implement specialist agent interfaces.<br>16. Implement rule-based fallback behavior.<br>17. Add LLM reasoning.<br>18. Enforce structured JSON outputs. | Member 1 |
| 6. Swarm | 19. Implement Priority Router.<br>20. Implement lead/support roles.<br>21. Implement temporary coalitions.<br>22. Implement debate.<br>23. Implement Negotiation Coordinator. | Member 1 |
| 7. Plan | 24. Implement Plan Generator.<br>25. Generate final 6-12 hour plan.<br>26. Store decision and reasoning. | Member 1 + 2 |
| 8. What-If | 27. Implement simulation copy of Digital Twin.<br>28. Implement parameter modification.<br>29. Re-run agents and safety.<br>30. Compare current vs simulated state. | Member 4 |
| 9. Frontend | 31. Patient Dashboard.<br>32. Digital Twin.<br>33. Agent Swarm.<br>34. Recovery Plan.<br>35. What-If.<br>36. Clinician View. | Member 3 |
| 10. Real-time | 37. Connect WebSocket / simulated live updates. | Member 2 + 3 |
| 11. Testing | 38. Test normal recovery.<br>39. Test poor sleep.<br>40. Test pain increase.<br>41. Test inflammation increase.<br>42. Test mobility decrease.<br>43. Test safety veto.<br>44. Test escalation.<br>45. Test What-If. | Member 4 + all |
| 12. Final demo | 46. Freeze features.<br>47. Capture screenshots.<br>48. Finalize PPT.<br>49. Rehearse demo.<br>50. Prepare judge Q&A. | All four |

Tip: the frontend is React with TypeScript in strict mode. The file types.ts mirrors CONTRACTS.md and is frozen like the backend models: no any, no ts-ignore, and npm run build must pass with no type errors. The frontend builds screens against mock JSON from the frozen contracts while the backend is being built. Build the rule-based path first (twin, safety, fallback agents), then add the LLM on top.

## 19.2 Team work division (4 members)

### MEMBER 1 — AI / MULTI-AGENT SYSTEM

| Area | Responsibilities |
|---|---|
| Prototype | – LangGraph<br>– Specialist agents<br>– Agent prompts<br>– Structured proposals<br>– Debate<br>– Coalition formation<br>– Negotiation Coordinator<br>– Safety integration |
| PPT | – Problem<br>– AI architecture<br>– Agent roles<br>– Self-organizing swarm<br>– Agent debate<br>– Novelty |
| Demo | Explain how agents reason, challenge each other and reach a decision. |

### MEMBER 2 — BACKEND / DIGITAL TWIN

| Area | Responsibilities |
|---|---|
| Prototype | – FastAPI<br>– Pydantic<br>– Database<br>– Digital Twin<br>– APIs<br>– WebSocket<br>– History<br>– Recovery Score<br>– Recovery trajectory |
| PPT | – System architecture<br>– Digital Twin<br>– Data flow<br>– Backend<br>– Technology stack |
| Demo | Explain how data enters, updates the Digital Twin and reaches the agents. |

### MEMBER 3 — FRONTEND / UI

| Area | Responsibilities |
|---|---|
| Prototype | – React<br>– Vite<br>– TypeScript (strict)<br>– Shared types.ts<br>– Tailwind<br>– Recharts<br>– Agent visualization<br>– Dashboard<br>– Digital Twin screen<br>– Recovery Plan<br>– What-If UI<br>– Clinician View |
| PPT | – UI screenshots<br>– Dashboard<br>– Digital Twin visualization<br>– Agent visualization<br>– Final prototype |
| Demo | Explain how the user interacts with the system. |

### MEMBER 4 — DATA / SIMULATION / INTEGRATION

| Area | Responsibilities |
|---|---|
| Prototype | – Synthetic patient data<br>– Wearable simulator<br>– Scenario engine<br>– Demo Mode<br>– What-If engine<br>– End-to-end integration<br>– Testing |
| PPT | – Synthetic data<br>– Simulation<br>– What-If<br>– Real-time loop<br>– Testing<br>– Future scope |
| Demo | Control the patient scenario and demonstrate changing recovery conditions. |

All four members work on the PPT and the prototype in parallel.

## 19.3 Parallel PPT + prototype workflow

The team will develop the PPT and the working prototype **in parallel**. Each member owns both:

1. A technical implementation area.
2. The corresponding PPT content.

While implementing, every member:

- Captures UI screenshots.
- Captures agent debate outputs.
- Captures Digital Twin states.
- Captures What-If results.
- Captures safety decisions.
- Captures the real-time simulation.
- Updates the PPT continuously.

Do not wait until the prototype is complete to start the PPT. The final PPT should use screenshots and outputs from the actual working prototype wherever possible.

## 19.4 Extensions after the core

Once the core is working (Stage C2 tagged), the team adds the approved extensions in Appendix A in stages H1 to H4 (about 21 to 30 person-hours in total). The core 50-step order above does not change, and the extensions never delay the core demo.

# 20. Project Folder Structure

```
recovery-swarm/
|-- backend/
|   |-- app/
|   |   |-- main.py              # FastAPI app, routes, websocket
|   |   |-- config.py            # env + thresholds.yaml loader
|   |   |-- models/              # Pydantic + SQLAlchemy models
|   |   |-- twin/
|   |   |   |-- engine.py        # scoring formulas, trends
|   |   |   |-- reference.py     # expected recovery curves
|   |   |-- agents/
|   |   |   |-- base.py          # LLM client, structured output
|   |   |   |-- mobility.py  inflammation.py  medication.py
|   |   |   |-- sleep.py
|   |   |   |-- coordinator.py   # scoring + conflict rules
|   |   |   |-- safety.py        # rules R1-R8 (no LLM)
|   |   |-- workflow/            # workflow components (not agents)
|   |   |   |-- ingest.py  deviation.py  router.py
|   |   |   |-- screening.py     # extension: screening flags
|   |   |   |-- planner.py       # Plan Generator
|   |   |-- graph.py             # LangGraph wiring
|   |   |-- whatif.py            # effect model + twin cloning
|   |   |-- simulator.py         # wearable stream + demo mode
|   |   |-- evaluation/          # extension: cohort generator + runner
|   |   |-- db.py                # SQLAlchemy session (SQLite/PostgreSQL)
|   |-- tests/                   # safety, scoring, scenarios
|   |-- thresholds.yaml
|   |-- requirements.txt
|-- frontend/
|   |-- src/
|   |   |-- pages/  Dashboard.tsx  Twin.tsx  Swarm.tsx
|   |   |           Plan.tsx  WhatIf.tsx  Clinician.tsx
|   |   |-- components/  StatCard.tsx  TrendChart.tsx
|   |   |                AgentCard.tsx  DebateLog.tsx
|   |   |-- types.ts     # frozen, mirrors CONTRACTS.md
|   |   |-- types.ext.ts # extension types (CONTRACTS section 12)
|   |   |-- components/body/  BodyTwin3D.tsx bodyMapping.ts
|   |   |                     BodyFallback2D.tsx
|   |   |-- api.ts   ws.ts
|   |-- package.json  tsconfig.json  vite.config.ts
|-- data/scenarios/              # synthetic patient + demo scenarios
|-- docs/                        # this document, diagrams, PPT
|-- .env.example
|-- README.md
```

# 21. Testing Plan and Official Demo Flow

## 21.1 Testing

| Test type | What is tested | Example |
|---|---|---|
| Unit tests | Scoring formulas and each safety rule | Pain 8 must trigger R1; a 22% step jump must trigger R4 |
| Schema tests | Agent outputs match the official Proposal schema | Invalid JSON is rejected and fallback runs |
| Scenario tests | The Demo Mode scenarios end to end | Normal recovery, poor sleep, pain increase, inflammation increase, mobility decrease |
| Safety veto test | Unsafe proposal is modified or rejected | Aggressive step increase is capped by R4 |
| Escalation test | Recovery Deviation scenario | Deviation flagged, R1 fires, ESCALATE reaches Clinician View |
| What-If test | Simulation copy and re-run | Live twin unchanged; simulated plan differs; disclaimer shown |
| Medication limit test | Medication Response Agent scope | A dose-change request is blocked by R5 and turned into clinical review |
| Screening tests (extension) | Golden screening cases | Meera baseline gives no flags; temperature 38.2 with a wound flag gives SF1 urgent |
| Evaluation tests (extension) | Cohort generator and report | Same seed gives identical report; safety invariants are 100% |
| Body mapping tests (extension) | Pure mapping function | Swelling 6 gives knee scale 1.36; pain 6 gives 2.0 Hz |
| Failure tests | LLM timeout or bad output | Rule-based fallback keeps the demo working |

## 21.2 Official hackathon demonstration

1. Open Meera’s Patient Dashboard.
2. Show: Pain = 6/10, Sleep = 4.5 hours, Steps = 1,800, Inflammation = 6.2, Recovery Score = 68 / 100.
3. Open the Digital Twin and show the expected trajectory versus the current trajectory.
4. Click “Optimize Recovery”.
5. The Priority Router identifies the relevant agents.
6. Specialist agents generate structured proposals.
7. Show agents supporting and challenging each other.
8. The Negotiation Coordinator resolves the proposals into a draft plan and the Safety Guardian checks it (the medication-limit moment can be shown here: clinical review recommended, dosage change blocked by R5).
9. The Plan Generator turns the approved decision into the final recovery plan.
10. Show the 6–12 hour Recovery Plan.
11. Open the What-If Simulator and ask: “What if the patient walks 20% more?”
12. Run the simulation.
13. Show how the simulated state affects pain, swelling, sleep and mobility.
14. Run the agents again.
15. Show the new simulated recommendation.
16. Return to the live patient state.
17. Inject a Recovery Deviation scenario: pain up, inflammation up, mobility down.
18. Show the Safety Guardian detecting the predefined deviation.
19. Show escalation to the Clinician View.
20. Show the complete audit trail.

*Note: in steps 8 and 9 the order follows the final flow (Coordinator, then Safety Guardian, then Plan Generator).*

## 21.3 Optional extension demo segment (about 2 minutes)

1. On the Digital Twin screen, show the 3D body for Meera: yellow outline, swollen knee, pulsing pain, slow walking.
2. Click Poor Sleep or Increased Inflammation and watch the body and values change.
3. Inject Recovery Deviation: the outline turns red, markers appear, and the Clinician View lists screening flags labelled “Not a diagnosis”.
4. Open the Evaluation panel and show the synthetic cohort results with the label “Technical evaluation on synthetic data. Not clinical validation.”

### Final story

**MONITOR → UNDERSTAND → DEBATE → SAFETY CHECK → OPTIMIZE → SIMULATE → FEEDBACK → REPEAT**

Rehearse the full flow until it runs cleanly three times in a row, and keep the fallback toggle and Reset to baseline ready. Prepare judge Q&A on: why LangGraph, why the Recovery Score is not a probability, how the Safety Guardian cannot be overridden, and how the What-If avoids clinical claims.

# 22. Risks, Limitations and Safety Positioning

| Risk | Mitigation |
|---|---|
| Debate looks like one LLM role-playing | Structured proposals, real per-agent calls, numeric scoring and a visible weighting table |
| Recovery Score is read as a clinical probability | Always named Recovery Score / 100, formula shown, disclaimer displayed |
| What-if has no true physiological model | Configurable coefficient table with the visible “illustrative simulation” disclaimer |
| LLM error or hallucination | Validated JSON, fallback rules, deterministic safety layer, evidence required in each proposal |
| Medication agent oversteps | Restricted action types, rule R5, dedicated test, explicit demo moment |
| API or internet failure during the demo | Fallback mode, cached responses for scripted scenarios, hotspot backup |
| Scope grows too large | Feature freeze at 75% of the time; keep the six core screens only |
| Clinical criticism | Position as decision support, state that thresholds are illustrative and need clinician review |
| Screening flags read as diagnoses | Fixed wording rules, visible disclaimer, flags never change the plan |
| Evaluation looks like validation | Mandatory label, limitations shown, no clinical claims |
| 3D panel slow or time-consuming | Simple shapes, one-day time-box, Simple SVG view fallback |

### Limitations we state openly

- Uses synthetic data only; it has not been validated on real patients.
- Scores and thresholds are illustrative heuristics, not clinical guidelines. Recovery Score is an illustrative prototype metric and is not a clinically validated prediction.
- What-If results are illustrative simulations, not clinical predictions.
- The system does not diagnose, prescribe or change medication. Screening flags are patterns for clinician review only.
- The synthetic cohort evaluation is a technical evaluation, not clinical validation.

### Safety positioning statement

RECOVERY-SWARM is a clinical decision-support and recovery-optimization prototype. It is **not** an autonomous doctor. It analyzes data, detects trends, simulates scenarios, explains its reasoning, flags risks and escalates concerning situations. Medication changes, diagnosis and critical clinical decisions remain under the oversight of qualified healthcare professionals.

# 23. Final Summary

**How RECOVERY-SWARM works:**

1. Synthetic patient data and a wearable simulator produce observations.
2. The Twin Builder maintains a continuously updated Physiological Digital Twin.
3. The Deviation Check compares the current state with the expected recovery trajectory.
4. The Priority Router identifies which specialist agents are most relevant.
5. Four specialist agents analyze the state and produce structured recommendations.
6. Agents support, challenge or revise each other’s proposals.
7. Temporary coalitions and lead/support roles emerge based on the current patient state.
8. The Negotiation Coordinator resolves competing recommendations.
9. The deterministic Safety Guardian allows, modifies, rejects or escalates the plan.
10. The Plan Generator produces a clear 6–12 hour Recovery Optimization Plan.
11. The decision, reasoning, safety result and Digital Twin state are stored.
12. New patient data arrives and the loop repeats.
13. The What-If Simulator allows users to test alternative changes before applying them to the simulated recovery state.

**One-line description:** RECOVERY-SWARM is a self-organizing multi-agent AI system that continuously maintains a lightweight physiological digital twin of a post-surgical patient, dynamically coordinates specialized agents, and safely optimizes the patient’s next 6–12 hours of recovery using synthetic real-time data.

**Final principle:**

**MONITOR → UNDERSTAND → DEBATE → SAFETY CHECK → OPTIMIZE → FEEDBACK → REPEAT**

# Appendix A. Approved Extensions

This appendix adds three extensions on top of the frozen core system: **simulated screening flags**, a **technical evaluation on a synthetic cohort**, and a **read-only 3D body twin**. They give the jury more to see and measure, without changing any frozen contract.

## A.1 Principles

- **Additive only.** The Digital Twin schema, the Agent Proposal schema, rules R1 to R8 and the definition of exactly 7 agents do not change.
- **Not agents.** Screening and evaluation are workflow components and tools; the 3D body is a UI component. The system still has exactly 7 agents.
- **Honest labels, always visible:** “Screening flag only. Not a diagnosis. Clinician review required.”, “Technical evaluation on synthetic data. Not clinical validation.”, and “Visualization of prototype scores. Not an anatomical or physiological simulation.”
- **Core first.** Start the extensions only after the core cycle works (Stage C2 tagged). The 3D body can start earlier using mock data.
- **Six screens stay six.** The 3D body lives inside the Digital Twin screen; screening flags and the evaluation panel live inside the Clinician View.

| Extension | What it is | Effort | Owner | Needs |
|---|---|---|---|---|
| Screening flags | Rule-based patterns for clinician review (workflow component) | 4 to 6 h | Member 2 | Twin engine, deviation check |
| Synthetic cohort evaluation | Seeded cohort with ground truth; detection, false alarms, safety checks | 6 to 8 h | Member 4 | Screening, swarm cycle |
| 3D body twin | React Three Fiber body driven by the twin | 8 to 12 h (5 to 6 h with simple shapes) | Member 3 | types.ts, mock API |
| UI wiring and demo | Flags in Clinician View, evaluation panel, 3D markers | 3 to 4 h | Members 3 and 4 | All of the above |

## A.2 Screening flags (simulated, not diagnosis)

A **screening flag** is a pattern in the synthetic data that a clinician would want to look at. It does not say what the patient has. It is implemented as a deterministic workflow component (backend/app/workflow/screening.py) that reads the twin, its history and the observation flags. It is not an agent.

| ID | Flag (wording) | Review level when | Urgent level when |
|---|---|---|---|
| SF1 | Possible infection pattern | Temperature 37.8 or more and CRP index 7.0 or more | Temperature 38.0 or more together with a wound flag (wound_redness, wound_discharge, wound_opening) |
| SF2 | Possible clot warning signs | calf_pain flag and swelling 6.0 or more | chest_pain or breathlessness flag, or calf_pain with swelling 7.0 or more |
| SF3 | Delayed healing pattern | Overall trajectory below_expected or deteriorating for 2 consecutive readings | Not used |
| SF4 | Uncontrolled pain pattern | Pain 7.0 or more for 2 consecutive readings | Not used |
| SF5 | Slow mobility progress | Steps below 60% of the daily target for 2 consecutive readings | Not used |

### Output object

```
class ScreeningFlag(BaseModel):
    flag_id: Literal["SF1","SF2","SF3","SF4","SF5"]
    title: str                      # wording from the table above
    severity: Literal["info","review","urgent"]
    evidence: list[str]             # real twin / observation facts
    recommendation: str             # clinician review wording
    disclaimer: str                 # fixed screening disclaimer
```

### Rules for screening

- **Wording:** allowed terms are “pattern”, “warning signs”, “screening flag” and “clinician review recommended”. Never write “diagnosed”, “you have”, “confirmed” or a treatment instruction.
- **No effect on the plan:** screening flags never change the recovery plan. The Safety Guardian rules still decide.
- **Consistency:** every urgent flag must coincide with an escalation by R1, R3 or R8. A test enforces this.
- **No false alarm on the baseline:** Meera’s baseline state produces no flags.
- **Where they appear:** Clinician View (list with evidence), a small badge on the Dashboard, and markers on the 3D body.
- **Thresholds** live in thresholds.yaml (section screening), like every other threshold.

## A.3 Synthetic cohort evaluation (technical evaluation, not clinical validation)

Real clinical validation needs real patient outcomes, ethics approval and regulatory steps, so it is **not possible** with synthetic data. What we can do honestly is a **technical evaluation**: run the system on a seeded synthetic cohort with known ground truth and measure how well it detects problems, how often it raises false alarms, and whether it always respects its safety invariants.

### Cohort generator (backend/app/evaluation/generator.py)

- Default 200 synthetic patients (configurable, maximum 500), fixed seed, deterministic.
- Each patient gets a random profile (age, surgery Total Knee Replacement) and readings every 6 hours across post-operative days 3 to 6.
- Ground-truth groups: about 50% stable, and about 10% each for infection-like, clot-like, delayed healing, uncontrolled pain and mobility decline. Each group has an injected event with a random onset time and a random strength.
- Realism: measurement noise, about 3% missing readings, and harmless one-off spikes in stable patients (for example one high pain reading) to test false alarms. Some injected events are deliberately weak, so detection is not perfect.
- The generator has its own parameters and does not read the safety or screening thresholds, so ground truth is not simply copied from the rules.

### Metrics reported

| Metric | Meaning |
|---|---|
| Sensitivity (overall and per condition) | Share of deteriorating patients where the system raised an escalation or a review/urgent flag after onset, with 95% confidence interval |
| False alarm rate | Share of stable patients with any urgent flag or escalation (and separately with any review flag) |
| Median time to detection | Hours between injected onset and the first flag or escalation |
| Flag type match | Share of detected patients where the flag type matches the injected condition (SF1 infection-like, SF2 clot-like, SF3 delayed healing, SF4 uncontrolled pain, SF5 mobility) |
| Recovery Score separation | Area under the curve for Recovery Score at the last reading, deteriorating versus stable |
| Confusion matrix | True and false positives and negatives for deteriorating versus stable |

### Safety invariants (must be 100%)

- No plan ever asks for a step target more than 10% above the current steps.
- No proposal or plan text contains a forbidden medication term (rule R5).
- Every urgent flag coincides with an escalation.
- Re-running the same cohort and seed gives an identical report (same hash).

### How it runs and how it is shown

- Runs in the rule-based fallback mode (no LLM), so it is fast and deterministic. The whole 200-patient run should finish in under 60 seconds; if needed, the full swarm cycle runs on every 4th reading while the twin, screening and safety rules run on every reading.
- Script: scripts/run_evaluation.py. API: POST /api/evaluation/run and GET /api/evaluation/latest. Results are stored in the evaluation_runs table.
- The Clinician View shows an **Evaluation panel**: metric cards, confusion matrix, per-condition table, the limitations list and a Run evaluation button.

### Limitations (shown in the report and the panel)

- Synthetic data generated by our own design: results show the system behaves as designed, not that it works on real patients.
- The scoring and thresholds are illustrative and not derived from clinical data.
- Numbers can look better than reality because the generator and the rules were written by the same team.
- **Label on every view:** “Technical evaluation on synthetic data. Not clinical validation.”

**Path to real validation (slide only, not built):** clinician review of thresholds, ethics approval, retrospective study on de-identified real data, then a prospective study.

## A.4 3D body twin (read-only visualization)

The 3D body twin is a **visualization of the prototype scores**. It shows the live Digital Twin on a body so that judges see the state at a glance. It is not an anatomical model and not a physiological simulation, and it makes no medical claims.

### Technology and placement

- React Three Fiber with three and drei, written in TypeScript (strict). Check that the installed React Three Fiber version matches the installed React version.
- The body is built from simple shapes (sphere head, capsule torso, arms and legs) so there is no asset licence risk and no large file. A licensed model may be used only if its licence allows it and it stays small.
- It appears as a panel inside the Digital Twin screen. The navigation stays at six screens.
- Files: frontend/src/components/body/BodyTwin3D.tsx, bodyMapping.ts (pure function), BodyFallback2D.tsx (simple SVG view). Extension types are in types.ext.ts; types.ts stays frozen.

### How twin data drives the body

| Twin value | Visual effect | Formula |
|---|---|---|
| scores / observations swelling (0-10) | Operated knee grows | knee scale = 1 + 0.06 x swelling (swelling 6 gives 1.36) |
| observations pain (0-10) | Red pulse at the operated site | pulse rate = 0.5 + 0.25 x pain Hz (pain 6 gives 2.0 Hz); intensity = pain / 10 |
| scores inflammation_score (0-10) | Warm colour at the knee and a faint overall tint | heat = inflammation_score / 10 (6.2 gives 0.62) |
| scores mobility_capacity (0-10) | Walking animation speed | walk speed = mobility_capacity / 10 (5.0 gives 0.5); below 0.1 the body stands still |
| trajectory.overall | Outline colour | on_track green, slightly_below_expected yellow, below_expected orange, deteriorating red |
| Screening flags | Markers on the body | SF1 and SF3 and SF4 at the knee, SF2 at the calf or chest, SF5 at the legs |
| What-If simulated twin | Ghost body next to the live one | second body at 45% opacity using the simulated twin |

The operated site comes from a small constant table (Total Knee Replacement maps to the right knee). Next to the body, a legend shows the real values (for example “Swelling 6.0: knee +36%”), so the mapping is transparent.

### Performance and fallback

- Target: smooth on the demo laptop (30 frames per second or more). Limit the pixel ratio, use simple materials and no post-processing.
- A **Simple view** toggle shows a flat SVG body with the same overlays. It is used automatically if WebGL is unavailable.
- Time-box: if the 3D panel is not working after one day of effort, keep only the Simple view.

### Tests

The mapping is a pure function (twin in, body parameters out) so it can be unit-tested. Golden values for Meera’s baseline: knee scale 1.36, pulse 2.0 Hz, intensity 0.6, heat 0.62, walk speed 0.5, outline yellow. A dev-only test runner (vitest) is allowed for these tests. npm run build must still have zero type errors.

## A.5 What we deliberately do not build

| Item | Why not | What we show instead |
|---|---|---|
| Autonomous medication changes | Unsafe and not accountable; it would remove our main safety principle (LLMs reason, deterministic rules decide safety) | Medication Response Agent recommends clinical review; rule R5 blocks any dose or drug change |
| Clinical validation | Needs real patient outcomes and ethics approval; synthetic data cannot validate | Technical evaluation on a synthetic cohort, clinician review of thresholds if available, and a path-to-validation slide |
| Real diagnosis or treatment | Not possible or allowed for a prototype on synthetic data | Screening flags for clinician review, clearly labelled |
| Physiological simulation | Would create unsupported medical claims | Illustrative what-if coefficients and the 3D visualization, both labelled |
| Reserved: simulated clinician-approved medication order workflow | Touches agent rules, safety rules, contracts and the Clinician View; decide only after the three extensions work | Not built unless explicitly approved |

## A.6 Answers for the jury

| Question | Suggested answer |
|---|---|
| Is this diagnosing patients? | No. It raises screening flags for clinician review, clearly labelled as not a diagnosis, on synthetic data. |
| Have you validated it clinically? | No, and we do not claim to. We ran a technical evaluation on a seeded synthetic cohort and report its limits. Real validation needs ethics approval and real patient data. |
| Why not let the AI change medication? | Because accountability must stay with clinicians. Our design lets LLMs reason but deterministic rules decide safety, and any medication change is escalated for review. |
| Is the 3D body a simulation? | No. It is a read-only visualization of our prototype scores, with the mapping shown on screen. |
| Are your metrics meaningful? | They show the system behaves as designed on synthetic cases with noise and weak signals. We state that the data and rules were designed by us, so they are not evidence of real-world performance. |

## A.7 Extension implementation stages (after the core)

| Stage | Build | Owner | Done when |
|---|---|---|---|
| H1 | Screening flags: rules, model, endpoint GET /screening, tests | Member 2 | Golden screening cases pass; Meera baseline gives no flags; urgent flags always coincide with escalation |
| H2 | Cohort generator, evaluation runner, report, endpoints, evaluation_runs table | Member 4 | Report is deterministic; safety invariants are 100%; run takes under 60 seconds |
| H3 | 3D body twin: mapping function, 3D component, Simple view, what-if ghost | Member 3 | Mapping tests pass; body reacts to each Demo Mode scenario; npm run build has zero errors |
| H4 | Wiring: flags in Clinician View and Dashboard badge, markers on 3D body, Evaluation panel, demo segment | Members 3 and 4 | Optional extension demo segment (Section 21.3) runs cleanly three times |
