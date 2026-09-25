import React from "react";
import { useTwin } from "../context/TwinContext";
import { Card, CardHeader, CardTitle, CardDescription } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { getStatusSemantic } from "../utils/statusColor";
import { METRIC_COLORS } from "../utils/metricColors";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import {
  AlertTriangle,
  RefreshCw,
  BarChart2,
  Activity,
  Droplets,
  Footprints,
  Moon,
  FastForward,
  Info,
} from "lucide-react";

export const DigitalTwinPage: React.FC = () => {
  const {
    twin,
    twinReference,
    loading,
    error,
    refreshTwin,
    advanceTime,
    injectScenario,
    actionLoading,
  } = useTwin();

  // 1. LOADING STATE
  if (loading && !twin) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 bg-slate-200 rounded w-1/3"></div>
        <div className="h-24 bg-slate-200 rounded-lg"></div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="h-32 bg-slate-200 rounded-lg"></div>
          <div className="h-32 bg-slate-200 rounded-lg"></div>
          <div className="h-32 bg-slate-200 rounded-lg"></div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="h-64 bg-slate-200 rounded-lg"></div>
          <div className="h-64 bg-slate-200 rounded-lg"></div>
        </div>
      </div>
    );
  }

  // 2. ERROR STATE
  if (error && !twin) {
    return (
      <div className="space-y-4">
        <Card className="border-red-200 bg-red-50/60">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
            <div className="space-y-1 flex-1">
              <h3 className="text-sm font-semibold text-red-900">Failed to load Digital Twin History</h3>
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

  const { profile, observations, trajectory, history } = twin;
  const isDeviating =
    trajectory.overall === "below_expected" ||
    trajectory.overall === "deteriorating" ||
    trajectory.inflammation === "worsening" ||
    observations.pain >= 7.0;

  const hasSufficientHistory = history && history.length >= 2;

  // Transform backend history list into Recharts compatible format
  const chartData = (history || []).map((entry, idx) => {
    const timeLabel = new Date(entry.timestamp).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });

    return {
      time: timeLabel || `t+${idx * 15}m`,
      pain: entry.observations.pain,
      expectedPain: twinReference?.expected_pain ?? 4.0,
      crp: entry.observations.crp,
      inflammationScore: entry.scores.inflammation_score,
      expectedInflammation: twinReference?.expected_inflammation ?? 5.2,
      steps: entry.observations.steps,
      mobilityCapacity: entry.scores.mobility_capacity,
      expectedSteps: twinReference?.expected_steps ?? 2500,
      sleepHours: entry.observations.sleep_hours,
      sleepQuality: entry.scores.sleep_quality,
    };
  });

  return (
    <div className="space-y-6">
      {/* Page Title & Context Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Physiological Digital Twin</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            {profile.name} • {profile.surgery} (Post-Op Day {profile.post_op_day}) • Patient ID: {twin.patient_id}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={getStatusSemantic(trajectory.overall)} dot>
            Trajectory: {trajectory.overall.replace(/_/g, " ")}
          </Badge>
        </div>
      </div>

      {/* 3. DEVIATION / EARLY-WARNING ALERT BANNER (When flagged) */}
      {isDeviating && (
        <Card className="border-amber-200 bg-amber-50/70">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <h3 className="text-sm font-semibold text-amber-900">Recovery Trajectory Deviation Detected</h3>
              <p className="text-xs text-amber-800 leading-relaxed">
                Patient vitals have deviated from expected post-surgical recovery curves (Pain: {observations.pain}/10, CRP Index: {observations.crp}/10, Trajectory: {trajectory.overall.replace(/_/g, " ")}). The Priority Router has dynamically elevated focus agents to evaluate consensus interventions.
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Expected vs Actual Trajectory Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Pain Trajectory */}
        <Card>
          <div className="flex justify-between items-start mb-2">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Pain Trajectory</span>
            <Activity className="w-4 h-4 text-amber-600" />
          </div>
          <div className="flex items-baseline gap-2 my-1">
            <span className="text-2xl font-semibold text-slate-900">{observations.pain}</span>
            <span className="text-xs text-slate-400">vs Expected {twinReference?.expected_pain ?? 4.0}</span>
          </div>
          <div className="text-[11px] text-slate-500 flex justify-between items-center pt-2 border-t border-slate-100 mt-2">
            <span>Reference Curve (Day {profile.post_op_day}):</span>
            <span className="font-medium text-slate-700">{twinReference?.expected_pain ?? 4.0} / 10</span>
          </div>
        </Card>

        {/* Inflammatory Marker Index */}
        <Card>
          <div className="flex justify-between items-start mb-2">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Inflammatory Marker Index</span>
            <Droplets className="w-4 h-4 text-rose-600" />
          </div>
          <div className="flex items-baseline gap-2 my-1">
            <span className="text-2xl font-semibold text-slate-900">{observations.crp}</span>
            <span className="text-xs text-slate-400">vs Expected {twinReference?.expected_inflammation ?? 5.2}</span>
          </div>
          <div className="text-[11px] text-slate-500 flex justify-between items-center pt-2 border-t border-slate-100 mt-2">
            <span>Reference Curve (Day {profile.post_op_day}):</span>
            <span className="font-medium text-slate-700">{twinReference?.expected_inflammation ?? 5.2} / 10</span>
          </div>
        </Card>

        {/* Mobility Target */}
        <Card>
          <div className="flex justify-between items-start mb-2">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Mobility Step Target</span>
            <Footprints className="w-4 h-4 text-blue-600" />
          </div>
          <div className="flex items-baseline gap-2 my-1">
            <span className="text-2xl font-semibold text-slate-900">{observations.steps.toLocaleString()}</span>
            <span className="text-xs text-slate-400">vs Target {twinReference?.expected_steps.toLocaleString() ?? 2500}</span>
          </div>
          <div className="text-[11px] text-slate-500 flex justify-between items-center pt-2 border-t border-slate-100 mt-2">
            <span>Reference Target (Day {profile.post_op_day}):</span>
            <span className="font-medium text-slate-700">{twinReference?.expected_steps.toLocaleString() ?? 2500} steps</span>
          </div>
        </Card>
      </div>

      {/* 4. NOT ENOUGH HISTORY YET STATE vs LOADED TREND CHARTS */}
      {!hasSufficientHistory ? (
        <Card className="py-10 px-6 text-center bg-slate-50/50 border-dashed">
          <div className="max-w-md mx-auto space-y-4">
            <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-500 flex items-center justify-center mx-auto border border-slate-200">
              <BarChart2 className="w-6 h-6 text-slate-600" />
            </div>
            <div className="space-y-1">
              <h3 className="text-base font-semibold text-slate-900">Insufficient History Data for Trend Analysis</h3>
              <p className="text-xs text-slate-500 leading-relaxed">
                At least 2 snapshot data points are required to plot trajectory curves. Click <strong>"Advance 1 Hour"</strong> or inject a scenario in the Demo Controller above to record patient history over time.
              </p>
            </div>
            <div className="flex items-center justify-center gap-3 pt-2">
              <Button
                variant="outline"
                size="sm"
                icon={<FastForward className="w-3.5 h-3.5" />}
                loading={actionLoading}
                onClick={() => advanceTime(60)}
              >
                Advance 1 Hour
              </Button>
              <Button
                variant="secondary"
                size="sm"
                loading={actionLoading}
                onClick={() => injectScenario("pain_spike")}
              >
                Inject Pain Spike
              </Button>
            </div>
          </div>
        </Card>
      ) : (
        /* Recharts Trend Graphs Grid */
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Recorded Trajectory Trends ({history.length} Snapshots)
            </h3>
            <span className="text-[11px] text-slate-400 flex items-center gap-1">
              <Info className="w-3.5 h-3.5" />
              Solid lines = Recorded values • Dashed lines = Sourced expected reference curves
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Chart 1: Pain Level Trajectory */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <Activity className="w-4 h-4 text-amber-600" />
                  <span>Pain Level vs Expected Reference Curve</span>
                </CardTitle>
                <CardDescription>Pain score (0-10) over recorded time points</CardDescription>
              </CardHeader>
              <div className="h-64 w-full pt-2">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                    <XAxis dataKey="time" tick={{ fontSize: 11, fill: "#64748B" }} />
                    <YAxis domain={[0, 10]} tick={{ fontSize: 11, fill: "#64748B" }} />
                    <Tooltip
                      contentStyle={{ backgroundColor: "#FFFFFF", borderRadius: "8px", borderColor: "#E2E8F0", fontSize: "12px" }}
                    />
                    <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }} />
                    <Line
                      type="monotone"
                      dataKey="pain"
                      name="Actual Pain Level"
                      stroke={METRIC_COLORS.pain}
                      strokeWidth={2.5}
                      dot={{ r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="expectedPain"
                      name="Expected Pain Curve"
                      stroke={METRIC_COLORS.expected}
                      strokeWidth={1.5}
                      strokeDasharray="5 5"
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>

            {/* Chart 2: Inflammatory Marker Index (CRP 0-10) */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <Droplets className="w-4 h-4 text-rose-600" />
                  <span>Inflammatory Marker Index (CRP 0-10) vs Expected</span>
                </CardTitle>
                <CardDescription>CRP Index & inflammation score over recorded time points</CardDescription>
              </CardHeader>
              <div className="h-64 w-full pt-2">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                    <XAxis dataKey="time" tick={{ fontSize: 11, fill: "#64748B" }} />
                    <YAxis domain={[0, 10]} tick={{ fontSize: 11, fill: "#64748B" }} />
                    <Tooltip
                      contentStyle={{ backgroundColor: "#FFFFFF", borderRadius: "8px", borderColor: "#E2E8F0", fontSize: "12px" }}
                    />
                    <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }} />
                    <Line
                      type="monotone"
                      dataKey="crp"
                      name="CRP Index (0-10)"
                      stroke={METRIC_COLORS.inflammation}
                      strokeWidth={2.5}
                      dot={{ r: 4 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="expectedInflammation"
                      name="Expected Inflammation Curve"
                      stroke={METRIC_COLORS.expected}
                      strokeWidth={1.5}
                      strokeDasharray="5 5"
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>

            {/* Chart 3: Mobility Capacity & Steps */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <Footprints className="w-4 h-4 text-sky-600" />
                  <span>Mobility Capacity Trend</span>
                </CardTitle>
                <CardDescription>Mobility score (0-10) & step progress</CardDescription>
              </CardHeader>
              <div className="h-64 w-full pt-2">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                    <XAxis dataKey="time" tick={{ fontSize: 11, fill: "#64748B" }} />
                    <YAxis domain={[0, 10]} tick={{ fontSize: 11, fill: "#64748B" }} />
                    <Tooltip
                      contentStyle={{ backgroundColor: "#FFFFFF", borderRadius: "8px", borderColor: "#E2E8F0", fontSize: "12px" }}
                    />
                    <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }} />
                    <Line
                      type="monotone"
                      dataKey="mobilityCapacity"
                      name="Mobility Capacity (0-10)"
                      stroke={METRIC_COLORS.mobility}
                      strokeWidth={2.5}
                      dot={{ r: 4 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>

            {/* Chart 4: Sleep Quality & Duration */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <Moon className="w-4 h-4 text-indigo-600" />
                  <span>Sleep Quality & Duration Trend</span>
                </CardTitle>
                <CardDescription>Sleep quality score & recorded hours</CardDescription>
              </CardHeader>
              <div className="h-64 w-full pt-2">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                    <XAxis dataKey="time" tick={{ fontSize: 11, fill: "#64748B" }} />
                    <YAxis domain={[0, 10]} tick={{ fontSize: 11, fill: "#64748B" }} />
                    <Tooltip
                      contentStyle={{ backgroundColor: "#FFFFFF", borderRadius: "8px", borderColor: "#E2E8F0", fontSize: "12px" }}
                    />
                    <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }} />
                    <Line
                      type="monotone"
                      dataKey="sleepQuality"
                      name="Sleep Quality (0-10)"
                      stroke={METRIC_COLORS.sleep}
                      strokeWidth={2.5}
                      dot={{ r: 4 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="sleepHours"
                      name="Sleep Duration (hrs)"
                      stroke="#8B5CF6"
                      strokeWidth={1.5}
                      strokeDasharray="3 3"
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
};
