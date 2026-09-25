# RECOVERY-SWARM 🩺🤖

**A Self-Organizing Multi-Agent System for Post-Surgical Recovery Optimization Using Real-Time Physiological Digital Twins**

RECOVERY-SWARM is a 24–48 hour hackathon prototype that continuously maintains a physiological Digital Twin of a post-surgical patient (e.g. Total Knee Replacement), dynamically coordinates specialized AI agents, resolves clinical trade-offs through structured debate, enforces deterministic safety rules, and generates personalized 6–12 hour recovery optimization plans using **synthetic data only**.

---

## 🌟 Key Architecture & Highlights

- **Physiological Digital Twin**: Real-time state synchronization tracking pain, CRP index, daily steps, swelling, sleep quality, and complication risk scores.
- **Dynamic Priority Routing**: Self-organizing router dynamically assigns `Lead`, `Supporting`, or `Waiting` roles to specialist agents based on the patient's current telemetry signals.
- **Structured Multi-Agent Debate**: Round-by-round stance evaluation, coalition formation (e.g., Sleep + Inflammation + Medication), and proposal revisions.
- **Deterministic Safety Guardian**: Non-LLM deterministic safety layer enforcing rules **R1–R8** (e.g., blocking activity increases during pain spikes $\ge 8.0/10$ or high fever $\ge 38.0^\circ\text{C}$) with absolute veto authority.
- **Strict Medication Safeguards**: Enforces Rule **R5** — agents cannot prescribe, adjust dosages, or diagnose. Recommends professional clinical review only.
- **Offline Fallback Engine**: `FALLBACK_MODE=true` runs the full multi-agent cycle with zero network or Gemini LLM dependencies.
- **Database Neutral**: SQLAlchemy 2 with SQLite default (PostgreSQL supported via `DATABASE_URL=postgresql+psycopg://...`).

---

## 🧩 The 7 System Agents & Workflow Components

| Component / Agent | Type | Role & Responsibilities |
|---|---|---|
| **Twin Builder** | Core Engine (Workflow) | Maintains digital twin telemetry state from observations. |
| **Inflammation & Healing** | Specialist Agent | Monitors CRP index, swelling, and tissue recovery trajectory. |
| **Mobility & Pain** | Specialist Agent | Evaluates physical activity capacity and step target progression. |
| **Sleep & Recovery** | Specialist Agent | Tracks sleep quality, duration, and rest-pain interactions. |
| **Medication Response** | Specialist Agent | Analyzes pain relief timing and flags pattern effectiveness for review. |
| **Risk & Safety Guardian** | Deterministic Safety Layer | Non-LLM rule engine (R1–R8) with final veto authority. |
| **Negotiation Coordinator** | Consensus Engine | Calculates priority-weighted consensus and generates draft plan. |

---

## 🖥️ The 6 Interactive UI Screens

1. **Dashboard (`DashboardPage.tsx`)**: Patient Meera Sharma (Day 4 Post-Op), telemetry stat cards, CRP Index (0–10 scale), Recovery Score (68/100), and latest plan summary.
2. **Digital Twin (`DigitalTwinPage.tsx`)**: Multi-day expected vs. actual trajectory comparison line charts (Recharts) sourced directly from `thresholds.yaml` reference curves, with active deviation banners.
3. **Agent Swarm (`AgentSwarmPage.tsx`)**: 7 agent status cards displaying priority routing scores, confidence, proposals, and a live round-by-round debate transcript.
4. **Recovery Plan (`RecoveryPlanPage.tsx`)**: 6–12 hour prioritized recovery plan, high/medium priority actions, continuous monitoring instructions, safety status, and interim guidance during clinical escalations.
5. **What-If Simulator (`WhatIfPage.tsx`)**: Test alternative scenarios (e.g. $+20\%$ steps, $+2.0\text{h}$ sleep) on a twin copy without modifying live patient state, complete with illustrative comparison metrics.
6. **Clinician View (`ClinicianViewPage.tsx`)**: Patient summary, safety escalation rule detail hits (e.g. Rule R1 trigger), specialist recommendations, and full database audit log ledger.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.11, FastAPI, Pydantic v2 (Strict), LangGraph, SQLAlchemy 2, pytest, NumPy/Pandas.
- **Frontend**: React 18, Vite, TypeScript (Strict Mode), Tailwind CSS, Recharts.
- **Real-Time**: FastAPI WebSockets.

---

## 🚀 Quick Start Guide

### 1. Backend Setup

```bash
cd backend
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

To run in **Offline Fallback Mode** (no Gemini API key required):
```env
FALLBACK_MODE=true
```

### 3. Run Backend Server & Test Suite

```bash
# Run complete test suite (100 tests)
$env:FALLBACK_MODE="true"; python -m pytest -q

# Start FastAPI dev server on port 8000
$env:FALLBACK_MODE="true"; python -m uvicorn app.main:app --reload --port 8000
```

### 4. Frontend Setup & Launch

Open a second terminal:

```bash
cd frontend
npm install

# Start Vite dev server
npm run dev

# Run strict TypeScript build check
npm run build
```

The UI will be available at `http://localhost:3000` (or `http://localhost:5173`).

---

## 🎬 Demo Verification Scripts

### 1. 20-Step Core Demo Check (SPEC Section 21.2)
```bash
# Run 20-step demo verification script (ensure backend is running on http://127.0.0.1:8000)
python scripts/demo_check.py
```

### 2. 4-Step Extension Segment Demo Check (SPEC Section 21.3)
```bash
# Run 4-step extension demo verification script
python scripts/demo_extensions.py
```

### The 20 Demo Steps:
1. Open Meera's Patient Dashboard (reset to baseline `meera_day4`).
2. Verify baseline metrics (Pain 6/10, Sleep 4.5h, Steps 1,800, Score 68/100).
3. Open Digital Twin & verify expected vs. actual recovery trajectory.
4. Click "Optimize Recovery" (`POST /api/patients/P001/cycle`).
5. Priority Router assigns Lead and Supporting roles dynamically.
6. Specialist agents generate structured proposals.
7. Observe agents supporting and challenging proposals in debate.
8. Negotiation Coordinator resolves draft plan; Safety Guardian checks safety (Rule R5 medication limits).
9. Plan Generator converts decision into recovery plan.
10. Display 6–12 hour Recovery Plan.
11. Open What-If Simulator: "What if patient walks 20% more steps?".
12. Run What-If simulation.
13. Observe simulated effects (steps, pain, swelling, sleep, recovery score).
14. Run agents on simulation copy.
15. Display simulated recommendation and mandatory disclaimer.
16. Return to live patient state (confirm live twin history untouched).
17. Inject "Recovery Deviation" scenario (pain up, inflammation up, steps down) & advance time 120 min.
18. Safety Guardian detects deviation.
19. Escalation triggered to Clinician View (Rules R1/R8 fired).
20. Display complete audit trail log in Clinician View.

---

## ⚠️ Known Limitations & Scope Disclosures

- **Synthetic Data Only**: The system operates exclusively on synthetic patient data and simulated wearable telemetry streams. It has not been validated on real human clinical trials.
- **Illustrative Prototype Scoring**: Recovery Score (0–100) and priority routing scores are illustrative prototype metrics based on heuristic formulas (`thresholds.yaml`), not clinically validated predictions or medical probabilities.
- **What-If Simulation Scope**: What-If predictions use a configurable coefficient effect model. Results are illustrative simulations, not clinical outcome predictions.
- **Non-Autonomous Medical Decisions**: The system does not diagnose, prescribe, start, stop, or adjust medication dosages. Rule R5 strictly converts any medication-related proposal into a recommendation for clinical review by a licensed healthcare professional.
- **Extension Status (H1–H4)**: Approved extensions (simulated screening flags, synthetic cohort evaluation, read-only 3D body twin) live inside existing screens as additive components without altering the core 7-agent architecture or frozen contract schemas.

---

## 📋 Honest-Labeling & Safety Positioning

> **Safety Positioning Statement**: RECOVERY-SWARM is a clinical decision-support and recovery-optimization prototype. It is **not** an autonomous doctor. It analyzes synthetic data, detects trends, simulates scenarios, explains its reasoning, flags risks, and escalates concerning situations. Medication changes, diagnosis, and critical clinical decisions remain strictly under the oversight of qualified healthcare professionals.

- **Recovery Score**: *Illustrative prototype metric (0–100), not a clinically validated probability.*
- **What-If Simulation**: *Illustrative simulation based on synthetic data and prototype assumptions.*
- **Screening Flags**: *Pattern flags for clinician review; not a diagnosis.*
