import React from "react";
import { Plan, PlanItem } from "../types";
import { Card, CardHeader, CardTitle, CardDescription } from "./ui/Card";
import { Badge } from "./ui/Badge";
import { getStatusStyle } from "../utils/statusColor";

interface PlanDisplayProps {
  plan: Plan;
  titlePrefix?: string;
  isSimulated?: boolean;
}

export const PlanDisplay: React.FC<PlanDisplayProps> = ({
  plan,
  titlePrefix = "Recovery Plan",
  isSimulated = false,
}) => {
  const safetyStyle = getStatusStyle(plan.safety_status || "allow");

  return (
    <div className="space-y-6">
      {/* Plan Header Summary Card */}
      <Card className="p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-slate-100">
          <div>
            <div className="flex items-center space-x-2 mb-1">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                Target Horizon:
              </span>
              <Badge variant="secondary" className="font-mono font-semibold">
                Next {plan.horizon_hours} Hours
              </Badge>
              {isSimulated && (
                <Badge variant="outline" className="border-indigo-200 text-indigo-700 bg-indigo-50 text-[10px]">
                  Simulated Swarm Decision
                </Badge>
              )}
            </div>
            <h2 className="text-xl font-bold text-slate-900">
              {titlePrefix} ({plan.horizon_hours}h Horizon)
            </h2>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="text-right">
              <span className="text-[11px] text-slate-500 block">Safety Status</span>
              <Badge variant="outline" className={safetyStyle.badge}>
                {plan.safety_status || "No safety rules triggered"}
              </Badge>
            </div>

            <div className="text-right border-l border-slate-200 pl-3">
              <span className="text-[11px] text-slate-500 block">Next Reassessment</span>
              <span className="text-xs font-semibold text-slate-900">
                {plan.next_reassessment}
              </span>
            </div>
          </div>
        </div>

        {/* Expected Score Change (if available) */}
        {plan.expected_score_change && (
          <div className="mt-4 pt-3 flex items-center justify-between text-xs text-slate-600">
            <span>Expected Prototype Score Impact:</span>
            <span className="font-semibold text-slate-900 bg-slate-100 px-2 py-0.5 rounded">
              {plan.expected_score_change}
            </span>
          </div>
        )}

        {/* Plan Explanation Banner */}
        <div className="mt-4 bg-slate-50 p-4 rounded-lg border border-slate-100">
          <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
            Swarm Decision Explanation
          </span>
          <p className="text-xs text-slate-700 leading-relaxed italic">
            "{plan.explanation}"
          </p>
        </div>
      </Card>

      {/* High-Priority Actions Grid/List */}
      <div className="space-y-3">
        <div className="flex items-center space-x-2">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
          <h2 className="text-base font-semibold text-slate-900 uppercase tracking-wide">
            High Priority Actions ({plan.high_priority.length})
          </h2>
        </div>

        {plan.high_priority.length > 0 ? (
          <div className="grid grid-cols-1 gap-3">
            {plan.high_priority.map((item: PlanItem, idx: number) => (
              <Card
                key={idx}
                className="p-5 border-l-4 border-l-amber-500 bg-amber-50/30 hover:bg-amber-50/50 transition-colors"
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div className="space-y-1 flex-1">
                    <div className="flex items-center space-x-2">
                      <Badge variant="warning" className="uppercase text-[10px] tracking-wider">
                        High Priority
                      </Badge>
                      <h3 className="text-sm font-bold text-slate-900">{item.action}</h3>
                    </div>
                    <p className="text-xs text-slate-700 leading-relaxed">{item.reason}</p>
                  </div>

                  {item.target && (
                    <div className="shrink-0 bg-white px-3 py-1.5 rounded-md border border-amber-200 shadow-sm text-right">
                      <span className="text-[10px] text-slate-500 block uppercase tracking-wider font-semibold">
                        Swarm's Recommended Next Target
                      </span>
                      <span className="text-xs font-mono font-bold text-slate-900">
                        {item.target}
                      </span>
                    </div>
                  )}
                </div>
              </Card>
            ))}
          </div>
        ) : (
          <Card className="p-4 text-xs text-slate-500 italic bg-slate-50">
            No high priority actions designated for this period.
          </Card>
        )}
      </div>

      {/* Medium-Priority Actions List */}
      <div className="space-y-3">
        <div className="flex items-center space-x-2">
          <span className="w-2.5 h-2.5 rounded-full bg-slate-400" />
          <h2 className="text-base font-semibold text-slate-900 uppercase tracking-wide">
            Medium Priority Actions ({plan.medium_priority.length})
          </h2>
        </div>

        {plan.medium_priority.length > 0 ? (
          <div className="grid grid-cols-1 gap-3">
            {plan.medium_priority.map((item: PlanItem, idx: number) => (
              <Card
                key={idx}
                className="p-4 border-l-4 border-l-slate-400 bg-slate-50/60"
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div className="space-y-1 flex-1">
                    <div className="flex items-center space-x-2">
                      <Badge variant="secondary" className="uppercase text-[10px] tracking-wider">
                        Medium Priority
                      </Badge>
                      <h3 className="text-sm font-semibold text-slate-900">{item.action}</h3>
                    </div>
                    <p className="text-xs text-slate-600">{item.reason}</p>
                  </div>

                  {item.target && (
                    <div className="shrink-0 bg-white px-3 py-1 rounded border border-slate-200 text-right">
                      <span className="text-[10px] text-slate-400 block uppercase tracking-wider font-semibold">
                        Swarm's Recommended Next Target
                      </span>
                      <span className="text-xs font-mono font-semibold text-slate-800">
                        {item.target}
                      </span>
                    </div>
                  )}
                </div>
              </Card>
            ))}
          </div>
        ) : (
          <Card className="p-4 text-xs text-slate-500 italic bg-slate-50">
            No medium priority actions designated for this period.
          </Card>
        )}
      </div>

      {/* Monitoring Instructions */}
      <Card>
        <CardHeader className="border-b border-slate-100 pb-3">
          <CardTitle className="text-base">Continuous Monitoring Instructions</CardTitle>
          <CardDescription>
            Clinical parameters and telemetry signals to observe during the next recovery cycle.
          </CardDescription>
        </CardHeader>
        <div className="p-4">
          {plan.monitoring && plan.monitoring.length > 0 ? (
            <ul className="space-y-2 text-xs text-slate-700">
              {plan.monitoring.map((mItem, idx) => (
                <li key={idx} className="flex items-start space-x-2">
                  <span className="text-amber-500 font-bold mt-0.5">•</span>
                  <span className="flex-1">{mItem}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-slate-500 italic">
              Standard telemetry monitoring continues.
            </p>
          )}
        </div>
      </Card>
    </div>
  );
};
