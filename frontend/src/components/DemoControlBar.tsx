import React from "react";
import { useNavigate } from "react-router-dom";
import { useTwin } from "../context/TwinContext";
import { Button } from "./ui/Button";
import { Badge } from "./ui/Badge";
import { ScenarioName } from "../types";
import { FastForward, RotateCcw, Sliders, Cpu } from "lucide-react";

export const DemoControlBar: React.FC = () => {
  const {
    injectScenario,
    advanceTime,
    runOptimizationCycle,
    resetPatient,
    simulatorStatus,
    actionLoading,
  } = useTwin();
  const navigate = useNavigate();

  const scenarios: Array<{ id: ScenarioName; label: string }> = [
    { id: "stable_recovery", label: "Stable Recovery" },
    { id: "poor_sleep", label: "Poor Sleep" },
    { id: "pain_spike", label: "Pain Spike" },
    { id: "increased_inflammation", label: "Increased Inflammation" },
    { id: "reduced_mobility", label: "Reduced Mobility" },
    { id: "recovery_deviation", label: "Recovery Deviation" },
  ];

  return (
    <div className="bg-slate-100 border-b border-slate-300 px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs">
      {/* Label & Active Scenario Status Badge */}
      <div className="flex items-center gap-2 text-slate-700 font-semibold uppercase tracking-wider text-[11px] shrink-0">
        <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
        <span>Demo Controller</span>

        {simulatorStatus?.scenario_name && (
          <Badge variant="caution" size="sm" className="font-mono text-[11px] normal-case tracking-normal bg-amber-50 text-amber-800 border-amber-300 ml-1">
            {simulatorStatus.scenario_name} · step {simulatorStatus.step_index}/{simulatorStatus.total_steps} · +{simulatorStatus.minute_offset} min
            {simulatorStatus.total_steps > 0 && simulatorStatus.step_index === simulatorStatus.total_steps ? " (fully advanced)" : ""}
          </Badge>
        )}
      </div>

      {/* Scenario Injection Buttons */}
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-slate-500 font-medium text-[11px] mr-1 hidden sm:inline">Scenarios:</span>
        {scenarios.map((sc) => (
          <Button
            key={sc.id}
            variant="outline"
            size="sm"
            disabled={actionLoading}
            onClick={() => injectScenario(sc.id)}
            className="text-[11px] h-7 px-2.5 bg-white border-slate-300 text-slate-700 hover:bg-slate-50"
          >
            {sc.label}
          </Button>
        ))}
      </div>

      {/* Controls / Actions */}
      <div className="flex items-center gap-1.5 shrink-0">
        <Button
          variant="outline"
          size="sm"
          disabled={actionLoading}
          icon={<FastForward className="w-3.5 h-3.5 text-slate-600" />}
          onClick={() => advanceTime(60)}
          className="text-[11px] h-7 px-2.5 bg-white border-slate-300 text-slate-700 hover:bg-slate-50"
        >
          Advance 1 Hour
        </Button>

        <Button
          variant="primary"
          size="sm"
          disabled={actionLoading}
          loading={actionLoading}
          icon={<Cpu className="w-3.5 h-3.5" />}
          onClick={() => runOptimizationCycle()}
          className="text-[11px] h-7 px-3 bg-teal-600 hover:bg-teal-700 text-white"
        >
          Optimize Recovery
        </Button>

        <Button
          variant="outline"
          size="sm"
          disabled={actionLoading}
          icon={<Sliders className="w-3.5 h-3.5 text-slate-600" />}
          onClick={() => navigate("/whatif")}
          className="text-[11px] h-7 px-2.5 bg-white border-slate-300 text-slate-700 hover:bg-slate-50"
        >
          Run What-If
        </Button>

        <Button
          variant="outline"
          size="sm"
          disabled={actionLoading}
          icon={<RotateCcw className="w-3.5 h-3.5 text-slate-600" />}
          onClick={() => resetPatient()}
          className="text-[11px] h-7 px-2.5 bg-white border-slate-300 text-slate-700 hover:bg-slate-50"
        >
          Reset
        </Button>
      </div>
    </div>
  );
};
