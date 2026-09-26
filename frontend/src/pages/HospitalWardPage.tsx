import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getHospitalPatients } from "../api";
import { HospitalPatientSummary } from "../types.ext";
import { Card, CardHeader, CardTitle, CardDescription } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { getStatusStyle } from "../utils/statusColor";
import { Building2, RefreshCw, ShieldCheck, ArrowRight, User } from "lucide-react";

export const HospitalWardPage: React.FC = () => {
  const [patients, setPatients] = useState<HospitalPatientSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchWardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getHospitalPatients();
      setPatients(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load hospital ward data.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWardData();
  }, []);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 mb-1">
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Hospital Management — Ward Overview</h1>
            <Badge variant="outline" className="border-emerald-300 text-emerald-800 bg-emerald-50 text-xs font-semibold px-2.5 py-0.5">
              Hospital Staff Mode
            </Badge>
          </div>
          <p className="text-xs text-slate-600">
            Centralized triage overview & risk monitoring across all monitored post-operative Total Knee Replacement ward beds.
          </p>
        </div>

        <Button
          onClick={fetchWardData}
          disabled={loading}
          variant="outline"
          className="w-full sm:w-auto shrink-0 flex items-center gap-1.5 text-xs bg-white border-slate-300"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>{loading ? "Refreshing..." : "Refresh Ward Data"}</span>
        </Button>
      </div>

      {/* Honest Labeling Disclaimer */}
      <div className="p-3 bg-slate-100 border border-slate-200 rounded-lg text-xs text-slate-700 flex items-center space-x-2">
        <ShieldCheck className="w-4 h-4 text-slate-500 shrink-0" />
        <span>Ward view: illustrative aggregation of prototype patients. Not a hospital information system.</span>
      </div>

      {/* Main Patients Table */}
      <Card>
        <CardHeader className="border-b border-slate-100 pb-4">
          <CardTitle className="text-base flex items-center gap-2">
            <Building2 className="w-4 h-4 text-emerald-600" />
            <span>Monitored Ward Beds ({patients.length})</span>
          </CardTitle>
          <CardDescription>
            Click any patient row to open their live Digital Twin, Telemetry, and Recovery Plan.
          </CardDescription>
        </CardHeader>

        {error ? (
          <div className="p-6 text-center text-xs text-red-600 bg-red-50/50">
            <p className="font-semibold mb-2">{error}</p>
            <Button size="sm" variant="outline" onClick={fetchWardData}>
              Retry
            </Button>
          </div>
        ) : loading && patients.length === 0 ? (
          <div className="p-8 text-center text-slate-400 animate-pulse text-xs">
            Loading ward patient summaries...
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
                  <th className="p-3.5">Patient ID</th>
                  <th className="p-3.5">Name</th>
                  <th className="p-3.5">Recovery Score</th>
                  <th className="p-3.5">Overall Trajectory</th>
                  <th className="p-3.5">Screening Risk</th>
                  <th className="p-3.5 text-center">Safety Escalation</th>
                  <th className="p-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {patients.map((patient) => {
                  const statusSt = getStatusStyle(patient.trajectory_overall);
                  return (
                    <tr
                      key={patient.patient_id}
                      className="hover:bg-slate-50/80 transition-colors"
                    >
                      <td className="p-3.5 font-mono font-bold text-slate-800">
                        {patient.patient_id}
                      </td>
                      <td className="p-3.5 font-semibold text-slate-900">
                        <div className="flex items-center space-x-2">
                          <div className="w-6 h-6 rounded-full bg-slate-100 text-slate-600 flex items-center justify-center text-[10px]">
                            <User className="w-3 h-3" />
                          </div>
                          <span>{patient.name}</span>
                        </div>
                      </td>
                      <td className="p-3.5 font-mono font-bold text-slate-900">
                        {patient.recovery_score} / 100
                      </td>
                      <td className="p-3.5">
                        <Badge variant="outline" className={statusSt.badge}>
                          {patient.trajectory_overall.replace(/_/g, " ")}
                        </Badge>
                      </td>
                      <td className="p-3.5">
                        {patient.top_screening_severity ? (
                          <Badge
                            variant="outline"
                            className={
                              patient.top_screening_severity === "urgent"
                                ? "border-red-300 text-red-700 bg-red-50 uppercase font-bold"
                                : "border-amber-300 text-amber-700 bg-amber-50 uppercase font-bold"
                            }
                          >
                            {patient.top_screening_severity}
                          </Badge>
                        ) : (
                          <span className="text-slate-400 text-[11px]">Clear</span>
                        )}
                      </td>
                      <td className="p-3.5 text-center">
                        {patient.escalated ? (
                          <Badge variant="outline" className="border-red-300 text-red-800 bg-red-100 font-bold">
                            ESCALATED
                          </Badge>
                        ) : (
                          <span className="text-slate-400 text-[11px]">Normal</span>
                        )}
                      </td>
                      <td className="p-3.5 text-right">
                        <Link to={`/patient/${patient.patient_id}/dashboard`}>
                          <Button size="sm" variant="outline" className="text-[11px] gap-1">
                            <span>Open Dashboard</span>
                            <ArrowRight className="w-3 h-3" />
                          </Button>
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
};
