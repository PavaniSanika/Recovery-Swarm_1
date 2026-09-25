export interface SimulatorStatus {
  scenario_name: string | null;
  step_index: number;
  total_steps: number;
  minute_offset: number;
  max_minute_offset: number;
}

export interface TwinReference {
  surgery: string;
  post_op_day: number;
  expected_pain: number;
  expected_inflammation: number;
  expected_steps: number;
  curves: Record<string, Record<string, number>>;
}

export type Severity = "info" | "review" | "urgent";
export type FlagId = "SF1" | "SF2" | "SF3" | "SF4" | "SF5";

export interface ScreeningFlag {
  flag_id: FlagId;
  title: string;
  severity: Severity;
  evidence: string[];
  recommendation: string;
  disclaimer: string;
}

export interface ScreeningResult {
  patient_id: string;
  flags: ScreeningFlag[];
  disclaimer: string;
}

export interface EvaluationRunRequest {
  cohort_size: number;
  seed: number;
}

export interface Confusion {
  tp: number;
  fn: number;
  fp: number;
  tn: number;
}

export interface GroupMetrics {
  group: string;
  n: number;
  detected: number;
  sensitivity: number;
  ci_low: number;
  ci_high: number;
  median_hours_to_detection: number | null;
  flag_type_match_rate: number | null;
}

export interface SafetyInvariants {
  max_step_increase_ok: boolean;
  no_forbidden_medication_terms: boolean;
  urgent_implies_escalation: boolean;
  deterministic_rerun: boolean;
  violations: string[];
}

export interface EvaluationReport {
  run_id: string;
  created_at: string;
  seed: number;
  cohort_size: number;
  mode: "fallback";
  sensitivity_overall: number;
  sensitivity_ci: [number, number];
  false_alarm_rate_strict: number;
  false_alarm_rate_lenient: number;
  median_hours_to_detection: number | null;
  recovery_score_auc: number;
  confusion: Confusion;
  per_group: GroupMetrics[];
  safety: SafetyInvariants;
  report_hash: string;
  limitations: string[];
  disclaimer: string;
}

export type BodyRegion = "knee" | "calf" | "chest" | "legs";
export type OutlineColor = "green" | "yellow" | "orange" | "red";

export interface BodyMarker {
  region: BodyRegion;
  flag_id: FlagId;
  severity: Severity;
}

export interface BodyParams {
  knee_scale: number;
  pain_hz: number;
  pain_intensity: number;
  heat: number;
  walk_speed: number;
  outline: OutlineColor;
  markers: BodyMarker[];
  site: "knee";
  operated_side: "left" | "right";
}

export const BODY_DISCLAIMER =
  "Visualization of prototype scores. Not an anatomical or physiological simulation.";
