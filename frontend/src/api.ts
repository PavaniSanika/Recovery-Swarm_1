import {
  AuditEntry,
  CycleResponse,
  HistoryEntry,
  ObservationIn,
  Plan,
  Proposal,
  RuleHit,
  ScenarioName,
  Stance,
  TwinState,
  WhatIfRequest,
  WhatIfResponse,
} from "./types";
import { SimulatorStatus, TwinReference, ScreeningResult, EvaluationReport } from "./types.ext";

const getApiBaseUrl = (): string => {
  let envUrl: string | undefined = undefined;
  try {
    if (typeof import.meta !== "undefined" && import.meta.env && import.meta.env.VITE_API_BASE_URL) {
      envUrl = import.meta.env.VITE_API_BASE_URL as string;
    }
  } catch {
    // Ignore in non-vite execution environments
  }
  if (envUrl && typeof envUrl === "string" && envUrl.trim() !== "") {
    return envUrl.trim().replace(/\/+$/, "");
  }
  return "http://localhost:8000";
};

const API_BASE = getApiBaseUrl();

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorMsg = `HTTP Error ${res.status}: ${res.statusText}`;
    try {
      const errData = (await res.json()) as { error?: { message?: string } };
      if (errData.error?.message) {
        errorMsg = errData.error.message;
      }
    } catch {
      // Ignore JSON parse error if body is empty or non-JSON
    }
    throw new Error(errorMsg);
  }
  return (await res.json()) as T;
}

export async function getTwin(patientId: string): Promise<TwinState> {
  const res = await fetch(`${API_BASE}/api/patients/${encodeURIComponent(patientId)}/twin`);
  return handleResponse<TwinState>(res);
}

export async function getTwinHistory(patientId: string): Promise<HistoryEntry[]> {
  const res = await fetch(`${API_BASE}/api/patients/${encodeURIComponent(patientId)}/twin/history`);
  return handleResponse<HistoryEntry[]>(res);
}

export async function postObservations(patientId: string, obs: ObservationIn): Promise<TwinState> {
  const res = await fetch(`${API_BASE}/api/patients/${encodeURIComponent(patientId)}/observations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(obs),
  });
  return handleResponse<TwinState>(res);
}

export async function postCycle(patientId: string): Promise<CycleResponse> {
  const res = await fetch(`${API_BASE}/api/patients/${encodeURIComponent(patientId)}/cycle`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  return handleResponse<CycleResponse>(res);
}

export interface DecisionSummary {
  cycle_id: string;
  created_at: string;
  safety_result: string;
  escalated: boolean;
  plan: Plan | null;
}

export async function getDecisions(patientId: string): Promise<DecisionSummary[]> {
  const res = await fetch(`${API_BASE}/api/patients/${encodeURIComponent(patientId)}/decisions`);
  return handleResponse<DecisionSummary[]>(res);
}

export async function getLatestPlan(patientId: string): Promise<Plan> {
  const res = await fetch(`${API_BASE}/api/patients/${encodeURIComponent(patientId)}/plan/latest`);
  return handleResponse<Plan>(res);
}

export interface DebateDetails {
  proposals: Proposal[];
  stances: Stance[];
  debate: Array<{
    round: number;
    agent: string;
    status: "Analyzing" | "Waiting" | "Supporting" | "Challenging" | "Revising" | "Vetoing" | "Approved";
    message: string;
    target_agent: string | null;
  }>;
  safety_events: RuleHit[];
}

export async function getDebateDetails(cycleId: string): Promise<DebateDetails> {
  const res = await fetch(`${API_BASE}/api/decisions/${encodeURIComponent(cycleId)}/debate`);
  return handleResponse<DebateDetails>(res);
}

export async function getAudit(patientId: string): Promise<AuditEntry[]> {
  const res = await fetch(`${API_BASE}/api/patients/${encodeURIComponent(patientId)}/audit`);
  return handleResponse<AuditEntry[]>(res);
}

export async function postWhatIf(patientId: string, request: WhatIfRequest): Promise<WhatIfResponse> {
  const res = await fetch(`${API_BASE}/api/patients/${encodeURIComponent(patientId)}/whatif`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  return handleResponse<WhatIfResponse>(res);
}

export async function simulatorInject(patientId: string, scenario: ScenarioName): Promise<TwinState> {
  const res = await fetch(`${API_BASE}/api/simulator/inject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ patient_id: patientId, scenario }),
  });
  return handleResponse<TwinState>(res);
}

export async function simulatorAdvance(patientId: string, minutes: number): Promise<TwinState> {
  const res = await fetch(`${API_BASE}/api/simulator/advance`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ patient_id: patientId, minutes }),
  });
  return handleResponse<TwinState>(res);
}

export async function simulatorReset(patientId: string): Promise<TwinState> {
  const res = await fetch(`${API_BASE}/api/simulator/reset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ patient_id: patientId }),
  });
  return handleResponse<TwinState>(res);
}

export async function postClinicianReview(cycleId: string, note: string, action: string): Promise<{ ok: boolean }> {
  const res = await fetch(`${API_BASE}/api/decisions/${encodeURIComponent(cycleId)}/clinician-review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ note, action }),
  });
  return handleResponse<{ ok: boolean }>(res);
}

export async function getSimulatorStatus(patientId: string): Promise<SimulatorStatus> {
  const res = await fetch(`${API_BASE}/api/patients/${encodeURIComponent(patientId)}/simulator/status`);
  return handleResponse<SimulatorStatus>(res);
}

export async function getTwinReference(patientId: string): Promise<TwinReference> {
  const res = await fetch(`${API_BASE}/api/patients/${encodeURIComponent(patientId)}/twin/reference`);
  return handleResponse<TwinReference>(res);
}

export async function getScreening(patientId: string): Promise<ScreeningResult> {
  const res = await fetch(`${API_BASE}/api/patients/${encodeURIComponent(patientId)}/screening`);
  return handleResponse<ScreeningResult>(res);
}

export async function runEvaluation(cohortSize = 200, seed = 2026): Promise<EvaluationReport> {
  const res = await fetch(`${API_BASE}/api/evaluation/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cohort_size: cohortSize, seed }),
  });
  return handleResponse<EvaluationReport>(res);
}

export async function getLatestEvaluation(): Promise<EvaluationReport> {
  const res = await fetch(`${API_BASE}/api/evaluation/latest`);
  return handleResponse<EvaluationReport>(res);
}
