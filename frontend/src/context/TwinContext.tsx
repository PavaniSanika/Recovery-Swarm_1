import React, { createContext, useContext, useEffect, useState } from "react";
import {
  getLatestPlan,
  getScreening,
  getSimulatorStatus,
  getTwin,
  getTwinReference,
  postCycle,
  simulatorAdvance,
  simulatorInject,
  simulatorReset,
} from "../api";
import {
  AgentStatusPayload,
  CycleResponse,
  DebateMessage,
  Plan,
  ScenarioName,
  TwinState,
  WsMessage,
} from "../types";
import { ScreeningResult, SimulatorStatus, TwinReference } from "../types.ext";
import { RecoverySwarmWebSocket } from "../ws";

export interface TwinContextType {
  patientId: string;
  twin: TwinState | null;
  latestCycle: CycleResponse | null;
  latestPlan: Plan | null;
  simulatorStatus: SimulatorStatus | null;
  twinReference: TwinReference | null;
  screeningResult: ScreeningResult | null;
  loading: boolean;
  error: string | null;
  actionLoading: boolean;
  isStreaming: boolean;
  liveAgentStatuses: Record<string, AgentStatusPayload>;
  liveDebateMessages: DebateMessage[];
  liveEscalation: { cycle_id: string; summary: string } | null;
  refreshTwin: () => Promise<void>;
  refreshScreening: () => Promise<void>;
  injectScenario: (scenario: ScenarioName) => Promise<void>;
  advanceTime: (minutes: number) => Promise<void>;
  runOptimizationCycle: () => Promise<void>;
  resetPatient: () => Promise<void>;
}

const TwinContext = createContext<TwinContextType | undefined>(undefined);

const formatErrorMessage = (err: unknown, defaultMsg: string): string => {
  if (err instanceof Error) {
    const m = err.message;
    if (
      m.includes("Failed to fetch") ||
      m.includes("NetworkError") ||
      m.includes("ECONNREFUSED") ||
      m.includes("Network request failed")
    ) {
      return "Backend service unavailable. Please check that the server is running on http://localhost:8000.";
    }
    return m;
  }
  return defaultMsg;
};

export const TwinProvider: React.FC<{ children: React.ReactNode; patientId?: string }> = ({
  children,
  patientId = "P001",
}) => {
  const [twin, setTwin] = useState<TwinState | null>(null);
  const [latestCycle, setLatestCycle] = useState<CycleResponse | null>(null);
  const [latestPlan, setLatestPlan] = useState<Plan | null>(null);
  const [simulatorStatus, setSimulatorStatus] = useState<SimulatorStatus | null>(null);
  const [twinReference, setTwinReference] = useState<TwinReference | null>(null);
  const [screeningResult, setScreeningResult] = useState<ScreeningResult | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<boolean>(false);

  // Live WebSocket Streaming state
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [liveAgentStatuses, setLiveAgentStatuses] = useState<Record<string, AgentStatusPayload>>({});
  const [liveDebateMessages, setLiveDebateMessages] = useState<DebateMessage[]>([]);
  const [liveEscalation, setLiveEscalation] = useState<{ cycle_id: string; summary: string } | null>(null);

  const fetchAuxiliaryData = async () => {
    try {
      const statusData = await getSimulatorStatus(patientId);
      setSimulatorStatus(statusData);
    } catch {
      setSimulatorStatus(null);
    }

    try {
      const refData = await getTwinReference(patientId);
      setTwinReference(refData);
    } catch {
      setTwinReference(null);
    }

    try {
      const screeningData = await getScreening(patientId);
      setScreeningResult(screeningData);
    } catch {
      setScreeningResult(null);
    }
  };

  const refreshScreening = async () => {
    try {
      const screeningData = await getScreening(patientId);
      setScreeningResult(screeningData);
    } catch {
      setScreeningResult(null);
    }
  };

  const refreshTwin = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getTwin(patientId);
      setTwin(data);
      await fetchAuxiliaryData();
      try {
        const p = await getLatestPlan(patientId);
        if (p) setLatestPlan(p);
      } catch {
        // Retain current in-memory plan if getLatestPlan returns 404
      }
    } catch (err: unknown) {
      setError(formatErrorMessage(err, "Failed to load Digital Twin data."));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshTwin();
  }, [patientId]);

  // Note on auto-advance after scenario injection:
  // Scenarios loaded by /api/simulator/inject start at minute_offset 0 (baseline readings).
  // For multi-step scenarios (e.g. recovery_deviation, pain_spike), peak symptoms and
  // safety escalation triggers (e.g. R1 pain spike, R8 wound flags) occur at later steps
  // (minute_offset 120 or 180). Auto-advance advances time to the scenario's final step
  // immediately after injection so that clicking "Optimize Recovery" triggers the expected
  // swarm debate and safety escalation during live demo flow without requiring extra manual clicks.
  // For single-reading scenarios (total_steps <= 1), advancing is a no-op.
  const injectScenario = async (scenario: ScenarioName) => {
    setActionLoading(true);
    setError(null);
    try {
      const updated = await simulatorInject(patientId, scenario);
      setTwin(updated);

      const statusData = await getSimulatorStatus(patientId);
      if (statusData && statusData.max_minute_offset > statusData.minute_offset) {
        const minutesToAdvance = statusData.max_minute_offset - statusData.minute_offset;
        if (minutesToAdvance > 0) {
          const finalUpdated = await simulatorAdvance(patientId, minutesToAdvance);
          setTwin(finalUpdated);
        }
      }

      await fetchAuxiliaryData();
    } catch (err: unknown) {
      setError(formatErrorMessage(err, `Failed to inject scenario '${scenario}'.`));
    } finally {
      setActionLoading(false);
    }
  };

  const advanceTime = async (minutes: number) => {
    setActionLoading(true);
    setError(null);
    try {
      const updated = await simulatorAdvance(patientId, minutes);
      setTwin(updated);
      await fetchAuxiliaryData();
    } catch (err: unknown) {
      setError(formatErrorMessage(err, `Failed to advance time by ${minutes} min.`));
    } finally {
      setActionLoading(false);
    }
  };

  const runOptimizationCycle = async () => {
    setActionLoading(true);
    setIsStreaming(true);
    setError(null);
    setLiveDebateMessages([]);
    setLiveEscalation(null);
    setLiveAgentStatuses({});

    let wsClient: RecoverySwarmWebSocket | null = null;
    try {
      wsClient = new RecoverySwarmWebSocket({
        patientId,
        onMessage: (msg: WsMessage) => {
          switch (msg.type) {
            case "twin_update":
              setTwin(msg.payload);
              break;
            case "agent_status":
              setLiveAgentStatuses((prev) => ({
                ...prev,
                [msg.payload.agent]: msg.payload,
              }));
              break;
            case "debate_message":
              setLiveDebateMessages((prev) => [...prev, msg.payload]);
              break;
            case "plan":
              setLatestPlan(msg.payload);
              break;
            case "escalation":
              setLiveEscalation(msg.payload);
              break;
          }
        },
        onError: (err) => {
          console.warn("WebSocket client connection error (falling back to HTTP):", err);
        },
      });

      wsClient.connect();

      // Invoke HTTP cycle simultaneously
      const cycleRes = await postCycle(patientId);
      setLatestCycle(cycleRes);
      setTwin(cycleRes.twin);
      const planToSet = cycleRes.plan || cycleRes.safety?.modified_plan || null;
      if (planToSet) {
        setLatestPlan(planToSet);
      }
      await fetchAuxiliaryData();
    } catch (err: unknown) {
      setError(formatErrorMessage(err, "Failed to run recovery optimization cycle."));
    } finally {
      setActionLoading(false);
      setIsStreaming(false);
      if (wsClient) {
        wsClient.disconnect();
      }
    }
  };

  const resetPatient = async () => {
    setActionLoading(true);
    setError(null);
    try {
      const baseline = await simulatorReset(patientId);
      setTwin(baseline);
      setLatestCycle(null);
      setLatestPlan(null);
      setLiveDebateMessages([]);
      setLiveEscalation(null);
      setLiveAgentStatuses({});
      await fetchAuxiliaryData();
    } catch (err: unknown) {
      setError(formatErrorMessage(err, "Failed to reset patient state."));
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <TwinContext.Provider
      value={{
        patientId,
        twin,
        latestCycle,
        latestPlan,
        simulatorStatus,
        twinReference,
        screeningResult,
        loading,
        error,
        actionLoading,
        isStreaming,
        liveAgentStatuses,
        liveDebateMessages,
        liveEscalation,
        refreshTwin,
        refreshScreening,
        injectScenario,
        advanceTime,
        runOptimizationCycle,
        resetPatient,
      }}
    >
      {children}
    </TwinContext.Provider>
  );
};

export const useTwin = (): TwinContextType => {
  const context = useContext(TwinContext);
  if (!context) {
    throw new Error("useTwin must be used within a TwinProvider");
  }
  return context;
};
