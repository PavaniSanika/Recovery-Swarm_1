import React from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import {
  LayoutDashboard,
  User,
  Users,
  FileText,
  Sliders,
  Stethoscope,
  Activity,
  Building2,
  LogOut,
} from "lucide-react";

export const Sidebar: React.FC = () => {
  const { role, patientId, setPatientId, logout } = useAuth();
  const navigate = useNavigate();

  const pid = patientId || "P001";
  const isHospital = role === "hospital";

  const handleBrandClick = () => {
    if (isHospital) {
      navigate("/hospital");
    } else {
      navigate(`/patient/${pid}/dashboard`);
    }
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <aside className="w-[240px] bg-slate-50 border-r border-slate-200 flex flex-col fixed inset-y-0 left-0 z-30">
      {/* Brand Header */}
      <div
        onClick={handleBrandClick}
        className="h-16 flex items-center gap-3 px-5 border-b border-slate-200 bg-white cursor-pointer hover:bg-slate-50/80 transition-colors"
      >
        <div className="w-8 h-8 rounded-lg bg-teal-600 flex items-center justify-center text-white font-bold text-sm shadow-sm">
          <Activity className="w-5 h-5" />
        </div>
        <div>
          <h1 className="text-sm font-semibold text-slate-900 tracking-tight">RECOVERY-SWARM</h1>
          <p className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">
            {isHospital ? "Hospital Ward Mode" : "Patient Portal"}
          </p>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {isHospital ? (
          <>
            <div className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider px-3 pb-1">
              Hospital Management
            </div>

            {/* Hospital Ward Link */}
            <NavLink
              to="/hospital"
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors duration-150 ${
                  isActive
                    ? "bg-emerald-100 text-emerald-900 font-bold border border-emerald-300"
                    : "text-slate-700 hover:bg-slate-100 hover:text-slate-900 font-semibold"
                }`
              }
            >
              <Building2 className="w-4 h-4 shrink-0 text-emerald-600" />
              <span>Hospital Ward Dashboard</span>
            </NavLink>

            <div className="pt-4 pb-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider px-3">
              Inspect Patient ({pid})
            </div>

            {/* Quick Patient Switcher for Staff */}
            <div className="px-3 pb-2">
              <select
                value={pid}
                onChange={(e) => {
                  const newPid = e.target.value;
                  setPatientId(newPid);
                  navigate(`/patient/${newPid}/dashboard`);
                }}
                className="w-full text-xs bg-white border border-slate-300 rounded p-1.5 text-slate-800 font-medium focus:outline-none focus:ring-1 focus:ring-emerald-500"
              >
                <option value="P001">P001 — Meera Sharma</option>
                <option value="P002">P002 — Rajesh Patel</option>
                <option value="P003">P003 — Anita Desai</option>
                <option value="P004">P004 — David Miller</option>
                <option value="P005">P005 — Sunita Rao</option>
                <option value="P006">P006 — Robert Chen</option>
              </select>
            </div>

            {[
              { to: `/patient/${pid}/dashboard`, label: "Patient Dashboard", icon: LayoutDashboard },
              { to: `/patient/${pid}/twin`, label: "Digital Twin", icon: User },
              { to: `/patient/${pid}/swarm`, label: "Agent Swarm", icon: Users },
              { to: `/patient/${pid}/plan`, label: "Recovery Plan", icon: FileText },
              { to: `/patient/${pid}/whatif`, label: "What-If", icon: Sliders },
              { to: `/patient/${pid}/clinician`, label: "Clinician View", icon: Stethoscope },
            ].map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-colors duration-150 ${
                      isActive
                        ? "bg-teal-50 text-teal-700 font-semibold border border-teal-200/60"
                        : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                    }`
                  }
                >
                  <Icon className="w-3.5 h-3.5 shrink-0" />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </>
        ) : (
          <>
            <div className="text-[10px] font-bold text-teal-700 uppercase tracking-wider px-3 pb-1">
              Patient Portal ({pid})
            </div>

            {[
              { to: `/patient/${pid}/dashboard`, label: "My Recovery Dashboard", icon: LayoutDashboard },
              { to: `/patient/${pid}/twin`, label: "My Digital Twin", icon: User },
              { to: `/patient/${pid}/swarm`, label: "Agent Swarm", icon: Users },
              { to: `/patient/${pid}/plan`, label: "My Recovery Plan", icon: FileText },
              { to: `/patient/${pid}/whatif`, label: "What-If Simulation", icon: Sliders },
              { to: `/patient/${pid}/clinician`, label: "Clinician Support", icon: Stethoscope },
            ].map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors duration-150 ${
                      isActive
                        ? "bg-teal-50 text-teal-700 font-semibold border border-teal-200/60"
                        : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                    }`
                  }
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </>
        )}
      </nav>

      {/* Footer Info & Logout */}
      <div className="p-3 border-t border-slate-200 bg-slate-100/60 space-y-2">
        <div className="text-[11px] text-slate-500 space-y-0.5">
          <div className="font-medium text-slate-700">Role: <span className="capitalize font-bold text-indigo-700">{role || "Guest"}</span></div>
          <div>Synthetic Data Only</div>
        </div>
        <button
          onClick={handleLogout}
          className="w-full flex items-center justify-center gap-2 px-3 py-1.5 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded text-xs font-semibold transition-colors"
        >
          <LogOut className="w-3.5 h-3.5" />
          <span>Log out</span>
        </button>
      </div>
    </aside>
  );
};
