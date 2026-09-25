import React, { useEffect, useState } from "react";
import { useTwin } from "../context/TwinContext";
import { getAudit } from "../api";
import { Card, CardHeader, CardTitle, CardDescription } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { getStatusStyle } from "../utils/statusColor";
import { METRIC_COLORS } from "../utils/metricColors";
import { AuditEntry } from "../types";
import { RefreshCw } from "lucide-react";

export const ClinicianViewPage: React.FC = () => {
  const {
    twin,
    latestCycle,
    twinReference,
    loading: twinLoading,
    error: twinError,
    actionLoading,
    refreshTwin,
    runOptimizationCycle,
  } = useTwin();

  const [auditEntries, setAuditEntries] = useState<AuditEntry[]>([]);
  const [auditLoading, setAuditLoading] = useState<boolean>(true);
  const [auditError, setAuditError] = useState<string | null>(null);

  const fetchAuditLog = async () => {
    setAuditLoading(true);
    setAuditError(null);
    try {
      const data = await getAudit("P001");
      setAuditEntries(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load audit trail log.";
      setAuditError(msg);
    } finally {
      setAuditLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditLog();
  }, [twin, latestCycle]);

  // Combined loading / error
  const isLoading = twinLoading || (auditLoading && auditEntries.length === 0);
  const displayError = twinError || auditError;

  // 1. Loading State
  if (isLoading && !twin) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Clinician View</h1>
          <p className="text-sm text-slate-500">
            Clinical decision support, safety escalation details, and audit trail logs.
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
  if (displayError && !twin) {
    const errStyle = getStatusStyle("deteriorating");
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Clinician View</h1>
          <p className="text-sm text-slate-500">
            Clinical decision support, safety escalation details, and audit trail logs.
          </p>
        </div>
        <Card className={`p-6 border ${errStyle.border} ${errStyle.bg}`}>
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center space-x-3">
                <div className={`w-3 h-3 rounded-full ${errStyle.dotBg}`} />
                <h3 className={`font-semibold ${errStyle.text}`}>Error Loading Clinician Data</h3>
              </div>
              <p className="mt-2 text-sm text-slate-700">{displayError}</p>
            </div>
            <Button
              variant="outline"
              size="sm"
              icon={<RefreshCw className="w-3.5 h-3.5" />}
              onClick={() => {
                refreshTwin();
                fetchAuditLog();
              }}
              className="bg-white border-red-300 text-red-700 hover:bg-red-50 shrink-0"
            >
              Retry
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  // Check deviation status established in Stage F3
  const hasDeviation =
    twin?.trajectory.overall !== "on_track" ||
    latestCycle?.escalated ||
    latestCycle?.safety?.result === "escalate" ||
    latestCycle?.safety?.result === "reject";

  // Check if current cycle is escalated
  const isEscalated =
    latestCycle?.escalated ||
    latestCycle?.safety?.result === "escalate" ||
    latestCycle?.safety?.result === "reject";

  // Expected reference values sourced from TwinReference (Stage F3)
  const expPain = twinReference?.expected_pain ?? 4.0;
  const expInflammation = twinReference?.expected_inflammation ?? 5.2;
  const expSteps = twinReference?.expected_steps ?? 2500;

  // Actual telemetry
  const actPain = twin?.observations.pain ?? 0;
  const actInflammation = twin?.scores.inflammation_score ?? 0;
  const actSteps = twin?.observations.steps ?? 0;
  const actSwelling = twin?.observations.swelling ?? 0;

  return (
    <div className="space-y-6">
      {/* Page Header & Honest-Labeling Disclaimer */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 mb-1">
            <h1 className="text-2xl font-semibold text-slate-900">Clinician View</h1>
            <Badge variant="outline" className="border-indigo-200 text-indigo-700 bg-indigo-50 text-[10px]">
              Decision Support System
            </Badge>
          </div>
          <p className="text-xs text-slate-500">
            Screening flags, safety escalation reasoning, and verified audit log trail. Recommends clinician review; does not diagnose or prescribe.
          </p>
        </div>

        <Button
          onClick={runOptimizationCycle}
          disabled={actionLoading}
          className="w-full sm:w-auto shrink-0"
        >
          {actionLoading ? "Optimizing..." : "Re-Run Optimization"}
        </Button>
      </div>

      {/* Honest Labeling Top Banner */}
      <div className="bg-slate-100 border border-slate-200 rounded-lg p-3 text-xs text-slate-600 flex items-center justify-between">
        <span>
          <strong className="font-semibold text-slate-800">Safety Positioning Statement:</strong> RECOVERY-SWARM is an illustrative clinical decision-support prototype. Critical clinical decisions, diagnoses, and medication management remain under qualified healthcare professional oversight.
        </span>
      </div>

      {/* Section 1: Patient Summary & Digital Twin Snapshot Card */}
      {twin && (
        <Card className="p-6">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pb-6 border-b border-slate-100">
            <div>
              <div className="flex items-center space-x-3 mb-1">
                <h2 className="text-xl font-bold text-slate-900">{twin.profile.name}</h2>
                <Badge variant="secondary">Age {twin.profile.age}</Badge>
                <Badge variant="outline" className="border-slate-300 text-slate-700">
                  {twin.profile.surgery}
                </Badge>
              </div>
              <p className="text-xs text-slate-500">
                Patient ID: <span className="font-mono font-semibold">{twin.patient_id}</span> • Post-Op Day {twin.profile.post_op_day}
              </p>
            </div>

            {/* Trajectory Badges */}
            <div className="flex flex-wrap items-center gap-2">
              <div className="text-right mr-2">
                <span className="text-[10px] text-slate-400 block uppercase tracking-wider font-semibold">
                  Overall Trajectory
                </span>
                <Badge variant="outline" className={getStatusStyle(twin.trajectory.overall).badge}>
                  {twin.trajectory.overall.replace(/_/g, " ")}
                </Badge>
              </div>

              <div className="text-right mr-2">
                <span className="text-[10px] text-slate-400 block uppercase tracking-wider font-semibold">
                  Inflammation
                </span>
                <Badge variant="outline" className={getStatusStyle(twin.trajectory.inflammation).badge}>
                  {twin.trajectory.inflammation.replace(/_/g, " ")}
                </Badge>
              </div>

              <div className="text-right mr-2">
                <span className="text-[10px] text-slate-400 block uppercase tracking-wider font-semibold">
                  Mobility
                </span>
                <Badge variant="outline" className={getStatusStyle(twin.trajectory.mobility).badge}>
                  {twin.trajectory.mobility.replace(/_/g, " ")}
                </Badge>
              </div>

              <div className="text-right">
                <span className="text-[10px] text-slate-400 block uppercase tracking-wider font-semibold">
                  Sleep
                </span>
                <Badge variant="outline" className={getStatusStyle(twin.trajectory.sleep).badge}>
                  {twin.trajectory.sleep.replace(/_/g, " ")}
                </Badge>
              </div>
            </div>
          </div>

          {/* Telemetry Metrics Snapshot Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-4 pt-6 text-xs">
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
              <span className="text-[11px] text-slate-500 block">Pain Score</span>
              <span className="text-base font-bold font-mono" style={{ color: METRIC_COLORS.pain }}>
                {actPain.toFixed(1)} / 10
              </span>
              <span className="text-[10px] text-slate-400 block mt-0.5">Exp: {expPain.toFixed(1)}</span>
            </div>

            <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
              <span className="text-[11px] text-slate-500 block">CRP Index</span>
              <span className="text-base font-bold font-mono" style={{ color: METRIC_COLORS.inflammation }}>
                {twin.observations.crp.toFixed(1)} / 10
              </span>
              <span className="text-[10px] text-slate-400 block mt-0.5">Exp: {expInflammation.toFixed(1)}</span>
            </div>

            <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
              <span className="text-[11px] text-slate-500 block">Daily Steps</span>
              <span className="text-base font-bold font-mono" style={{ color: METRIC_COLORS.mobility }}>
                {actSteps}
              </span>
              <span className="text-[10px] text-slate-400 block mt-0.5">Target: {expSteps}</span>
            </div>

            <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
              <span className="text-[11px] text-slate-500 block">Sleep Hours</span>
              <span className="text-base font-bold font-mono" style={{ color: METRIC_COLORS.sleep }}>
                {twin.observations.sleep_hours.toFixed(1)} h
              </span>
              <span className="text-[10px] text-slate-400 block mt-0.5">Target: 7.5h</span>
            </div>

            <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
              <span className="text-[11px] text-slate-500 block">Swelling Score</span>
              <span className="text-base font-bold font-mono text-slate-900">
                {actSwelling.toFixed(1)} / 10
              </span>
              <span className="text-[10px] text-slate-400 block mt-0.5">Baseline: 6.0</span>
            </div>

            <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
              <span className="text-[11px] text-slate-500 block">Recovery Score</span>
              <span className="text-base font-bold font-mono text-slate-900">
                {twin.scores.recovery_score} / 100
              </span>
              <span className="text-[10px] text-slate-400 block mt-0.5">Prototype metric</span>
            </div>
          </div>
        </Card>
      )}

      {/* Section 2: Recent Telemetry & Deviation Check Section */}
      <Card className="p-6">
        <CardHeader className="p-0 pb-4 border-b border-slate-100">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base">Recent Telemetry Trends & Trajectory Deviation</CardTitle>
              <CardDescription>
                Compares current observations against post-op Day {twin?.profile.post_op_day} reference expectations.
              </CardDescription>
            </div>
            <Badge variant="outline" className={getStatusStyle(twin?.trajectory.overall).badge}>
              {hasDeviation ? "Deviation Detected" : "On Track"}
            </Badge>
          </div>
        </CardHeader>

        <div className="pt-4 space-y-4">
          {hasDeviation ? (
            <div className="p-4 rounded-lg bg-orange-50 border border-orange-200 text-xs text-orange-900 space-y-2">
              <div className="flex items-center space-x-2">
                <span className="w-2.5 h-2.5 rounded-full bg-orange-500" />
                <h4 className="font-bold uppercase tracking-wide text-orange-900">
                  Recovery Trajectory Deviation Identified
                </h4>
              </div>
              <p className="text-orange-800 leading-relaxed">
                Patient telemetry exhibits deviation from standard Day {twin?.profile.post_op_day} Total Knee Replacement recovery curves.
                {actPain > expPain && ` Pain score (${actPain.toFixed(1)}) exceeds expected baseline (${expPain.toFixed(1)}).`}
                {actInflammation > expInflammation && ` Inflammation index (${actInflammation.toFixed(1)}) is elevated above expected (${expInflammation.toFixed(1)}).`}
                {actSteps < expSteps && ` Daily mobility (${actSteps} steps) is below expected step target (${expSteps}).`}
              </p>
            </div>
          ) : (
            <div className="p-4 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-900">
              <p>
                Patient telemetry remains aligned with expected Post-Op Day {twin?.profile.post_op_day} recovery reference curves.
              </p>
            </div>
          )}
        </div>
      </Card>

      {/* Section 3: Safety Escalation Detail Card (When Escalated) */}
      {isEscalated && (
        <Card className="p-6 border-red-200 bg-red-50/50 space-y-4">
          <div className="flex items-start justify-between gap-4 border-b border-red-200 pb-4">
            <div>
              <span className="text-[10px] font-bold text-red-700 uppercase tracking-wider block">
                Deterministic Safety Layer Event
              </span>
              <h3 className="text-lg font-bold text-red-900">Safety Guardian Escalation Detail</h3>
              <p className="text-xs text-red-700 mt-1">
                Triggered by deterministic rules (R1-R8) in thresholds.yaml. Recommends clinician review.
              </p>
            </div>
            <Badge variant="outline" className="border-red-300 text-red-800 bg-red-100 font-bold">
              ESCALATION ACTIVE
            </Badge>
          </div>

          {/* Triggered Rules List */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold text-red-900 uppercase tracking-wide">
              Triggered Safety Rules ({latestCycle?.safety?.rules_triggered.length || 0})
            </h4>

            {latestCycle?.safety?.rules_triggered && latestCycle.safety.rules_triggered.length > 0 ? (
              <div className="space-y-2">
                {latestCycle.safety.rules_triggered.map((ruleHit, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-white rounded-lg border border-red-200 text-xs space-y-1 shadow-sm"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-red-800 bg-red-100 px-2 py-0.5 rounded text-[11px]">
                        Rule {ruleHit.rule_id} — {ruleHit.outcome.toUpperCase()}
                      </span>
                    </div>
                    <p className="text-slate-800 font-medium pt-1">{ruleHit.detail}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-red-700 italic">
                Safety Guardian triggered escalation based on clinical telemetry red flags.
              </p>
            )}
          </div>

          {/* Agent Recommendations Leading to Safety Check */}
          {latestCycle?.proposals && latestCycle.proposals.length > 0 && (
            <div className="space-y-2 pt-2 border-t border-red-200">
              <h4 className="text-xs font-bold text-red-900 uppercase tracking-wide">
                Specialist Proposals Prior to Escalation
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {latestCycle.proposals.map((p, idx) => (
                  <div key={idx} className="p-2.5 bg-white/80 rounded border border-red-200 text-xs">
                    <span className="font-semibold text-slate-900 capitalize block mb-0.5">
                      {p.agent} Agent: {p.action_type} ({p.direction})
                    </span>
                    <p className="text-slate-600 text-[11px] line-clamp-2">{p.rationale}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* System Recommendation */}
          <div className="bg-red-100/80 p-4 rounded-lg border border-red-300 text-xs text-red-900 space-y-1">
            <span className="font-bold block uppercase tracking-wide">System Recommendation</span>
            <p className="leading-relaxed">
              Automatic escalation to clinical team triggered. Activity progression suspended and clinical review of pain management and swelling control requested.
            </p>
          </div>
        </Card>
      )}

      {/* Section 4: Real Chronological Audit Trail Table */}
      <Card>
        <CardHeader className="border-b border-slate-100 pb-4">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Decision & Safety Audit Trail Log</CardTitle>
              <CardDescription>
                Chronological ledger of safety evaluation events, rule triggers, and swarm decisions persisted to SQLite.
              </CardDescription>
            </div>
            <Button
              variant="outline"
              onClick={fetchAuditLog}
              disabled={auditLoading}
              className="text-xs"
            >
              {auditLoading ? "Refreshing..." : "Refresh Log"}
            </Button>
          </div>
        </CardHeader>

        {auditEntries.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
                  <th className="p-3">Timestamp</th>
                  <th className="p-3">Cycle ID</th>
                  <th className="p-3">Actor</th>
                  <th className="p-3">Event Detail</th>
                  <th className="p-3">Rule ID</th>
                  <th className="p-3 text-right">Outcome</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {auditEntries.map((entry, idx) => {
                  const outcomeSt = getStatusStyle(entry.outcome);
                  return (
                    <tr key={idx} className="hover:bg-slate-50/60 transition-colors">
                      <td className="p-3 font-mono text-slate-500 whitespace-nowrap">
                        {new Date(entry.timestamp).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit",
                        })}
                      </td>
                      <td className="p-3 font-mono text-slate-700 font-semibold whitespace-nowrap">
                        {entry.cycle_id}
                      </td>
                      <td className="p-3 font-semibold text-slate-900 whitespace-nowrap">
                        {entry.actor}
                      </td>
                      <td className="p-3 text-slate-700 leading-normal max-w-md">
                        {entry.event}
                      </td>
                      <td className="p-3 font-mono text-slate-600 font-semibold whitespace-nowrap">
                        {entry.rule_id ? (
                          <Badge variant="outline" className="border-slate-300 bg-white">
                            {entry.rule_id}
                          </Badge>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                      <td className="p-3 text-right whitespace-nowrap">
                        <Badge variant="outline" className={outcomeSt.badge}>
                          {entry.outcome}
                        </Badge>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-8 text-center text-slate-500 bg-slate-50/50">
            <p className="text-sm font-medium mb-1">No Audit Trail Logs Persisted Yet</p>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              Execute a recovery cycle to generate safety evaluation rows and coordinator decision audit records in the database.
            </p>
          </div>
        )}
      </Card>
    </div>
  );
};
