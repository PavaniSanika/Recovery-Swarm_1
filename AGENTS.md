# AGENTS.md: rules for the coding agent (RECOVERY-SWARM)

You are helping build a **24-48 hour hackathon prototype** called RECOVERY-SWARM: a self-organizing multi-agent system around a Physiological Digital Twin for post-surgical recovery. It uses **synthetic data only**.

## Read first
1. `docs/SPEC.md`: what to build and how it behaves.
2. `docs/CONTRACTS.md`: frozen schemas, formulas, thresholds, DB, API and golden test vectors.
If they disagree, `CONTRACTS.md` wins for data shapes, formulas and thresholds; `SPEC.md` wins for behaviour and UI.
If something is unclear or missing, **ask a human. Do not invent architecture.**

## Stack (fixed, do not change)
- Backend: Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2 + **SQLite by default**, pytest, NumPy/Pandas.
- AI orchestration: **LangGraph** only. One LLM provider, structured JSON output.
- Frontend: React + Vite + **TypeScript (strict mode)** + Tailwind CSS + Recharts (React Flow optional). Extensions add `three` + `@react-three/fiber` + `drei` (3D body) and dev-only `vitest`. Files are `.ts` / `.tsx`, never plain `.js` / `.jsx`.
- Real-time: WebSocket (FastAPI).
- Database: keep the code **database-neutral**: SQLAlchemy `JSON` columns only, no SQLite-specific or PostgreSQL-specific SQL or features. SQLite is the default for development, tests and the demo. PostgreSQL is a supported option selected only by `DATABASE_URL=postgresql+psycopg://user:pass@host/recovery` (psycopg is an optional dependency). Never hardcode a database engine.
- Do NOT add CrewAI, Docker, Kubernetes, Redis, Celery, auth systems or any other infrastructure.

## Non-negotiable rules
1. **Frozen contracts.** Never rename, remove or add fields in `TwinState`, `Proposal`, or any model in `CONTRACTS.md`. Propose changes in writing and wait for approval.
2. **One shared state.** All components read and write the Digital Twin through the Twin Engine. No parallel patient state objects.
3. **LLMs reason; deterministic rules decide safety.** The Safety Guardian is plain Python rules from `thresholds.yaml`. Never call an LLM inside it. LLM output can never override it.
4. **Structured data only between agents.** Agents return validated `Proposal` / `Stance` objects. Never parse free-form text to extract decisions. Validate with Pydantic; on failure retry, then fall back to rule-based output.
5. **No faked results.** Never hardcode demo outputs, plans, scores or debate text. Everything shown must come from the pipeline. Fixture data belongs only in `data/scenarios/` and tests.
6. **Config, not magic numbers.** Thresholds, weights, coefficients and reference curves live in `backend/thresholds.yaml`.
7. **Rule-based fallback everywhere.** Every LLM agent has a deterministic fallback. `FALLBACK_MODE=true` must run the full cycle with no network.
8. **Medication limits.** No agent may recommend, start, stop, increase, decrease or choose a medication or dose, or diagnose. Only "clinical review" is allowed. Rule R5 and a test enforce this.
9. **Workflow components are not agents.** Data Ingestion, Deviation Check, Priority Router, Plan Generator, Persistence are graph nodes. The 7 agents are: Twin Builder, Inflammation & Healing, Mobility & Pain, Medication Response, Sleep & Recovery, Risk & Safety Guardian, Negotiation Coordinator.
10. **What-if never touches the live twin.** Simulations run on a copy, with `is_simulation=true`, and write only to `simulation_runs`.
11. **Terminology.** Use "Recovery Score" (0-100, `recovery_score`). Never "Recovery Probability". Show: "Recovery Score is an illustrative prototype metric and is not a clinically validated prediction." What-if UI must always show: "Illustrative simulation only. Results are based on prototype assumptions and synthetic data and are not clinical predictions."
12. **Frontend types.** `frontend/src/types.ts` mirrors `docs/CONTRACTS.md` section 11 and is frozen like the backend models. All API and WebSocket data must use these types. No `any`, no `@ts-ignore`, no `as unknown as`; fix the type or ask a human. `npm run build` must finish with zero type errors.
13. **Scope.** Six screens only: Dashboard, Digital Twin, Agent Swarm, Recovery Plan, What-If, Clinician View. No login, signup, settings, notifications or patient management. Approved extensions (rule 15) live inside existing screens.
14. **Never present the system as a doctor.** It is decision-support. It escalates to a clinician; it does not diagnose or prescribe.
15. **Approved extensions (CONTRACTS section 12) are additive.** Screening flags, the synthetic cohort evaluation and the 3D body twin must not change the twin schema, the proposal schema, rules R1-R8 or the 7-agent definition. Screening and evaluation are workflow components, not agents. Extension types go in `types.ext.ts`; `types.ts` stays frozen. Only start extension stages (H1-H4) after the core (through Stage C2) is tagged, except the 3D body which may use mock data earlier.
16. **Honest labels.** Use exactly: "Screening flag only. Not a diagnosis. Clinician review required." / "Technical evaluation on synthetic data. Not clinical validation." / "Visualization of prototype scores. Not an anatomical or physiological simulation." Never write "diagnosed", "you have", "confirmed", "validated", or "clinically validated" about the prototype. Never build autonomous medication changes or any dose, drug, or prescription recommendation. A simulated clinician-approved medication workflow is NOT approved; do not build it unless a human approves it in writing.
17. **Evaluation integrity.** The cohort generator must be independent of the safety and screening thresholds. Never tune safety or screening thresholds to improve evaluation numbers. Report results honestly, including failures and limitations.

## How to work
- **Plan first.** Before writing code for a stage, output a short plan (files to create or change, tests to write). Wait for approval.
- **Stay in the current stage.** Do not build later stages early.
- **Test-driven.** Write pytest tests from `docs/CONTRACTS.md` section 9 (golden vectors) first or alongside code. Run them and show the output. Never claim something works without running it.
- **Small changes.** Prefer small, focused commits. Do not rewrite files you were not asked to touch. Do not reformat unrelated code.
- **LangGraph and library APIs change.** Before writing LangGraph, FastAPI or LLM SDK code, check the installed version and its current docs; do not rely on memory.
- **Be honest.** If a test fails, a requirement cannot be met, or you had to assume something, say so clearly. Do not hide failures or weaken tests to make them pass.
- **Keep it simple.** Hackathon scope. No premature abstraction, no extra features, no unnecessary dependencies.

## Commands (keep these working)
```
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q                                   # all tests
uvicorn app.main:app --reload --port 8000   # API
cd frontend && npm install && npm run dev   # UI
cd frontend && npm run build                # type-check + build, must have zero errors
FALLBACK_MODE=true pytest -q                # runs with no LLM/network
DATABASE_URL=postgresql+psycopg://user:pass@host/recovery pytest -q   # optional, run once before the demo
```

## Definition of done (every stage)
- All tests for the stage pass and output is shown.
- `FALLBACK_MODE=true` still works (from Stage C onward).
- Frontend stages: `npm run build` passes with zero TypeScript errors.
- No frozen contract changed; no hardcoded outputs; no new infrastructure.
- A short summary of what changed, what was tested and any open questions.
