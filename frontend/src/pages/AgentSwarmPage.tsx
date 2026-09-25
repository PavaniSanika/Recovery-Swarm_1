import React from "react";
import { useNavigate } from "react-router-dom";
import { useTwin } from "../context/TwinContext";
import { Card, CardHeader, CardTitle, CardDescription } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { getStatusStyle } from "../utils/statusColor";
import { METRIC_COLORS } from "../utils/metricColors";
import { AgentStatus, Proposal, Role } from "../types";
import { Activity, RefreshCw, ShieldAlert } from "lucide-react";

export const AgentSwarmPage: React.FC = () => {
  const navigate = useNavigate();
  const {
    twin,
    latestCycle,
    loading,
    error,
    actionLoading,
    isStreaming,
    liveAgentStatuses,
    liveDebateMessages,
    liveEscalation,
    refreshTwin,
    runOptimizationCycle,
  } = useTwin();

  // 1. Loading State
  if (loading && !twin) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Agent Swarm</h1>
          <p className="text-sm text-slate-500">
            Multi-agent priority routing, debate messages, and stance evolution.
          </p>
        </div>
        <Card className="p-8 text-center animate-pulse">
          <div className="h-6 bg-slate-200 rounded w-1/4 mx-auto mb-4" />
          <div className="h-4 bg-slate-200 rounded w-1/2 mx-auto" />
        </Card>
      </div>
    );
  }

  // 2. Error State
  if (error && !latestCycle && !isStreaming) {
    const errStyle = getStatusStyle("deteriorating");
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Agent Swarm</h1>
          <p className="text-sm text-slate-500">
            Multi-agent priority routing, debate messages, and stance evolution.
          </p>
        </div>
        <Card className={`p-6 border ${errStyle.border} ${errStyle.bg}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className={`w-3 h-3 rounded-full ${errStyle.dotBg}`} />
              <h3 className={`font-semibold ${errStyle.text}`}>Error Loading Swarm Data</h3>
            </div>
            <Button
              variant="outline"
              size="sm"
              icon={<RefreshCw className="w-3.5 h-3.5" />}
              onClick={refreshTwin}
            >
              Retry
            </Button>
          </div>
          <p className="mt-2 text-sm text-slate-700">{error}</p>
        </Card>
      </div>
    );
  }

  // 3. "No Cycle Run Yet" State (Only if no cycle and not currently streaming)
  if (!latestCycle && !isStreaming && Object.keys(liveAgentStatuses).length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">Agent Swarm</h1>
            <p className="text-sm text-slate-500">
              Multi-agent priority routing, debate messages, and stance evolution.
            </p>
          </div>
          <Button
            onClick={runOptimizationCycle}
            disabled={actionLoading}
            className="w-full sm:w-auto"
          >
            {actionLoading ? "Optimizing..." : "Optimize Recovery"}
          </Button>
        </div>

        <Card className="p-8 text-center bg-slate-50/50 border-dashed border-2 border-slate-300">
          <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-6 h-6 text-slate-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 10V3L4 14h7v7l9-11h-7z"
              />
            </svg>
          </div>
          <h3 className="text-base font-semibold text-slate-800 mb-1">
            No Recovery Optimization Cycle Executed Yet
          </h3>
          <p className="text-sm text-slate-600 max-w-md mx-auto mb-6">
            Execute a multi-agent optimization cycle to view dynamic agent priority scores,
            specialist proposals, inter-agent debate stances, and safety verification results.
          </p>
          <Button
            onClick={runOptimizationCycle}
            disabled={actionLoading}
          >
            {actionLoading ? "Executing Swarm Debate..." : "Run Optimization Cycle"}
          </Button>
        </Card>
      </div>
    );
  }

  // Active data derivations
  const activeDebateMessages = liveDebateMessages.length > 0 ? liveDebateMessages : (latestCycle?.debate || []);

  const proposalMap: Record<string, Proposal> = {};
  if (latestCycle?.proposals) {
    latestCycle.proposals.forEach((p) => {
      proposalMap[p.agent] = p;
    });
  }

  const priorityScores = latestCycle?.priority?.priority_scores || {};
  const roles = latestCycle?.priority?.roles || {};

  // Extract Twin Builder debate message if present
  const twinBuilderMsg = activeDebateMessages.find((m) => m.agent === "twin_builder");

  // Escalation detection (immediate upon live WebSocket escalation OR cycle response)
  const isEscalated = Boolean(
    liveEscalation ||
    latestCycle?.escalated ||
    latestCycle?.safety?.result === "escalate" ||
    latestCycle?.safety?.result === "reject"
  );
  const safetyOutcome = latestCycle?.safety?.result || (isEscalated ? "escalate" : "allow");
  const safetyStatusLabel: AgentStatus = isEscalated ? "Vetoing" : "Approved";

  // Group debate messages by round
  const debateRoundsMap: Record<number, typeof activeDebateMessages> = {};
  activeDebateMessages.forEach((msg) => {
    const list = debateRoundsMap[msg.round] || [];
    list.push(msg);
    debateRoundsMap[msg.round] = list;
  });
  const sortedRounds = Object.keys(debateRoundsMap)
    .map(Number)
    .sort((a, b) => a - b);

  // Specialist definitions
  const specialists = [
    {
      id: "mobility",
      title: "Mobility & Pain Agent",
      metricColor: METRIC_COLORS.pain,
      desc: "Evaluates physical activity capacity, step progression, and movement tolerance.",
    },
    {
      id: "inflammation",
      title: "Inflammation & Healing Agent",
      metricColor: METRIC_COLORS.inflammation,
      desc: "Monitors CRP index, swelling levels, and tissue recovery trajectories.",
    },
    {
      id: "sleep",
      title: "Sleep & Recovery Agent",
      metricColor: METRIC_COLORS.sleep,
      desc: "Tracks sleep quality, duration, and restorative sleep-pain interactions.",
    },
    {
      id: "medication",
      title: "Medication Response Agent",
      metricColor: METRIC_COLORS.mobility,
      desc: "Analyzes pain relief timing and medication effectiveness patterns.",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Top Bar / Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-3 mb-1">
            <h1 className="text-2xl font-semibold text-slate-900">Agent Swarm</h1>
            {isStreaming && (
              <Badge variant="outline" className="border-indigo-300 text-indigo-700 bg-indigo-50 animate-pulse flex items-center gap-1.5 text-xs">
                <span className="w-2 h-2 rounded-full bg-indigo-600 animate-ping" />
                Swarm Active (Live Streaming)
              </Badge>
            )}
          </div>
          <p className="text-sm text-slate-500">
            Multi-agent priority routing, debate messages, and stance evolution.
          </p>
        </div>
        <Button
          onClick={runOptimizationCycle}
          disabled={actionLoading || isStreaming}
          className="w-full sm:w-auto shrink-0"
        >
          {actionLoading || isStreaming ? "Swarm Executing..." : "Re-Run Optimization"}
        </Button>
      </div>

      {/* Escalation Alert Banner (Shows IMMEDIATELY when escalation WebSocket event arrives) */}
      {isEscalated && (
        <Card className="p-5 border-red-200 bg-red-50/80">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start space-x-3">
              <ShieldAlert className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <Badge variant="outline" className="border-red-300 bg-red-100 text-red-800 font-bold text-[10px]">
                    ESCALATION EVENT
                  </Badge>
                  <h3 className="text-sm font-bold text-red-900 uppercase tracking-wide">
                    Clinician Escalation Triggered
                  </h3>
                </div>
                <p className="text-xs text-red-800 leading-relaxed">
                  {liveEscalation?.summary || "Safety Guardian triggered escalation during cycle. Activity progression suspended and clinical review requested."}
                </p>
              </div>
            </div>
            <Button
              size="sm"
              variant="outline"
              className="border-red-300 text-red-800 bg-white hover:bg-red-100 text-xs shrink-0 font-medium"
              onClick={() => navigate("/clinician")}
            >
              View Clinician Escalation
            </Button>
          </div>
        </Card>
      )}

      {/* Section 1: 7 Agent Status Cards Grid */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
            <Activity className="w-4 h-4 text-indigo-600" />
            <span>Swarm Agents & Priority Status</span>
          </h2>
          <span className="text-xs text-slate-500 font-mono">
            {latestCycle?.cycle_id ? `Cycle ID: ${latestCycle.cycle_id}` : isStreaming ? "Streaming live cycle..." : ""}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Card 1: Twin Builder (Workflow Component) */}
          <Card className="bg-slate-50/60 border-slate-300 flex flex-col justify-between">
            <div>
              <div className="flex items-start justify-between gap-2 mb-2">
                <div>
                  <span className="text-[10px] font-semibold tracking-wider text-slate-500 uppercase block">
                    Workflow Component
                  </span>
                  <h3 className="text-base font-semibold text-slate-900">Twin Builder</h3>
                </div>
                <Badge variant="outline" className="border-slate-300 text-slate-600 bg-white">
                  Core Engine
                </Badge>
              </div>

              <p className="text-xs text-slate-500 mb-3">
                Maintains digital twin state synchronization from telemetry observations.
              </p>

              <div className="space-y-2 text-xs border-t border-slate-200 pt-3">
                <div className="flex justify-between items-center text-slate-700">
                  <span>Post-Op Day:</span>
                  <span className="font-semibold text-slate-900">Day {twin?.profile.post_op_day ?? 4}</span>
                </div>
                <div className="flex justify-between items-center text-slate-700">
                  <span>Recovery Score:</span>
                  <span className="font-semibold text-slate-900">{twin?.scores.recovery_score ?? 68} / 100</span>
                </div>
                <div className="flex justify-between items-center text-slate-700">
                  <span>Pain / CRP / Steps:</span>
                  <span className="font-mono text-slate-900 font-medium">
                    {twin?.observations.pain.toFixed(1)} | {twin?.observations.crp.toFixed(1)} | {twin?.observations.steps}
                  </span>
                </div>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-200">
              <p className="text-[11px] text-slate-600 italic">
                "{twinBuilderMsg ? twinBuilderMsg.message : `Digital Twin synchronized for ${twin?.profile.name || 'Patient'}.`}"
              </p>
            </div>
          </Card>

          {/* Cards 2-5: 4 Specialist Negotiating Agents */}
          {specialists.map((spec) => {
            const livePayload = liveAgentStatuses[spec.id];
            const prop = proposalMap[spec.id];
            const pScore = livePayload?.confidence ?? (priorityScores[spec.id] ?? 0);
            const role: Role = livePayload?.role || roles[spec.id] || "supporting";

            // Status from live payload or cycle response
            const currentStatus: AgentStatus = livePayload?.status
              ? livePayload.status
              : prop
              ? (latestCycle?.plan ? "Approved" : "Analyzing")
              : isStreaming
              ? "Analyzing"
              : role === "waiting"
              ? "Waiting"
              : "Supporting";

            const statusSt = getStatusStyle(currentStatus);
            const roleBadgeVariant = role === "lead" ? "warning" : "secondary";

            return (
              <Card key={spec.id} className="flex flex-col justify-between">
                <div>
                  {/* Card Header */}
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div>
                      <span
                        className="text-[10px] font-semibold tracking-wider uppercase block"
                        style={{ color: spec.metricColor }}
                      >
                        Specialist Agent
                      </span>
                      <h3 className="text-base font-semibold text-slate-900">{spec.title}</h3>
                    </div>
                    <Badge variant={roleBadgeVariant} className="capitalize">
                      {role}
                    </Badge>
                  </div>

                  <p className="text-xs text-slate-500 mb-3">{spec.desc}</p>

                  {/* Priority & Confidence Metrics */}
                  <div className="space-y-2 text-xs border-t border-slate-100 pt-3">
                    <div className="flex justify-between items-center">
                      <span className="text-slate-600">Priority Score / Conf:</span>
                      <span className="font-mono font-semibold text-slate-900">
                        {pScore > 0 ? (pScore > 1 ? pScore.toFixed(2) : `${Math.round(pScore * 100)}%`) : "N/A"}
                      </span>
                    </div>

                    {/* Proposal / Recommendation */}
                    {livePayload?.recommendation || prop ? (
                      <div className="mt-2 bg-slate-50 p-2 rounded border border-slate-100 space-y-1">
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="font-medium text-slate-700 capitalize">
                            {livePayload?.recommendation || (prop ? `${prop.action_type} (${prop.direction})` : "Analyzing")}
                          </span>
                          {prop?.target_value !== undefined && prop?.target_value !== null && (
                            <span className="font-mono text-slate-900 font-semibold">
                              Target: {prop.target_value}
                            </span>
                          )}
                        </div>
                        {prop?.rationale && (
                          <p className="text-[11px] text-slate-600 line-clamp-2">
                            {prop.rationale}
                          </p>
                        )}
                      </div>
                    ) : (
                      <p className="text-xs text-slate-400 italic mt-2">
                        {isStreaming ? "Analyzing twin data..." : "No active proposal this cycle."}
                      </p>
                    )}
                  </div>
                </div>

                {/* Card Footer: Status Badge */}
                <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                  <span className="text-[11px] text-slate-500 font-medium">Status:</span>
                  <Badge variant="outline" className={statusSt.badge}>
                    {currentStatus}
                  </Badge>
                </div>
              </Card>
            );
          })}

          {/* Card 6: Risk & Safety Guardian (Deterministic Rule Layer) */}
          <Card className="bg-slate-50/60 border-slate-300 flex flex-col justify-between">
            <div>
              <div className="flex items-start justify-between gap-2 mb-2">
                <div>
                  <span className="text-[10px] font-semibold tracking-wider text-red-600 uppercase block">
                    Safety Rule Engine
                  </span>
                  <h3 className="text-base font-semibold text-slate-900">Safety Guardian</h3>
                </div>
                <Badge variant="outline" className="border-red-200 text-red-700 bg-red-50">
                  Deterministic
                </Badge>
              </div>

              <p className="text-xs text-slate-500 mb-3">
                Non-LLM deterministic rule engine (R1-R8) with absolute veto authority.
              </p>

              <div className="space-y-2 text-xs border-t border-slate-200 pt-3">
                <div className="flex justify-between items-center text-slate-700">
                  <span>Safety Evaluation:</span>
                  <span className="font-semibold uppercase tracking-wider text-slate-900">
                    {safetyOutcome}
                  </span>
                </div>
                <div className="flex justify-between items-center text-slate-700">
                  <span>Rules Triggered:</span>
                  <span className="font-mono font-medium text-slate-900">
                    {latestCycle?.safety?.rules_triggered.length || 0}
                  </span>
                </div>
              </div>

              {latestCycle?.safety?.rules_triggered && latestCycle.safety.rules_triggered.length > 0 && (
                <div className="mt-3 bg-red-50 p-2 rounded border border-red-200 space-y-1">
                  <span className="text-[10px] font-bold text-red-800 block uppercase">
                    Safety Rule Hits
                  </span>
                  {latestCycle.safety.rules_triggered.map((hit, idx) => (
                    <div key={idx} className="text-[11px] text-red-700">
                      <span className="font-mono font-bold">{hit.rule_id}:</span> {hit.detail}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="mt-4 pt-3 border-t border-slate-200 flex items-center justify-between">
              <span className="text-[11px] text-slate-500 font-medium">Outcome:</span>
              <Badge variant="outline" className={getStatusStyle(safetyStatusLabel).badge}>
                {safetyStatusLabel}
              </Badge>
            </div>
          </Card>

          {/* Card 7: Negotiation Coordinator */}
          <Card className="bg-slate-50/60 border-slate-300 flex flex-col justify-between">
            <div>
              <div className="flex items-start justify-between gap-2 mb-2">
                <div>
                  <span className="text-[10px] font-semibold tracking-wider text-indigo-600 uppercase block">
                    Consensus Engine
                  </span>
                  <h3 className="text-base font-semibold text-slate-900">Negotiation Coordinator</h3>
                </div>
                <Badge variant="outline" className="border-indigo-200 text-indigo-700 bg-indigo-50">
                  Weighted Scoring
                </Badge>
              </div>

              <p className="text-xs text-slate-500 mb-3">
                Calculates weighted consensus, resolves conflicts, and produces draft plan.
              </p>

              <div className="space-y-2 text-xs border-t border-slate-200 pt-3">
                <div className="flex justify-between items-center text-slate-700">
                  <span>Coalitions Formed:</span>
                  <span className="font-semibold text-slate-900">
                    {latestCycle?.coalitions.length || 0}
                  </span>
                </div>
                <div className="flex justify-between items-center text-slate-700">
                  <span>Escalation Status:</span>
                  <span className={`font-semibold ${isEscalated ? "text-red-600" : "text-emerald-600"}`}>
                    {isEscalated ? "Escalated" : "Plan Drafted"}
                  </span>
                </div>
              </div>

              {latestCycle?.coalitions && latestCycle.coalitions.length > 0 && (
                <div className="mt-3 bg-indigo-50/60 p-2 rounded border border-indigo-200 space-y-1">
                  <span className="text-[10px] font-bold text-indigo-800 block uppercase">
                    Active Coalition
                  </span>
                  {latestCycle.coalitions.map((co, idx) => (
                    <div key={idx} className="text-[11px] text-indigo-900 capitalize font-medium">
                      {co.join(" + ")}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="mt-4 pt-3 border-t border-slate-200 flex items-center justify-between">
              <span className="text-[11px] text-slate-500 font-medium">Resolution:</span>
              <Badge variant="outline" className={getStatusStyle(latestCycle?.plan ? "Approved" : isEscalated ? "Vetoing" : "Analyzing").badge}>
                {latestCycle?.plan ? "Approved" : isEscalated ? "Escalated" : "In Progress"}
              </Badge>
            </div>
          </Card>
        </div>
      </div>

      {/* Section 2: Live Debate Transcript */}
      <Card>
        <CardHeader className="border-b border-slate-100 pb-4">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <span>Live Multi-Agent Debate Log</span>
                {isStreaming && (
                  <span className="text-xs text-indigo-600 font-mono font-normal flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-600 animate-ping" />
                    Streaming...
                  </span>
                )}
              </CardTitle>
              <CardDescription>
                Structured round-by-round transcript of agent proposals, stances, and safety checks.
              </CardDescription>
            </div>
            <Badge variant="secondary" className="font-mono text-xs">
              {activeDebateMessages.length} Transcript Items
            </Badge>
          </div>
        </CardHeader>

        {activeDebateMessages.length > 0 ? (
          <div className="divide-y divide-slate-100">
            {sortedRounds.map((roundNum) => {
              const roundMsgs = debateRoundsMap[roundNum] || [];
              const roundTitle =
                roundNum === 1
                  ? "Round 1 — Initial Proposals & Safety Screening"
                  : `Round ${roundNum} — Inter-Agent Debate, Coalitions & Consensus Approval`;

              return (
                <div key={roundNum} className="p-4 space-y-3">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-bold text-slate-500 uppercase tracking-wider bg-slate-100 px-2 py-0.5 rounded">
                      {roundTitle}
                    </span>
                  </div>

                  <div className="space-y-2">
                    {roundMsgs.map((msg, idx) => {
                      const statusSt = getStatusStyle(msg.status);
                      return (
                        <div
                          key={idx}
                          className="flex flex-col sm:flex-row sm:items-baseline justify-between p-3 rounded-lg bg-slate-50/70 border border-slate-100 text-xs gap-2"
                        >
                          <div className="flex items-baseline space-x-2 flex-1">
                            <span className="font-semibold text-slate-900 capitalize min-w-[120px]">
                              {msg.agent.replace("_", " ")}
                            </span>
                            {msg.target_agent && (
                              <span className="text-slate-400 text-[11px]">
                                → <span className="text-slate-700 capitalize">{msg.target_agent}</span>
                              </span>
                            )}
                            <span className="text-slate-700 flex-1">{msg.message}</span>
                          </div>
                          <div className="self-end sm:self-auto shrink-0">
                            <Badge variant="outline" className={statusSt.badge}>
                              {msg.status}
                            </Badge>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="p-8 text-center text-slate-500 bg-slate-50/50">
            <p className="text-sm font-medium mb-1">Waiting for Swarm Cycle</p>
            <p className="text-xs text-slate-400">
              Click "Optimize Recovery" to trigger the multi-agent debate and view live streaming transcript events.
            </p>
          </div>
        )}
      </Card>
    </div>
  );
};
