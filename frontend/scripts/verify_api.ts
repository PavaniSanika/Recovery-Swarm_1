import { getTwin, postCycle, getLatestPlan, simulatorReset } from "../src/api";
import { TwinState, CycleResponse, Plan } from "../src/types";

async function verify() {
  console.log("==================================================");
  console.log("STARTING FRONTEND API VERIFICATION (REAL BACKEND, FALLBACK_MODE=true)");
  console.log("==================================================\n");

  // Step 0: Reset simulator state to clean baseline Meera
  console.log("--- 0. Resetting P001 simulator state ---");
  await simulatorReset("P001");
  console.log("Simulator reset completed.\n");

  // 1. GET /api/patients/P001/twin
  console.log("--- 1. Testing getTwin('P001') ---");
  const twin: TwinState = await getTwin("P001");
  console.log(`Patient ID:      ${twin.patient_id}`);
  console.log(`Name:            ${twin.profile.name}`);
  console.log(`Surgery:         ${twin.profile.surgery} (Day ${twin.profile.post_op_day})`);
  console.log(`Recovery Score:  ${twin.scores.recovery_score} / 100`);
  console.log(`Observations:    pain=${twin.observations.pain}, steps=${twin.observations.steps}, swelling=${twin.observations.swelling}`);
  console.log(`Trajectory:      overall=${twin.trajectory.overall}, inflammation=${twin.trajectory.inflammation}`);
  
  // Runtime assertion check
  if (!twin.patient_id || typeof twin.scores.recovery_score !== "number") {
    throw new Error("Invalid TwinState structure returned");
  }
  console.log("STATUS: TwinState interface verification PASSED.\n");

  // 2. POST /api/patients/P001/cycle
  console.log("--- 2. Testing postCycle('P001') ---");
  const cycle: CycleResponse = await postCycle("P001");
  console.log(`Cycle ID:        ${cycle.cycle_id}`);
  console.log(`Escalated:       ${cycle.escalated}`);
  console.log(`Safety Result:   ${cycle.safety.result}`);
  console.log(`Proposals Count: ${cycle.proposals.length}`);
  console.log(`Debate Messages: ${cycle.debate.length}`);
  if (cycle.proposals.length > 0) {
    const p0 = cycle.proposals[0];
    if (p0) {
      console.log(`Sample Proposal: [${p0.agent}] ${p0.action_type} (${p0.direction}) target=${p0.target_value}`);
    }
  }

  // Runtime assertion check
  if (!cycle.cycle_id || !Array.isArray(cycle.proposals) || !cycle.safety) {
    throw new Error("Invalid CycleResponse structure returned");
  }
  console.log("STATUS: CycleResponse interface verification PASSED.\n");

  // 3. GET /api/patients/P001/plan/latest
  console.log("--- 3. Testing getLatestPlan('P001') ---");
  const plan: Plan = await getLatestPlan("P001");
  console.log(`Horizon Hours:   ${plan.horizon_hours}`);
  console.log(`Safety Status:   ${plan.safety_status}`);
  console.log(`Steps Target:    ${plan.steps_target}`);
  console.log(`High Priority:   ${plan.high_priority.length} item(s)`);
  if (plan.high_priority.length > 0) {
    const hp0 = plan.high_priority[0];
    if (hp0) {
      console.log(`  * Action: ${hp0.action} (Reason: ${hp0.reason})`);
    }
  }

  // Runtime assertion check
  if (typeof plan.horizon_hours !== "number" || !Array.isArray(plan.high_priority)) {
    throw new Error("Invalid Plan structure returned");
  }
  console.log("STATUS: Plan interface verification PASSED.\n");

  console.log("==================================================");
  console.log("ALL FRONTEND VERIFICATION CHECKS COMPLETED SUCCESSFULLY");
  console.log("==================================================");
}

verify().catch((err) => {
  console.error("Verification failed:", err);
  process.exit(1);
});
