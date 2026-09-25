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
