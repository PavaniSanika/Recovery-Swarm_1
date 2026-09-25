import React from "react";
import { useTwin } from "../context/TwinContext";
import { Card, CardHeader, CardTitle, CardDescription } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { getStatusSemantic } from "../utils/statusColor";
import {
  Activity,
  Thermometer,
  Footprints,
  Moon,
  AlertTriangle,
  RefreshCw,
  TrendingUp,
  Pill,
  Heart,
  Droplets,
  Clock,
  ShieldCheck,
  Cpu,
  FileQuestion,
  CheckCircle2,
} from "lucide-react";

export const DashboardPage: React.FC = () => {
  const { twin, latestCycle, latestPlan, screeningResult, loading, error, refreshTwin, runOptimizationCycle, actionLoading } =
    useTwin();

  const isEscalated =
    latestCycle?.escalated ||
    latestCycle?.safety?.result === "escalate" ||
    latestCycle?.safety?.result === "reject";

  const activePlan =
    latestPlan ||
    latestCycle?.plan ||
    (isEscalated ? latestCycle?.safety?.modified_plan || null : null);

  // Determine highest screening severity
  const flags = screeningResult?.flags || [];
  const hasUrgent = flags.some((f) => f.severity === "urgent");
  const hasReview = flags.some((f) => f.severity === "review");
  const screeningSeverity: "none" | "review" | "urgent" = hasUrgent ? "urgent" : hasReview ? "review" : "none";

  // 1. LOADING STATE (Real Skeleton Loader)
  if (loading && !twin) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 bg-slate-200 rounded w-1/3"></div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="h-36 bg-slate-200 rounded-lg lg:col-span-2"></div>
          <div className="h-36 bg-slate-200 rounded-lg"></div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-28 bg-slate-200 rounded-lg"></div>
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="h-44 bg-slate-200 rounded-lg"></div>
          <div className="h-44 bg-slate-200 rounded-lg"></div>
        </div>
      </div>
    );
  }

  // 2. ERROR STATE (Real Error Banner)
  if (error && !twin) {
    return (
      <div className="space-y-4">
        <Card className="border-red-200 bg-red-50/60">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
            <div className="space-y-1 flex-1">
              <h3 className="text-sm font-semibold text-red-900">Failed to load Digital Twin</h3>
              <p className="text-xs text-red-700">{error}</p>
            </div>
            <Button
              variant="outline"
              size="sm"
              icon={<RefreshCw className="w-3.5 h-3.5" />}
              onClick={refreshTwin}
              className="bg-white border-red-300 text-red-700 hover:bg-red-50"
            >
              Retry
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  if (!twin) return null;

  const { profile, observations, scores, trajectory, medications } = twin;

  return (
    <div className="space-y-6">
      {/* Inline Error Alert if background refresh fails */}
      {error && (
        <Card padding="sm" className="border-red-200 bg-red-50/60">
          <div className="flex items-center justify-between text-xs text-red-800">
            <span className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
              <span>{error}</span>
            </span>
            <Button variant="ghost" size="sm" onClick={refreshTwin} className="h-6 text-xs text-red-700">
              Retry
            </Button>
          </div>
        </Card>
      )}

      {/* Patient Header & Recovery Score */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Patient Profile Card */}
        <Card className="lg:col-span-2 flex flex-col justify-between">
          <div>
            <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-semibold text-slate-900">{profile.name}</h2>
                <Badge variant="neutral" size="sm">
                  ID: {twin.patient_id}
                </Badge>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={getStatusSemantic(trajectory.overall)} dot>
                  Overall: {trajectory.overall.replace(/_/g, " ")}
                </Badge>
                <span title="Screening flag only. Not a diagnosis. Clinician review required.">
                  <Badge
                    variant={
                      screeningSeverity === "urgent"
                        ? "danger"
                        : screeningSeverity === "review"
                        ? "warning"
                        : "success"
                    }
                    size="sm"
                  >
                    Screening: {screeningSeverity === "urgent" ? "Urgent Review" : screeningSeverity === "review" ? "Review Flagged" : "Clear"}
                  </Badge>
                </span>
              </div>
            </div>
            <p className="text-xs text-slate-500">
              {profile.surgery} • Age {profile.age} • Post-Op Day {profile.post_op_day} • <span className="text-[11px] text-slate-400 font-normal">Screening flag only. Not a diagnosis. Clinician review required.</span>
            </p>
          </div>

          <div className="pt-4 mt-4 border-t border-slate-100 grid grid-cols-3 gap-2 text-xs">
            <div>
              <span className="text-slate-400 block text-[11px]">Inflammation Trajectory</span>
              <Badge variant={getStatusSemantic(trajectory.inflammation)} size="sm" className="mt-1">
                {trajectory.inflammation.replace(/_/g, " ")}
              </Badge>
            </div>
            <div>
              <span className="text-slate-400 block text-[11px]">Mobility Trajectory</span>
              <Badge variant={getStatusSemantic(trajectory.mobility)} size="sm" className="mt-1">
                {trajectory.mobility.replace(/_/g, " ")}
              </Badge>
            </div>
            <div>
              <span className="text-slate-400 block text-[11px]">Sleep Quality</span>
              <Badge variant={getStatusSemantic(trajectory.sleep)} size="sm" className="mt-1">
                {trajectory.sleep}
              </Badge>
            </div>
          </div>
        </Card>

        {/* Recovery Score Card */}
        <Card className="flex flex-col justify-between border-teal-200/80 bg-gradient-to-br from-white to-teal-50/20">
          <div>
            <div className="flex justify-between items-start">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Recovery Score
              </span>
              <Activity className="w-4 h-4 text-teal-600" />
            </div>

            <div className="my-3 flex items-baseline gap-2">
              <span className="text-4xl font-bold text-slate-900">{scores.recovery_score}</span>
              <span className="text-slate-400 text-sm font-medium">/ 100</span>
            </div>
          </div>

          <div className="pt-2 border-t border-slate-100">
            <p className="text-[11px] text-slate-500 leading-snug">
              Recovery Score is an illustrative prototype metric and is not a clinically validated prediction.
            </p>
          </div>
        </Card>
      </div>

      {/* Physiological Vitals Grid (6 Metric Cards) */}
      <div>
        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
          Current Physiological Vitals & Synthetic Indices
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {/* Pain Level */}
          <Card padding="sm" className="flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-slate-500 text-[11px] mb-1">
                <span>Pain Level</span>
                <Activity className="w-3.5 h-3.5 text-amber-500" />
              </div>
              <div className="text-xl font-semibold text-slate-900">
                {observations.pain} <span className="text-xs font-normal text-slate-400">/ 10</span>
              </div>
            </div>
            <div className="mt-2 pt-2 border-t border-slate-100">
              <Badge variant={getStatusSemantic(observations.pain > 6 ? "below_expected" : "on_track")} size="sm">
                {observations.pain > 6 ? "Elevated" : "Controlled"}
              </Badge>
            </div>
          </Card>

          {/* Mobility (Steps) */}
          <Card padding="sm" className="flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-slate-500 text-[11px] mb-1">
                <span>Mobility (Steps)</span>
                <Footprints className="w-3.5 h-3.5 text-blue-500" />
              </div>
              <div className="text-xl font-semibold text-slate-900">
                {observations.steps.toLocaleString()}
              </div>
            </div>
            <div className="mt-2 pt-2 border-t border-slate-100">
              <Badge variant={getStatusSemantic(trajectory.mobility)} size="sm">
                Capacity: {scores.mobility_capacity}/10
              </Badge>
            </div>
          </Card>

          {/* Sleep Duration */}
          <Card padding="sm" className="flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-slate-500 text-[11px] mb-1">
                <span>Sleep Duration</span>
                <Moon className="w-3.5 h-3.5 text-indigo-500" />
              </div>
              <div className="text-xl font-semibold text-slate-900">
                {observations.sleep_hours} <span className="text-xs font-normal text-slate-400">hrs</span>
              </div>
            </div>
            <div className="mt-2 pt-2 border-t border-slate-100">
              <Badge variant={getStatusSemantic(trajectory.sleep)} size="sm">
                Quality: {scores.sleep_quality}/10
              </Badge>
            </div>
          </Card>

          {/* Inflammatory Marker Index */}
          <Card padding="sm" className="flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-slate-500 text-[11px] mb-1">
                <span>CRP Index (0-10)</span>
                <Droplets className="w-3.5 h-3.5 text-rose-500" />
              </div>
              <div className="text-xl font-semibold text-slate-900">
                {observations.crp} <span className="text-xs font-normal text-slate-400">/ 10</span>
              </div>
            </div>
            <div className="mt-2 pt-2 border-t border-slate-100">
              <Badge variant={getStatusSemantic(trajectory.inflammation)} size="sm">
                Score: {scores.inflammation_score}/10
              </Badge>
            </div>
          </Card>

          {/* Joint Swelling */}
          <Card padding="sm" className="flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-slate-500 text-[11px] mb-1">
                <span>Joint Swelling</span>
                <Thermometer className="w-3.5 h-3.5 text-orange-500" />
              </div>
              <div className="text-xl font-semibold text-slate-900">
                {observations.swelling} <span className="text-xs font-normal text-slate-400">/ 10</span>
              </div>
            </div>
            <div className="mt-2 pt-2 border-t border-slate-100">
              <Badge variant={getStatusSemantic(observations.swelling > 6 ? "below_expected" : "on_track")} size="sm">
                {observations.swelling > 6 ? "Moderate/High" : "Mild"}
              </Badge>
            </div>
          </Card>

          {/* Temp & Heart Rate */}
          <Card padding="sm" className="flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-slate-500 text-[11px] mb-1">
                <span>Vitals (Temp/HR)</span>
                <Heart className="w-3.5 h-3.5 text-emerald-500" />
              </div>
              <div className="text-sm font-semibold text-slate-900 mt-1">
                {observations.temperature}°C <span className="text-slate-400 font-normal">/</span> {observations.heart_rate} <span className="text-[10px] font-normal text-slate-400">bpm</span>
              </div>
            </div>
            <div className="mt-2 pt-2 border-t border-slate-100">
              <Badge variant={getStatusSemantic(observations.temperature >= 37.8 ? "deteriorating" : "on_track")} size="sm">
                {observations.temperature >= 37.8 ? "Fever Warning" : "Normal"}
              </Badge>
            </div>
          </Card>
        </div>
      </div>

      {/* Secondary Information Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Active Medications Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Pill className="w-4 h-4 text-teal-600" />
              <span>Current Medications Regimen</span>
            </CardTitle>
            <CardDescription>Prescribed medications and synthetic response index</CardDescription>
          </CardHeader>
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              {medications.current.map((med, idx) => (
                <Badge key={idx} variant="neutral" className="bg-slate-100 text-slate-800">
                  {med}
                </Badge>
              ))}
            </div>
            <div className="text-xs text-slate-600 flex justify-between items-center pt-3 border-t border-slate-100">
              <span className="text-slate-500">Medication Effectiveness Score:</span>
              <span className="font-semibold text-slate-900 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                {medications.response_score} / 10
              </span>
            </div>
          </div>
        </Card>

        {/* Latest Active Recovery Plan Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <TrendingUp className="w-4 h-4 text-teal-600" />
              <span>Latest Recovery Plan</span>
            </CardTitle>
            <CardDescription>
              {activePlan ? `${activePlan.horizon_hours}-Hour Swarm Consensus Plan` : "6–12 Hour Optimization Plan"}
            </CardDescription>
          </CardHeader>

          {/* 3. LOADED PLAN STATE vs 4. NO-PLAN-YET STATE */}
          {activePlan ? (
            <div className="space-y-3 text-xs">
              <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                <span className="flex items-center gap-1.5 text-slate-500">
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  <span>Horizon: {activePlan.horizon_hours} Hours</span>
                </span>
                <Badge variant={getStatusSemantic("allow")}>
                  <ShieldCheck className="w-3 h-3 mr-1 inline" />
                  {activePlan.safety_status}
                </Badge>
              </div>

              {activePlan.steps_target !== null && (
                <div className="flex justify-between items-center bg-slate-50 p-2 rounded border border-slate-200">
                  <span className="font-medium text-slate-700">Mobility Steps Target:</span>
                  <span className="font-bold text-teal-700 text-sm">{activePlan.steps_target.toLocaleString()} steps</span>
                </div>
              )}

              {/* High Priority Actions */}
              {activePlan.high_priority.length > 0 && (
                <div className="space-y-1.5 pt-1">
                  <span className="font-semibold text-slate-900 text-[11px] uppercase tracking-wider block">
                    High Priority Actions
                  </span>
                  {activePlan.high_priority.map((item, idx) => (
                    <div key={idx} className="flex items-start gap-2 bg-slate-50/70 p-2 rounded border border-slate-100">
                      <CheckCircle2 className="w-4 h-4 text-teal-600 shrink-0 mt-0.5" />
                      <div>
                        <div className="font-semibold text-slate-800">{item.action}</div>
                        <div className="text-[11px] text-slate-500 mt-0.5">{item.reason}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Monitoring */}
              {activePlan.monitoring.length > 0 && (
                <div className="pt-2 border-t border-slate-100 text-[11px] text-slate-500 flex items-center justify-between">
                  <span className="font-medium text-slate-700">Monitoring:</span>
                  <span>{activePlan.monitoring.join(", ")}</span>
                </div>
              )}
            </div>
          ) : (
            /* 4. NO PLAN YET STATE (Standardized Empty State Card Pattern) */
            <div className="py-6 px-4 text-center space-y-3 bg-slate-50/50 rounded-lg border border-dashed border-slate-200">
              <FileQuestion className="w-8 h-8 text-slate-400 mx-auto" />
              <div className="space-y-1">
                <h4 className="text-xs font-semibold text-slate-800">No Recovery Plan Generated Yet</h4>
                <p className="text-[11px] text-slate-500 max-w-xs mx-auto">
                  Click "Optimize Recovery" in the Demo Controller above to run the 7-agent swarm cycle and generate a personalized plan.
                </p>
              </div>
              <Button
                variant="primary"
                size="sm"
                icon={<Cpu className="w-3.5 h-3.5" />}
                loading={actionLoading}
                onClick={runOptimizationCycle}
                className="mt-2 text-xs"
              >
                Optimize Recovery
              </Button>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};
