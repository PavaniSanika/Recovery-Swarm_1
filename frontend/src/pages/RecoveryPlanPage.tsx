import React from "react";
import { useNavigate } from "react-router-dom";
import { useTwin } from "../context/TwinContext";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { getStatusStyle } from "../utils/statusColor";
import { PlanDisplay } from "../components/PlanDisplay";
import { Plan } from "../types";
import { RefreshCw } from "lucide-react";

export const RecoveryPlanPage: React.FC<{ onNavigateToClinician?: () => void }> = ({
  onNavigateToClinician,
}) => {
  const navigate = useNavigate();
  const {
    twin,
    latestCycle,
    latestPlan,
    loading,
    error,
    actionLoading,
    refreshTwin,
    runOptimizationCycle,
  } = useTwin();

  // 1. Loading State
  if (loading && !twin) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Recovery Plan</h1>
          <p className="text-sm text-slate-500">6–12 hour personalized recovery optimization plan.</p>
        </div>
        <Card className="p-8 text-center animate-pulse">
          <div className="h-6 bg-slate-200 rounded w-1/4 mx-auto mb-4" />
          <div className="h-4 bg-slate-200 rounded w-1/2 mx-auto" />
        </Card>
      </div>
    );
  }

  // 2. Error State
  if (error) {
    const errStyle = getStatusStyle("deteriorating");
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Recovery Plan</h1>
          <p className="text-sm text-slate-500">6–12 hour personalized recovery optimization plan.</p>
        </div>
        <Card className={`p-6 border ${errStyle.border} ${errStyle.bg}`}>
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center space-x-3">
                <div className={`w-3 h-3 rounded-full ${errStyle.dotBg}`} />
                <h3 className={`font-semibold ${errStyle.text}`}>Error Loading Recovery Plan</h3>
              </div>
              <p className="mt-2 text-sm text-slate-700">{error}</p>
            </div>
            <Button
              variant="outline"
              size="sm"
              icon={<RefreshCw className="w-3.5 h-3.5" />}
              onClick={refreshTwin}
              className="bg-white border-red-300 text-red-700 hover:bg-red-50 shrink-0"
            >
              Retry
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  // Determine active plan (latestPlan OR latestCycle.plan OR latestCycle.safety.modified_plan)
  const isEscalated =
    latestCycle?.escalated ||
    latestCycle?.safety?.result === "escalate" ||
    latestCycle?.safety?.result === "reject";

  const activePlan: Plan | null =
    latestPlan ||
    latestCycle?.plan ||
    (isEscalated ? latestCycle?.safety?.modified_plan || null : null);

  // 3. "No Plan Yet" State
  if (!activePlan) {
    return (
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">Recovery Plan</h1>
            <p className="text-sm text-slate-500">6–12 hour personalized recovery optimization plan.</p>
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
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
          </div>
          <h3 className="text-base font-semibold text-slate-800 mb-1">
            No Active Recovery Plan Generated Yet
          </h3>
          <p className="text-sm text-slate-600 max-w-md mx-auto mb-6">
            Execute a multi-agent recovery optimization cycle to generate personalized 6–12 hour
            prioritized recovery recommendations, monitoring parameters, and reassessment schedules.
          </p>
          <Button
            onClick={runOptimizationCycle}
            disabled={actionLoading}
          >
            {actionLoading ? "Generating Plan..." : "Run Optimization Cycle"}
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Recovery Plan</h1>
          <p className="text-sm text-slate-500">6–12 hour personalized recovery optimization plan.</p>
        </div>
        <Button
          onClick={runOptimizationCycle}
          disabled={actionLoading}
          className="w-full sm:w-auto"
        >
          {actionLoading ? "Optimizing..." : "Re-Run Optimization"}
        </Button>
      </div>

      {/* Escalation Interim Guidance Banner (if escalated) */}
      {isEscalated && (
        <Card className="p-5 border-red-200 bg-red-50/80">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center space-x-2">
                <span className="w-2.5 h-2.5 rounded-full bg-red-600 animate-pulse" />
                <h3 className="text-sm font-bold text-red-900 uppercase tracking-wide">
                  Interim Safety Guidance — Clinician Escalation Active
                </h3>
              </div>
              <p className="text-xs text-red-800">
                Safety Guardian triggered escalation. Activity progression suspended pending clinical review.
              </p>
            </div>
            <Button
              variant="outline"
              onClick={() => {
                if (onNavigateToClinician) {
                  onNavigateToClinician();
                } else {
                  navigate("/clinician");
                }
              }}
              className="shrink-0 border-red-300 text-red-800 hover:bg-red-100 text-xs"
            >
              View Clinician Escalation
            </Button>
          </div>
        </Card>
      )}

      {/* Render Plan Display */}
      <PlanDisplay plan={activePlan} titlePrefix="Recovery Optimization Plan" />
    </div>
  );
};
