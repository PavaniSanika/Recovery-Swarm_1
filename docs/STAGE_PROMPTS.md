# RECOVERY-SWARM: Build Guide and Stage Prompts (for Antigravity)

Use this file to build the system stage by stage. Give the agent one stage at a time. Do not move on until the current stage passes its checks.

---

## 0. One-time setup (before the first prompt)

1. Create a Git repo named `recovery-swarm` and copy this bundle into it:
```
recovery-swarm/
  AGENTS.md
  docs/
    SPEC.md
    CONTRACTS.md
    STAGE_PROMPTS.md      (this file)
    img/                  (diagrams used by SPEC.md)
```
2. Install Python 3.11+, Node 20+ (with npm) and Git. Create `backend/.env` from this template:
```
LLM_API_KEY=your_key_here
LLM_MODEL=your_model_name
DATABASE_URL=sqlite:///./recovery.db
# Optional PostgreSQL (one-line switch):
# DATABASE_URL=postgresql+psycopg://user:pass@host/recovery
FALLBACK_MODE=false
TEMPERATURE=0.1
```
Add `.env` and `*.db` to `.gitignore`.
3. **Database:** nothing to install. SQLite is the default. (Optional: if you want to try PostgreSQL later, create a database and put the `postgresql+psycopg://...` line in `.env`; the code must work unchanged.)
4. Open the repo folder in Antigravity. Make sure it has AGENTS.md as a workspace rule (or paste its contents into the rules setting if your version has one).
5. Choose ONE LLM provider for the app itself (the model that runs inside RECOVERY-SWARM). This is separate from the model Antigravity uses to write code.
6. **Human task, do this yourselves:** read `docs/CONTRACTS.md` once. It is short, and you own it. If you want a change, edit it before Stage A.
7. Commit: `git commit -m "chore: spec and contracts"`.

## How to run each stage

1. Paste the stage prompt. The agent will reply with a **plan**. Read it. Check it stays inside the stage and follows AGENTS.md. Approve or correct it.
2. Let it implement. Ask it to run the tests and paste the output.
3. Run the **human checks** at the end of the stage yourself (do not only trust the agent's summary).
4. If OK: `git commit -m "stage X: done"` and tag `git tag stage-X`. If not, use the fix prompts in section 9.
5. Start a **new chat/session** for each stage and begin with "Read AGENTS.md, docs/SPEC.md and docs/CONTRACTS.md" (the stage prompts already do this). It avoids old context confusing the agent.

## Team of 4 (parallel work)

- **Member 4** starts Stage A. **Member 2** starts Stage B after A's models exist. **Member 1** starts Stage C after B's safety and twin engine exist (they can stub them from CONTRACTS.md until then).
- **Member 3** can start Stage F early with the TypeScript project, `types.ts` and a **mock API** (see F0 below) using the frozen formats, then switch to the real API after Stage E.
- Rule: each person works on their own folders/branches, merges to `main` often, and never edits contract files without telling everyone.

---

## Stage A: Repo, contracts as code, synthetic data, simulator (Phases 1-2)

**Paste this:**

```
Read AGENTS.md, docs/SPEC.md and docs/CONTRACTS.md fully before doing anything.

Task: Stage A only. Do NOT build later stages.

Goal: create the repo skeleton, turn the frozen contracts into code, and build the
synthetic data and simulator.

Do:
1. Create the folder structure from SPEC section 20 (backend/app/..., frontend/ placeholder,
   data/scenarios/, docs/). Add requirements.txt (SPEC 18.4), .env.example, .gitignore, README.md.
2. Implement backend/app/models/schemas.py exactly as CONTRACTS section 2 (extra="forbid").
3. Implement backend/app/config.py that loads backend/thresholds.yaml (CONTRACTS section 3)
   and .env (LLM_*, DATABASE_URL, FALLBACK_MODE, TEMPERATURE). Create thresholds.yaml exactly as in CONTRACTS section 3.
4. Create the synthetic patient P001 (Meera Sharma, canonical twin) and the six scenario files
   in data/scenarios/ (CONTRACTS section 8). Use fixed seeds.
5. Implement backend/app/simulator.py: load a scenario, advance simulated time (minutes), and
   yield deterministic ObservationIn objects. Same scenario + seed must give identical output.
6. Write pytest tests: the canonical twin JSON validates against TwinState; extra fields are
   rejected; each scenario file loads and produces the expected number of steps; the simulator
   is deterministic (run twice, compare).

First output a short plan (files to create, tests to write) and WAIT for my approval.
Then implement, run `pytest -q`, and show the results.
```

**Human checks:** `pytest -q` passes. Open `models/schemas.py` and compare fields with CONTRACTS by eye. Run the simulator twice and confirm identical output. Confirm no extra frameworks were added.

---

## Stage B: Twin Engine, Deviation Check, Safety Guardian (Phases 3-4)

**Paste this:**

```
Read AGENTS.md, docs/SPEC.md and docs/CONTRACTS.md fully before doing anything.

Task: Stage B only (Digital Twin engine + deterministic safety). No agents, no LLM yet.

Do:
1. backend/app/twin/engine.py: implement the formulas in CONTRACTS section 4 (inflammation_score,
   mobility_capacity, sleep_quality, recovery_score, complication_risk, medication_effectiveness
   rules) and the trajectory labels. All numbers come from thresholds.yaml.
2. backend/app/twin/reference.py: expected curves and step targets from thresholds.yaml.
3. TwinEngine.update(twin, observation_in) -> new TwinState: validate, compute scores and
   trajectory, append the previous state to history (compact HistoryEntry), and compute
   trends from history on demand (helper, not a stored field). Missing values are marked,
   never invented.
4. backend/app/workflow/deviation.py (workflow component, rule-based): the three deviation
   rules from CONTRACTS section 3 (deviation_check) and a red-flag helper.
5. backend/app/agents/safety.py: deterministic Safety Guardian implementing R1-R8 exactly as in
   CONTRACTS section 5.3, with evaluate() and evaluate_proposal(), strictest-outcome-wins, and
   the retry limit. NO LLM calls anywhere in this file.
6. Tests from CONTRACTS section 9: 9.1 (Meera scores and trajectory), 9.2, 9.3 (all safety cases),
   plus edge cases for each rule R1-R8 (trigger and non-trigger) and history/trend behaviour.

First output a short plan and WAIT for my approval. Then implement, run `pytest -q`, show output.
```

**Human checks:** Golden vectors pass. Manually change one input (for example pain to 8) and confirm the right rule fires. `grep -ri "llm\|anthropic\|openai" backend/app/agents/safety.py` shows nothing.

---

## Stage C: Rule-based swarm: agents, router, debate, coordinator, LangGraph (Phases 5-7, no LLM)

**Paste this:**

```
Read AGENTS.md, docs/SPEC.md and docs/CONTRACTS.md fully before doing anything.

Task: Stage C only. Build the whole swarm using RULE-BASED agents (no LLM yet). The full
cycle must run offline.

First, check the installed LangGraph version and read its current documentation before writing
graph code.

Do:
1. backend/app/agents/{mobility,inflammation,medication,sleep}.py: each has a rule_based_*(twin)
   function returning a valid Proposal (CONTRACTS section 2), plus a common interface so an LLM
   version can be added later. The medication agent may only return action_type pain_review,
   monitoring or escalate and must never mention doses (CONTRACTS 5.4).
2. backend/app/workflow/router.py (Priority Router, a workflow component): formulas in
   CONTRACTS 5.1, roles lead/supporting/waiting. Test that Meera baseline gives the lead set
   {inflammation, sleep, mobility} with values within +/-0.05 of the CONTRACTS numbers.
3. Debate: rule-based stance function returning Stance objects (support/oppose/revise with
   revised_confidence and a short message), coalition formation, and DebateMessage log with
   the UI statuses (Analyzing, Waiting, Supporting, Challenging, Revising, Vetoing, Approved).
   Meera's mobility agent should propose 2200, then revise to about 1900 after the stance round.
4. backend/app/agents/coordinator.py (Negotiation Coordinator, no LLM): weighted scoring and
   conservative-first conflict rules exactly as CONTRACTS 5.2, producing a draft plan.
5. backend/app/workflow/planner.py (Plan Generator, workflow component): template-based Plan
   from the approved decision only (no invented actions).
6. backend/app/graph.py: LangGraph graph following SPEC 15.2 and CONTRACTS: ingest -> twin_builder
   -> deviation_check -> priority_router -> (4 specialists in parallel) -> debate_round ->
   coordinator -> safety_guardian -> (allow/modify -> plan_generator | reject -> retry coordinator
   max 2 | escalate -> persist) -> persist. Include a red-flag escalation path from
   deviation_check. Use SwarmState from SPEC 15.2 (including is_simulation). The persist node can
   be a stub for now.
7. A function run_cycle(twin, fallback=True) -> CycleResponse.
8. Tests: full cycle on Meera baseline produces plan with steps_target around 1900, safety
   result "allow", no rules triggered; pain_spike scenario escalates; recovery_deviation
   escalates; poor_sleep makes sleep the top-priority agent; the cycle is deterministic.

First output a short plan and WAIT for my approval. Then implement, run `pytest -q`, show output.
```

**Human checks:** Run `run_cycle` on each of the six scenarios and read the printed debate. Does it make sense? Does the plan differ between scenarios? Is any text hardcoded per scenario (it must not be)?

---

## Stage D: Add LLM reasoning with structured output and fallbacks (Phase 5, steps 17-18)

**Paste this:**

```
Read AGENTS.md, docs/SPEC.md and docs/CONTRACTS.md fully before doing anything.

Task: Stage D only. Add LLM reasoning to the swarm on top of the working rule-based version.

First, check the installed SDK version for the chosen LLM provider and read its current docs
for structured (JSON) output. Use the provider configured in .env (LLM_API_KEY, LLM_MODEL).

Do:
1. backend/app/agents/base.py: one LLM client wrapper with temperature, max_tokens, timeout and
   retries from thresholds.yaml (llm section); structured output validated with Pydantic;
   retry on invalid output, then fall back. Never crash the cycle because of an LLM error.
2. LLM versions of the four specialist agents: a system prompt per agent (specialty, limits,
   "use only facts from the twin", "list evidence", "prefer gradual changes of 10% or less",
   "return JSON matching Proposal only"), input limited to the agent's twin slice, output
   validated as Proposal. The medication prompt must forbid dosage and medication changes and
   allow only clinical-review style outputs.
3. LLM versions of the stance round (Stance objects, one per other proposal) and of the Plan
   Generator wording (the LLM may only reword and explain actions already in the approved
   decision; the code must verify the plan contains no new actions, else use the template).
4. Keep the Coordinator, Priority Router and Safety Guardian deterministic (no LLM).
5. FALLBACK_MODE=true and per-call fallback both use the Stage C rule-based path.
6. Optional response cache for scripted scenarios (keyed by scenario + step + agent) so demos
   can run without the network.
7. Tests (mock the LLM; do not call the real API in tests): valid JSON accepted; invalid JSON
   triggers retry then fallback; a medication proposal containing a dose change is blocked by
   R5; Safety Guardian result is unchanged by anything the LLM says; full cycle works with
   FALLBACK_MODE=true and with a mocked LLM.
8. One manual script scripts/try_llm.py that runs Meera's baseline cycle with the real LLM and
   prints proposals, stances and the plan.

First output a short plan and WAIT for my approval. Then implement, run `pytest -q`, show output.
```

**Human checks:** Run `scripts/try_llm.py` yourself. Do the proposals cite real twin values in `evidence`? Turn off the network or set a wrong key: does the cycle still finish through fallback? Try to make the medication agent output a dose: does R5 block it?

---

## Stage E: Persistence, API, WebSocket, What-If, Demo Mode (Phases 7-8, 10)

**Paste this:**

```
Read AGENTS.md, docs/SPEC.md and docs/CONTRACTS.md fully before doing anything.

Task: Stage E only. Persistence, API, real-time, What-If and Demo Mode. No frontend yet.

Do:
1. backend/app/db.py + models: the 9 tables in CONTRACTS section 6 (SQLAlchemy 2, JSON columns),
   created with create_all at startup. Keep the code database-neutral: no SQLite-specific or
   PostgreSQL-specific features; the engine comes only from DATABASE_URL (default SQLite).
   Tests run on SQLite (temporary DB per test session). /simulator/reset must delete P001's
   saved states, decisions, plans and simulation runs, then restore the baseline.
2. backend/app/main.py: FastAPI app with every endpoint in CONTRACTS section 7, using the
   frozen request/response models and the error format. CORS enabled for the Vite dev server.
3. WebSocket /ws/patients/{id}: push twin_update, agent_status, debate_message, safety, plan
   and escalation messages while a cycle runs (message formats in CONTRACTS section 7).
4. backend/app/whatif.py: implement the flow in SPEC section 10 and CONTRACTS 9.4: deep-copy
   the twin, apply changes (steps_pct, steps, pain, sleep_hours, swelling), apply the effect
   model from thresholds.yaml, recompute derived scores, run the same graph with
   is_simulation=True, compare with the current state, add the exact disclaimer. Persist only
   to simulation_runs. The live twin must remain unchanged.
5. Demo Mode: /simulator/inject, /simulator/advance, /simulator/reset per CONTRACTS section 7
   using the scenario files (deterministic, seeded). Reset returns to the Meera Day 4 baseline.
6. Audit endpoint returns the safety_events and decisions trail for the Clinician View.
7. Tests with FastAPI TestClient: each endpoint; the cycle response validates as CycleResponse;
   what-if for +20% steps gives target 1980 with R4 and leaves twin_states row count unchanged;
   pain_spike scenario ends in escalation with a safety_events row for R1; reset restores
   the baseline; WebSocket sends messages in order during a cycle.

First output a short plan and WAIT for my approval. Then implement, run `pytest -q`, show output.
Finally give me curl examples for: inject pain_spike, run a cycle, run a what-if, fetch the audit.
```

**Human checks:** Start the server and open `http://localhost:8000/docs`. Run the curl examples. Inject a scenario, run a cycle, and inspect the rows in the SQLite file (`sqlite3 recovery.db`, for example `select cycle_id, safety_result from decisions;`). Confirm what-if did not change `twin_states`.

---

## Stage F: Frontend, one screen at a time (Phase 9)

### F0 (Member 3, can start after Stage A): TypeScript project, types and mock API

```
Read AGENTS.md, docs/SPEC.md and docs/CONTRACTS.md (especially section 7 and section 11).
Task: Stage F0 only.
1. Create frontend/ with Vite + React + TypeScript (strict mode) + Tailwind CSS + Recharts.
   Files must be .ts / .tsx.
2. Create frontend/src/types.ts exactly as in CONTRACTS section 11 (no changes, no any).
3. Create a small typed mock API layer (frontend/src/mock/) returning realistic data that
   satisfies those types for: Meera baseline, each scenario, a cycle response, a what-if
   response, an audit list. Switching mock vs real API must be one flag in frontend/src/api.ts.
4. Write api.ts (typed functions for every endpoint in CONTRACTS section 7) and ws.ts (typed
   WebSocket client that parses into WsMessage with an exhaustive switch).
5. `npm run build` must pass with zero type errors. Do not use any, @ts-ignore or
   `as unknown as`.
Plan first and wait for approval. Then implement, run `npm run build`, and show the output.
```

### F1: Layout, navigation and Demo Mode bar

```
Read AGENTS.md, docs/SPEC.md (especially section 17) and docs/CONTRACTS.md (sections 7 and 11).
Task: Stage F1 only. Using the existing TypeScript project and types.ts, create the app shell:
sidebar "RECOVERY-SWARM" with exactly six items (Dashboard, Digital Twin, Agent Swarm,
Recovery Plan, What-If, Clinician View), routing, and a Demo Mode control bar (Stable Recovery,
Poor Sleep, Pain Spike, Increased Inflammation, Reduced Mobility, Recovery Deviation,
Advance 1 Hour, Optimize Recovery, Run What-If, Reset) that calls the typed api.ts functions.
No login, signup or settings screens. All components are .tsx with typed props.
`npm run build` must have zero type errors. Plan first and wait for approval. Run the dev
server and describe what I should see.
```

### F2 to F6: one prompt per screen (use this template)

```
Read AGENTS.md, docs/SPEC.md (section 17) and docs/CONTRACTS.md.
Task: build ONLY the screen "<SCREEN>" (SPEC 17.x) as a typed .tsx page using the types in types.ts. Use the real API (or the mock flag).
Show exactly the data listed for that screen, use the terms "Recovery Score: 68 / 100" and the
required disclaimers, and update live over the WebSocket where applicable.
Do not change other screens. Do not hardcode any values: everything comes from the API.
No any, no @ts-ignore. `npm run build` must pass with zero type errors.
Plan first, wait for approval, then implement and tell me how to verify it.
```

Screens, in this order and what each must show:

| Step | Screen | Must show |
|---|---|---|
| F2 | Dashboard | Meera Day 4, pain, sleep, steps, inflammation, swelling, **Recovery Score X / 100** with the score note, status badge, latest plan summary |
| F3 | Digital Twin | Pain, inflammation, mobility and sleep trend charts (Recharts) from `/twin/history`; expected vs actual trajectory; recovery-deviation banner when flagged |
| F4 | Agent Swarm | 7 agent cards (status, confidence, recommendation, evidence, role lead/supporting/waiting) and a live debate log below; statuses Analyzing, Waiting, Supporting, Challenging, Revising, Vetoing, Approved |
| F5 | Recovery Plan | Next 6-12 hour plan, high / medium priority, monitoring, reasons, safety status, next reassessment, expected score change; example format in SPEC 17.4 |
| F6a | What-If | Input (e.g. "walk 20% more"), current vs simulated pain / swelling / sleep / mobility, simulated plan, exact disclaimer |
| F6b | Clinician View | Patient summary, twin, trajectory, recent changes, triggered deviation, agent recommendations, safety rule triggered, system recommendation ("ESCALATE TO CLINICIAN REVIEW"), audit trail; wording says it recommends review and does not diagnose |

**Human checks:** Run `npm run build` yourself (zero type errors). Search the frontend for `any`, `@ts-ignore` and `.js`/`.jsx` files (there should be none). Click through the full 20-step demo in SPEC 21.2 using the UI only. Confirm nothing is hardcoded: inject a different scenario and see the numbers, charts and debate change.

---

## Stage G: Testing, polish and demo rehearsal (Phases 11-12)

**Paste this:**

```
Read AGENTS.md, docs/SPEC.md and docs/CONTRACTS.md fully before doing anything.

Task: Stage G only. Test, harden and prepare for the demo. Do not add features.

Do:
1. Add the missing end-to-end tests listed in SPEC 21.1: normal recovery, poor sleep, pain
   increase, inflammation increase, mobility decrease, safety veto, escalation, what-if,
   medication limit, LLM failure. Run the whole suite with and without FALLBACK_MODE.
2. Write scripts/demo_check.py that runs the 20-step demo flow from SPEC 21.2 against the API
   and prints PASS/FAIL per step (reset first). It must pass three runs in a row.
3. Audit the codebase against AGENTS.md: search for hardcoded outputs, LLM calls inside the
   Safety Guardian, the words "Recovery Probability" or "probability" used as a score name,
   extra screens, extra infrastructure, any changed contract fields, and violations of AGENTS.md rules 15 to 17 (extension labels, forbidden words such as "diagnosed" or "clinically validated", evaluation integrity). Report findings; fix
   only real violations.
4. Run `npm run build` and fix all TypeScript errors properly (no any, no @ts-ignore). Make sure the UI and API never crash on an LLM error or missing data (show fallback or
   "data needed" messages).
5. Add a README with setup, run commands, the demo script and known limitations, using the
   scope text from SPEC section 1 (synthetic data, illustrative scoring, not clinical).
6. Run the full test suite once against PostgreSQL by setting DATABASE_URL to a postgresql+psycopg URL (optional, if a PostgreSQL server is available) and report any failures caused by database-specific behaviour.
7. Print a list of screenshots and outputs to capture for the PPT (SPEC 19.3).

First output a short plan and WAIT for my approval. Then implement and show all results.
```

**Pitch line for the database question:** "SQLite for the prototype, PostgreSQL-ready through a single config change."

**Human checks:** Do the full demo yourselves three times, using a different person as presenter each time. Time it. Prepare judge Q&A.

---

---

## Extensions (after the core): Stages H1 to H4

Approved extensions from SPEC Appendix A and CONTRACTS section 12: **screening flags**, **synthetic cohort evaluation**, **3D body twin**. Start H1, H2 and H4 only after Stage C2 is tagged (H2 also needs H1). H3 can start once F0 exists (it uses mock data). Do NOT start the simulated medication-order workflow; it is not approved. Run Stage G (final testing and rehearsal) after the extensions, so it also covers them.

Time estimates: H1 4 to 6 h, H2 6 to 8 h, H3 8 to 12 h (5 to 6 h with simple shapes), H4 3 to 4 h.
Owners: H1 Member 2, H2 Member 4, H3 Member 3, H4 Members 3 and 4.

### Stage H1: Screening flags (backend)

```
Read AGENTS.md, docs/SPEC.md (Appendix A.2) and docs/CONTRACTS.md (section 12.1) fully.
Task: Stage H1 only. Implement screening flags as a deterministic workflow component (not an
agent). I am on Windows. Do not modify Stage A/B/C files except additive changes described below.

Do:
1. Add the `screening:` section to backend/thresholds.yaml exactly as in CONTRACTS 12.1 and tell
   me exactly what you added. Do not change other sections.
2. Add ScreeningFlag and ScreeningResult to backend/app/models/schemas.py (or a new
   backend/app/models/extensions.py) exactly as in CONTRACTS 12.1.
3. backend/app/workflow/screening.py: screen(twin, flags, history) -> ScreeningResult, rules
   SF1-SF5, one flag per id with the highest severity, ordered SF1..SF5, thresholds only from
   thresholds.yaml, wording rules from CONTRACTS (no "diagnosed", "you have", "confirmed",
   no treatment instructions), fixed SCREENING_DISCLAIMER on every flag and the result.
4. Add GET /api/patients/{id}/screening only if the Stage E API already exists; otherwise expose
   a function the API can call later and say so.
5. Tests: all golden vectors S1-S8 from CONTRACTS 12.1; a consistency test that every state
   producing an urgent flag also makes SafetyGuardian.evaluate return "escalate"; a test that
   all six scenario files run through TwinEngine.update + screen without errors and that
   Meera baseline gives no flags; a test that no flag text contains forbidden words.

First output a short plan and WAIT for my approval. Then implement, run pytest -q, show output.
```

**Human checks:** Run screening on each scenario and read the flags. Do they cite real values in `evidence`? Search flag text for "diagnos", "you have", "confirmed": there should be none except in the disclaimer ("Not a diagnosis").

### Stage H2: Synthetic cohort evaluation (backend)

```
Read AGENTS.md, docs/SPEC.md (Appendix A.3) and docs/CONTRACTS.md (section 12.2) fully.
Task: Stage H2 only. Build the synthetic cohort generator, the evaluation runner and the report.
This is a TECHNICAL evaluation on synthetic data, not clinical validation. I am on Windows.

Do:
1. Add the `evaluation:` section to backend/thresholds.yaml exactly as in CONTRACTS 12.2 and
   tell me exactly what you added.
2. backend/app/evaluation/generator.py: seeded (numpy default_rng) cohort generator as specified.
   It must NOT read or import the safety_rules or screening thresholds; it has its own constants.
3. backend/app/evaluation/runner.py: run every patient's readings through TwinEngine.update,
   deviation check, screening and the SafetyGuardian on every reading, and the full swarm cycle
   (fallback mode, no LLM) every full_cycle_every_n_readings readings. Compute all metrics and
   safety invariants exactly as defined in CONTRACTS 12.2, build EvaluationReport (with
   limitations and EVAL_DISCLAIMER) and report_hash.
4. scripts/run_evaluation.py printing a readable summary. Add the evaluation_runs table and the
   endpoints POST /api/evaluation/run and GET /api/evaluation/latest if the Stage E API exists.
5. Tests from CONTRACTS 12.2: deterministic hash, different seed changes the hash, safety
   invariants all true, report validates, disclaimer and limitations present, runtime under
   max_runtime_s for 200 patients, smoke expectations.
6. Never tune safety or screening thresholds to improve results. If a smoke expectation fails,
   report it and tell me; adjust only the generator if it is unrealistic, and explain why.

First output a short plan and WAIT for my approval. Then implement, run pytest -q, show output.
```

**Human checks:** Run `scripts/run_evaluation.py` twice: same numbers. Read the report. Are the results plausible and not suspiciously perfect? Are the limitations printed?

### Stage H3: 3D body twin (frontend)

```
Read AGENTS.md, docs/SPEC.md (Appendix A.4) and docs/CONTRACTS.md (section 12.3) fully.
Task: Stage H3 only. Build the read-only 3D body twin inside the Digital Twin screen.
It is a visualization of prototype scores, not an anatomical or physiological simulation.

Before adding dependencies, check the installed React version and install the matching
versions of three, @react-three/fiber and @react-three/drei (and @types/three). Add vitest as a
dev dependency only for the mapping tests.

Do:
1. frontend/src/types.ext.ts exactly as in CONTRACTS 12.3 (do not edit types.ts).
2. frontend/src/components/body/bodyMapping.ts: pure function twinToBodyParams(twin, flags) using
   the exact formulas in CONTRACTS 12.3. Unit tests (vitest) with the Meera golden values and
   edge cases (clamping, walk_speed below 0.1 -> 0, each outline colour, each marker region).
3. BodyTwin3D.tsx: a body built from simple shapes (sphere, capsules), operated right knee
   scaled by knee_scale, red pulse at the site using pain_hz and pain_intensity, warm heat tint,
   walking animation using walk_speed, outline colour, markers for screening flags, and a legend
   showing the real values (for example "Swelling 6.0: knee +36%"). Always show BODY_DISCLAIMER.
4. A "Simple view" toggle and BodyFallback2D.tsx (SVG body with the same overlays), used
   automatically if WebGL is unavailable.
5. What-If ghost body: when a simulated twin is available, render a second body at 45% opacity.
6. Performance: limit pixel ratio, simple materials, no post-processing; target 30+ fps on a
   laptop. If the 3D panel is not working after a reasonable effort, keep only the Simple view
   and tell me.
7. `npm run build` must pass with zero type errors; no any, no @ts-ignore. Use only mock or API
   data through the existing typed functions; do not hardcode values.

First output a short plan and WAIT for my approval. Then implement, run the tests and
`npm run build`, and show the output.
```

**Human checks:** Click each Demo Mode scenario and watch the body change (swelling, pulse, outline, walking). Toggle Simple view. Open the What-If screen and confirm the ghost body appears. Run `npm run build`.

### Stage H4: Wiring and demo segment (frontend + backend)

```
Read AGENTS.md, docs/SPEC.md (Appendix A and Section 21.3) and docs/CONTRACTS.md (section 12).
Task: Stage H4 only. Wire the finished extensions into the existing six screens; add no new
screens.

Do:
1. Clinician View: a "Screening flags" list (title, severity, evidence, recommendation, the
   SCREENING_DISCLAIMER) fed by GET /screening, and an "Evaluation" panel: metric cards, confusion
   matrix, per-group table, safety invariants, limitations, EVAL_DISCLAIMER, and a "Run
   evaluation" button calling POST /evaluation/run (show a loading state).
2. Dashboard: a small badge showing the highest screening severity (none / review / urgent),
   with the same wording rules (never "diagnosis").
3. Digital Twin: pass the screening flags to the 3D body markers.
4. Add a demo script scripts/demo_extensions.py (or extend demo_check.py) that runs the 4-step
   extension segment in SPEC 21.3 against the API and prints PASS/FAIL per step.
5. `npm run build` zero errors; all backend tests pass; both run in FALLBACK_MODE=true.

First output a short plan and WAIT for my approval. Then implement and show all results.
```

**Human checks:** Do the 2-minute extension demo segment three times. Confirm every screening view shows the disclaimer and the evaluation panel shows "Technical evaluation on synthetic data. Not clinical validation."

---

## 9. Helper prompts (use when things go wrong)

**A test fails or the agent seems stuck:**

```
Do not change the tests or the contracts to make this pass. First explain why the test fails
(quote the failing assertion and the relevant code). Then propose the smallest fix in the
implementation. Wait for my approval before editing.
```

**Suspect faked or hardcoded results:**

```
Audit for hardcoded outputs. For each scenario, show me where the plan text, scores and debate
messages come from in the code. Then change one input value in a scenario file and re-run the
cycle to prove the outputs change. List any place where text is hardcoded per scenario.
```

**Agent drifted from the spec:**

```
Compare what you built against docs/SPEC.md section <N> and docs/CONTRACTS.md section <M>.
List every difference (missing, extra, or renamed). Do not fix anything yet.
```

**Agent wants to change a frozen contract:**

```
Write a one-paragraph change request: what field, why it is needed, what else it affects.
Do not edit any contract file. I will decide.
```

**Resume in a new session:**

```
Read AGENTS.md, docs/SPEC.md and docs/CONTRACTS.md. We finished stages <A..X> (git tag stage-X).
Run `pytest -q` and summarize the current state of the repo in 10 lines. Do not change code yet.
Today's task: Stage <Y> (paste stage prompt).
```

---

## 10. Expectations and fallback plan

- Expect to debug by hand: LangGraph wiring, LLM JSON quirks, WebSocket timing and frontend styling.
- If time runs short: keep the rule-based path (`FALLBACK_MODE=true`). It still demonstrates the whole architecture, and you can use the LLM for only the four specialists.
- Freeze features at about 75% of the time. Use the rest for Stage G and rehearsal.
- Capture screenshots for the PPT at the end of every stage, not only at the end.
