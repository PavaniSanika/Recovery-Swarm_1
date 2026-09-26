// Demo-only role selector for hackathon presentation. Not a real security/authentication system.
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Card, CardTitle, CardDescription } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { User, Building2, Shield, ArrowRight } from "lucide-react";

const SEEDED_PATIENTS = [
  { id: "P001", name: "Meera Sharma", condition: "Day 4 Baseline TKR" },
  { id: "P002", name: "Rajesh Patel", condition: "Pain Spike Scenario" },
  { id: "P003", name: "Anita Desai", condition: "Recovery Deviation" },
  { id: "P004", name: "David Miller", condition: "Increased Inflammation" },
  { id: "P005", name: "Sunita Rao", condition: "Reduced Mobility" },
  { id: "P006", name: "Robert Chen", condition: "Poor Sleep Debt" },
];

export const LoginPage: React.FC = () => {
  const { loginAsPatient, loginAsHospital } = useAuth();
  const navigate = useNavigate();
  const [selectedPatient, setSelectedPatient] = useState("P001");

  const handlePatientLogin = () => {
    loginAsPatient(selectedPatient);
    navigate(`/patient/${selectedPatient}/dashboard`);
  };

  const handleHospitalLogin = () => {
    loginAsHospital();
    navigate("/hospital");
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4 sm:p-6">
      <div className="w-full max-w-3xl space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center space-x-2 bg-indigo-50 border border-indigo-200 text-indigo-700 px-3 py-1 rounded-full text-xs font-semibold">
            <Shield className="w-3.5 h-3.5" />
            <span>Hackathon Demo Mode</span>
          </div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight sm:text-4xl">
            RECOVERY-SWARM
          </h1>
          <p className="text-sm text-slate-600 max-w-md mx-auto">
            Self-Organizing Multi-Agent System around a Physiological Digital Twin for Post-Surgical Recovery.
          </p>
        </div>

        {/* Role Selector Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Patient Role Tile */}
          <Card className="p-6 flex flex-col justify-between hover:shadow-md transition-shadow border-slate-200">
            <div className="space-y-4">
              <div className="w-12 h-12 rounded-xl bg-indigo-100 text-indigo-700 flex items-center justify-center">
                <User className="w-6 h-6" />
              </div>
              <div>
                <CardTitle className="text-lg">Continue as Patient</CardTitle>
                <CardDescription className="text-xs text-slate-500 mt-1">
                  View individual digital twin, recovery score, telemetry trends, and recovery plan.
                </CardDescription>
              </div>

              {/* Patient Selector Dropdown */}
              <div className="space-y-1.5 pt-2">
                <label className="text-xs font-semibold text-slate-700 block">
                  Select Patient Account:
                </label>
                <select
                  value={selectedPatient}
                  onChange={(e) => setSelectedPatient(e.target.value)}
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-slate-800 font-medium focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {SEEDED_PATIENTS.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.id}) — {p.condition}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <Button
              onClick={handlePatientLogin}
              className="mt-6 w-full flex items-center justify-center gap-2"
            >
              <span>Launch Patient Portal</span>
              <ArrowRight className="w-4 h-4" />
            </Button>
          </Card>

          {/* Hospital Staff Role Tile */}
          <Card className="p-6 flex flex-col justify-between hover:shadow-md transition-shadow border-slate-200">
            <div className="space-y-4">
              <div className="w-12 h-12 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center">
                <Building2 className="w-6 h-6" />
              </div>
              <div>
                <CardTitle className="text-lg">Continue as Hospital Staff</CardTitle>
                <CardDescription className="text-xs text-slate-500 mt-1">
                  Access hospital ward dashboard, patient risk triage table, and screening flags.
                </CardDescription>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-600">
                <p>
                  <strong>Ward Overview:</strong> Monitored aggregate view across all 6 post-op TKR ward beds.
                </p>
              </div>
            </div>

            <Button
              onClick={handleHospitalLogin}
              variant="outline"
              className="mt-6 w-full border-emerald-600 text-emerald-700 hover:bg-emerald-50 flex items-center justify-center gap-2"
            >
              <span>Open Hospital Ward</span>
              <ArrowRight className="w-4 h-4" />
            </Button>
          </Card>
        </div>

        {/* Demo Disclaimer */}
        <div className="text-center text-[11px] text-slate-400 max-w-lg mx-auto leading-relaxed">
          Demo-only role selector for hackathon presentation. Not a real security or authentication system. Operating on synthetic patient data only.
        </div>
      </div>
    </div>
  );
};
