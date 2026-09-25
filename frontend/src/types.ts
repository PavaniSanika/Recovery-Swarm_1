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
