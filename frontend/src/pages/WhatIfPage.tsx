import React, { useState } from "react";
import { useTwin } from "../context/TwinContext";
import { postWhatIf } from "../api";
import { WhatIfResponse } from "../types";
import { BodyTwin3D } from "../components/body/BodyTwin3D";
import { Card, CardHeader, CardTitle, CardDescription } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { PlanDisplay } from "../components/PlanDisplay";
import { getStatusStyle } from "../utils/statusColor";
import { METRIC_COLORS } from "../utils/metricColors";
import {
  Sliders,
  Play,
  RotateCcw,
  AlertTriangle,
  HelpCircle,
  ShieldAlert,
} from "lucide-react";

export const WhatIfPage: React.FC = () => {
  const { twin, patientId } = useTwin();

  // Input states
  const [stepsPct, setStepsPct] = useState<number>(20);
  const [overridePain, setOverridePain] = useState<string>("");
  const [overrideSleep, setOverrideSleep] = useState<string>("");
  const [overrideSwelling, setOverrideSwelling] = useState<string>("");

  // Simulation run state
  const [result, setResult] = useState<WhatIfResponse | null>(null);
  const [simulating, setSimulating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleRunSimulation = async (pctValue?: number) => {
    const targetPct = pctValue !== undefined ? pctValue : stepsPct;
    setSimulating(true);
    setError(null);

    const changes: Record<string, number> = {
      steps_pct: targetPct,
    };

    if (overridePain !== "" && !isNaN(parseFloat(overridePain))) {
      changes.pain = parseFloat(overridePain);
    }
    if (overrideSleep !== "" && !isNaN(parseFloat(overrideSleep))) {
      changes.sleep_hours = parseFloat(overrideSleep);
    }
    if (overrideSwelling !== "" && !isNaN(parseFloat(overrideSwelling))) {
      changes.swelling = parseFloat(overrideSwelling);
    }

    try {
      const res = await postWhatIf(patientId || "P001", { changes });
      setResult(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Simulation request failed.";
      setError(msg);
    } finally {
      setSimulating(false);
    }
  };

  const handleResetInputs = () => {
    setStepsPct(20);
    setOverridePain("");
    setOverrideSleep("");
    setOverrideSwelling("");
    setResult(null);
    setError(null);
  };

  // Safely extract comparison parameters if result is available
  const curPain = result?.comparison?.current?.pain ?? 0;
  const simPain = result?.comparison?.simulated?.pain ?? 0;
  const curSwelling = result?.comparison?.current?.swelling ?? 0;
  const simSwelling = result?.comparison?.simulated?.swelling ?? 0;
  const curSleep = result?.comparison?.current?.sleep_hours ?? 0;
  const simSleep = result?.comparison?.simulated?.sleep_hours ?? 0;
  const curSteps = result?.comparison?.current?.steps ?? 0;
  const simSteps = result?.comparison?.simulated?.steps ?? 0;
  const curScore = result?.comparison?.current?.recovery_score ?? 0;
  const simScore = result?.comparison?.simulated?.recovery_score ?? 0;

  return (
    <div className="space-y-6">
      {/* Header & Section Title */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 mb-1">
            <h1 className="text-2xl font-semibold text-slate-900">What-If Simulation</h1>
            <Badge variant="outline" className="border-indigo-200 text-indigo-700 bg-indigo-50 text-[10px]">
              Sandbox Engine
            </Badge>
          </div>
          <p className="text-xs text-slate-500">
            Simulate parameter adjustments on a Digital Twin clone without altering live patient state.
          </p>
        </div>

        {result && (
          <Button
            variant="outline"
            size="sm"
            onClick={handleResetInputs}
            disabled={simulating}
            className="w-full sm:w-auto text-xs"
          >
            <RotateCcw className="w-3.5 h-3.5 mr-1" />
            Reset Sandbox
          </Button>
        )}
      </div>

      {/* Mandatory Honest-Labeling Disclaimer Banner */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-900 flex items-start space-x-2">
        <HelpCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <strong className="font-semibold block text-amber-950">Prototype Simulation Disclaimer:</strong>
          <p className="text-amber-800 leading-normal">
            Illustrative simulation only. Results are based on prototype assumptions and synthetic data and are not clinical predictions.
          </p>
        </div>
      </div>

      {/* 3D Body Twin Sandbox Panel (Ghost body overlay rendered when simulatedTwin is available).
          Pass empty array for flags argument until Stage H1/H4 screening data is wired */}
      {twin && (
        <BodyTwin3D
          twin={twin}
          simulatedTwin={result?.simulated_twin || null}
          flags={[]}
          className="mb-6"
        />
      )}

      {/* Simulation Controls Input Card */}
      <Card className="p-6">
        <CardHeader className="p-0 pb-4 border-b border-slate-100">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center space-x-2">
              <Sliders className="w-4 h-4 text-indigo-600" />
              <span>Simulation Controls & Scenario Inputs</span>
            </CardTitle>
            <span className="text-xs text-slate-400 font-mono">Patient: P001 (Meera)</span>
          </div>
          <CardDescription>
            Adjust mobility steps percentage or directly override telemetry values for counterfactual analysis.
          </CardDescription>
        </CardHeader>

        <div className="pt-5 space-y-6">
          {/* Main Controls: Steps Percentage Slider */}
          <div className="space-y-3 bg-slate-50/80 p-4 rounded-lg border border-slate-200">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-slate-800 uppercase tracking-wide">
                Mobility Steps Adjustment (% change)
              </label>
              <span className="text-sm font-mono font-bold text-indigo-700 bg-indigo-50 px-2.5 py-0.5 rounded border border-indigo-200">
                {stepsPct > 0 ? `+${stepsPct}%` : `${stepsPct}%`}
              </span>
            </div>

            <input
              type="range"
              min="-50"
              max="50"
              step="5"
              value={stepsPct}
              onChange={(e) => setStepsPct(parseInt(e.target.value, 10))}
              className="w-full accent-indigo-600 h-2 bg-slate-200 rounded-lg cursor-pointer"
            />

            <div className="flex justify-between text-[11px] text-slate-500 font-mono pt-1">
              <span>-50% (Rest)</span>
              <span>0% (Maintain)</span>
              <span>+20% (Target)</span>
              <span>+50% (High Activity)</span>
            </div>

            {/* Quick Presets */}
            <div className="flex items-center gap-2 pt-2 border-t border-slate-200/60">
              <span className="text-[11px] text-slate-500 font-medium">Quick Presets:</span>
              {[-20, 0, 20, 30].map((preset) => (
                <Button
                  key={preset}
                  variant={stepsPct === preset ? "primary" : "outline"}
                  size="sm"
                  onClick={() => {
                    setStepsPct(preset);
                    handleRunSimulation(preset);
                  }}
                  disabled={simulating}
                  className="h-7 text-xs py-0 px-2.5"
                >
                  {preset > 0 ? `+${preset}%` : `${preset}%`}
                </Button>
              ))}
            </div>
          </div>

          {/* Optional Direct Parameter Override Collapsible/Grid */}
          <div className="space-y-2">
            <span className="text-xs font-semibold text-slate-700 block">
              Optional Direct Parameter Overrides (Leave empty to use effect model derivation)
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div className="space-y-1">
                <label className="text-[11px] text-slate-500 font-medium">Pain Score (0–10)</label>
                <input
                  type="number"
                  min="0"
                  max="10"
                  step="0.5"
                  placeholder={`Current: ${twin?.observations.pain.toFixed(1) ?? "6.0"}`}
                  value={overridePain}
                  onChange={(e) => setOverridePain(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-md border border-slate-300 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[11px] text-slate-500 font-medium">Sleep Hours (0–14)</label>
                <input
                  type="number"
                  min="0"
                  max="14"
                  step="0.5"
                  placeholder={`Current: ${twin?.observations.sleep_hours.toFixed(1) ?? "4.5"}`}
                  value={overrideSleep}
                  onChange={(e) => setOverrideSleep(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-md border border-slate-300 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[11px] text-slate-500 font-medium">Swelling Index (0–10)</label>
                <input
                  type="number"
                  min="0"
                  max="10"
                  step="0.5"
                  placeholder={`Current: ${twin?.observations.swelling.toFixed(1) ?? "6.0"}`}
                  value={overrideSwelling}
                  onChange={(e) => setOverrideSwelling(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-md border border-slate-300 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>
            </div>
          </div>

          {/* Action Button */}
          <div className="pt-2 flex items-center justify-end">
            <Button
              onClick={() => handleRunSimulation()}
              disabled={simulating}
              className="w-full sm:w-auto px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs shadow-sm"
            >
              {simulating ? (
                <>Simulating Swarm Response...</>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 mr-1.5 fill-current" />
                  Run What-If Simulation
                </>
              )}
            </Button>
          </div>
        </div>
      </Card>

      {/* STATE 1: LOADING STATE */}
      {simulating && (
        <Card className="p-8 text-center space-y-4 animate-pulse">
          <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto" />
          <div>
            <h3 className="text-sm font-semibold text-slate-800">Invoking Swarm on Twin Clone</h3>
            <p className="text-xs text-slate-500 mt-1">
              Applying physiological effect formulas and executing agent debate cycle...
            </p>
          </div>
        </Card>
      )}

      {/* STATE 2: ERROR STATE */}
      {error && !simulating && (
        <Card className="p-5 border-red-200 bg-red-50/60">
          <div className="flex items-start space-x-3">
            <AlertTriangle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
            <div className="space-y-1 flex-1">
              <h3 className="text-xs font-bold text-red-900 uppercase tracking-wide">
                Simulation Execution Failure
              </h3>
              <p className="text-xs text-red-700">{error}</p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleRunSimulation()}
              className="border-red-300 text-red-700 hover:bg-red-100 text-xs shrink-0"
            >
              Retry Simulation
            </Button>
          </div>
        </Card>
      )}

      {/* STATE 3: NOT YET RUN (EMPTY STATE) */}
      {!result && !simulating && !error && (
        <Card className="p-8 text-center bg-slate-50/50 border-dashed border-2 border-slate-300">
          <div className="w-12 h-12 rounded-full bg-indigo-50 border border-indigo-100 flex items-center justify-center mx-auto mb-3">
            <Sliders className="w-6 h-6 text-indigo-600" />
          </div>
          <h3 className="text-sm font-semibold text-slate-800 mb-1">
            No Active What-If Simulation Results
          </h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto mb-5 leading-relaxed">
            Select a step modification percentage or parameter overrides above and click "Run What-If Simulation" to project physiological effects and view the swarm's simulated recovery plan.
          </p>
          <Button
            onClick={() => handleRunSimulation()}
            className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs"
          >
            <Play className="w-3.5 h-3.5 mr-1.5 fill-current" />
            Run Baseline +20% Steps Simulation
          </Button>
        </Card>
      )}

      {/* STATE 4: LOADED WITH RESULTS */}
      {result && !simulating && (
        <div className="space-y-6">
          {/* Side-by-Side Telemetry & Score Comparison Card */}
          <Card className="p-6">
            <CardHeader className="p-0 pb-4 border-b border-slate-100">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <CardTitle className="text-base">Current State vs. Simulated State Comparison</CardTitle>
                  <CardDescription>
                    Direct counterfactual evaluation of physiological signals and recovery score.
                  </CardDescription>
                </div>

                <Badge
                  variant="outline"
                  className={getStatusStyle(result.safety.result).badge}
                >
                  Safety Guardian: {result.safety.result.toUpperCase()}
                </Badge>
              </div>
            </CardHeader>

            {/* Comparison Grid */}
            <div className="pt-5 grid grid-cols-1 md:grid-cols-5 gap-3 text-xs">
              {/* Pain */}
              <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-100 space-y-2">
                <span className="text-[11px] text-slate-500 font-semibold block">Pain Score</span>
                <div className="flex items-baseline justify-between">
                  <div>
                    <span className="text-xs text-slate-400 block">Current</span>
                    <span className="text-sm font-bold font-mono text-slate-700">
                      {curPain.toFixed(1)}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-xs text-slate-400 block">Simulated</span>
                    <span className="text-sm font-bold font-mono" style={{ color: METRIC_COLORS.pain }}>
                      {simPain.toFixed(1)}
                    </span>
                  </div>
                </div>
                <div className="text-[10px] font-mono text-slate-500 pt-1 border-t border-slate-200/60 flex justify-between">
                  <span>Effect:</span>
                  <span className="font-semibold text-slate-800">{result.effects.pain}</span>
                </div>
              </div>

              {/* Swelling */}
              <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-100 space-y-2">
                <span className="text-[11px] text-slate-500 font-semibold block">Swelling Score</span>
                <div className="flex items-baseline justify-between">
                  <div>
                    <span className="text-xs text-slate-400 block">Current</span>
                    <span className="text-sm font-bold font-mono text-slate-700">
                      {curSwelling.toFixed(1)}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-xs text-slate-400 block">Simulated</span>
                    <span className="text-sm font-bold font-mono text-slate-900">
                      {simSwelling.toFixed(1)}
                    </span>
                  </div>
                </div>
                <div className="text-[10px] font-mono text-slate-500 pt-1 border-t border-slate-200/60 flex justify-between">
                  <span>Effect:</span>
                  <span className="font-semibold text-slate-800">{result.effects.swelling}</span>
                </div>
              </div>

              {/* Sleep Hours */}
              <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-100 space-y-2">
                <span className="text-[11px] text-slate-500 font-semibold block">Sleep Hours</span>
                <div className="flex items-baseline justify-between">
                  <div>
                    <span className="text-xs text-slate-400 block">Current</span>
                    <span className="text-sm font-bold font-mono text-slate-700">
                      {curSleep.toFixed(1)}h
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-xs text-slate-400 block">Simulated</span>
                    <span className="text-sm font-bold font-mono" style={{ color: METRIC_COLORS.sleep }}>
                      {simSleep.toFixed(1)}h
                    </span>
                  </div>
                </div>
                <div className="text-[10px] font-mono text-slate-500 pt-1 border-t border-slate-200/60 flex justify-between">
                  <span>Effect:</span>
                  <span className="font-semibold text-slate-800">{result.effects.sleep_hours}</span>
                </div>
              </div>

              {/* Steps */}
              <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-100 space-y-2">
                <span className="text-[11px] text-slate-500 font-semibold block">Telemetry: Observed Steps</span>
                <div className="flex items-baseline justify-between">
                  <div>
                    <span className="text-xs text-slate-400 block">Current</span>
                    <span className="text-sm font-bold font-mono text-slate-700">
                      {curSteps}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-xs text-slate-400 block">Simulated Obs.</span>
                    <span className="text-sm font-bold font-mono" style={{ color: METRIC_COLORS.mobility }}>
                      {simSteps}
                    </span>
                  </div>
                </div>
                <div className="text-[10px] font-mono text-slate-500 pt-1 border-t border-slate-200/60 flex justify-between">
                  <span>Delta:</span>
                  <span className="font-semibold text-slate-800">{result.effects.steps}</span>
                </div>
              </div>

              {/* Recovery Score */}
              <div className="p-3.5 rounded-lg bg-indigo-50/60 border border-indigo-100 space-y-2">
                <span className="text-[11px] text-indigo-900 font-bold block">Recovery Score</span>
                <div className="flex items-baseline justify-between">
                  <div>
                    <span className="text-xs text-indigo-400 block">Current</span>
                    <span className="text-sm font-bold font-mono text-slate-700">
                      {curScore}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-xs text-indigo-400 block">Simulated</span>
                    <span className="text-base font-extrabold font-mono text-indigo-950">
                      {simScore} / 100
                    </span>
                  </div>
                </div>
                <div className="text-[10px] font-mono text-indigo-800 pt-1 border-t border-indigo-200/60 flex justify-between">
                  <span>Delta:</span>
                  <span className="font-semibold">
                    {simScore - curScore > 0 ? `+${simScore - curScore}` : simScore - curScore} pts
                  </span>
                </div>
              </div>
            </div>

            {/* Safety Guardian Rules Triggered Banner */}
            {result.safety.rules_triggered && result.safety.rules_triggered.length > 0 && (
              <div className="mt-4 p-3 rounded-lg bg-orange-50 border border-orange-200 text-xs space-y-1">
                <div className="flex items-center space-x-2 text-orange-900 font-bold uppercase tracking-wide text-[11px]">
                  <ShieldAlert className="w-4 h-4 text-orange-600" />
                  <span>Safety Guardian Rules Triggered in Simulation</span>
                </div>
                <div className="space-y-1 pt-1">
                  {result.safety.rules_triggered.map((rule, idx) => (
                    <div key={idx} className="text-orange-800 flex items-center justify-between font-mono text-[11px]">
                      <span>Rule {rule.rule_id}: {rule.detail}</span>
                      <Badge variant="outline" className="bg-white border-orange-300 text-orange-900">
                        {rule.outcome}
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Card>

          {/* Simulated Plan View (if present) */}
          {result.simulated_plan ? (
            <PlanDisplay plan={result.simulated_plan} titlePrefix="Simulated Recovery Plan" isSimulated={true} />
          ) : (
            <Card className="p-5 bg-red-50 border-red-200 text-xs text-red-800">
              <span className="font-bold block uppercase tracking-wide mb-1">No Safe Plan Generated</span>
              <p>
                Safety Guardian escalated the simulation due to safety constraint violations. Activity progression suspended.
              </p>
            </Card>
          )}
        </div>
      )}
    </div>
  );
};
