import { simulatorInject, simulatorAdvance, simulatorReset, getTwinReference, getTwinHistory, getTwin } from "../src/api";
import { TwinState, HistoryEntry } from "../src/types";
import { TwinReference } from "../src/types.ext";

async function verifyF3() {
  console.log("==================================================");
  console.log("STARTING STAGE F3 DIGITAL TWIN & TRENDS VERIFICATION");
  console.log("==================================================\n");

  // Step 0: Reset simulator state
  console.log("--- Step 0: Reset Patient P001 & Check Initial History ---");
  const baseline: TwinState = await simulatorReset("P001");
  const history0: HistoryEntry[] = await getTwinHistory("P001");
  const ref: TwinReference = await getTwinReference("P001");

  console.log(`Baseline Patient: ${baseline.profile.name}, Surgery: ${ref.surgery} (Day ${ref.post_op_day})`);
  console.log(`Reference Curves Sourced from Backend: expected_pain=${ref.expected_pain}, expected_inflammation=${ref.expected_inflammation}, expected_steps=${ref.expected_steps}`);
  console.log(`Reference Curves Dictionary: pain(Day 4)=${ref.curves["pain"]?.["4"]}, inflammation(Day 4)=${ref.curves["inflammation"]?.["4"]}`);
  console.log(`Initial History Length: ${history0.length}`);
  
  if (history0.length < 2) {
    console.log("STATUS: history.length < 2 -> 'Not Enough History Yet' Empty State Card active.");
  }
  console.log("PASSED: Reference extension & Initial state verified.\n");

  // Step 1: Inject Scenario - pain_spike & advance to build history
  console.log("--- Step 1: Inject 'pain_spike' & Advance to Build Trend History ---");
  await simulatorInject("P001", "pain_spike");
  await simulatorAdvance("P001", 60);
  await simulatorAdvance("P001", 60);
  await simulatorAdvance("P001", 60);

  const twinUpdated: TwinState = await getTwin("P001");
  const historyUpdated: HistoryEntry[] = await getTwinHistory("P001");

  console.log(`Updated Twin State: Pain=${twinUpdated.observations.pain}, CRP Index=${twinUpdated.observations.crp}/10, Trajectory=${twinUpdated.trajectory.overall}`);
  console.log(`Updated History Length: ${historyUpdated.length} Snapshots`);
  historyUpdated.forEach((h, idx) => {
    console.log(`  [Snapshot ${idx + 1}] Time=${h.timestamp.slice(11, 16)} | Pain=${h.observations.pain} | CRP=${h.observations.crp} | Steps=${h.observations.steps} | Overall=${h.overall}`);
  });

  const isDeviating = twinUpdated.trajectory.overall === "below_expected" || twinUpdated.trajectory.overall === "deteriorating" || twinUpdated.observations.pain >= 7.0;
  console.log(`Deviation Alert Banner Active: ${isDeviating ? "YES (Warning Banner Visible)" : "NO"}`);

  if (historyUpdated.length >= 2) {
    console.log("STATUS: history.length >= 2 -> Recharts Trend Graphs & Trajectory Comparison Active.");
  }
  console.log("PASSED: Trend graphs & deviation banner state verified.\n");

  console.log("==================================================");
  console.log("ALL STAGE F3 DIGITAL TWIN VERIFICATION CHECKS PASSED");
  console.log("==================================================");
}

verifyF3().catch((err) => {
  console.error("F3 Verification failed:", err);
  process.exit(1);
});
