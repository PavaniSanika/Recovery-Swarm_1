import React from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  User,
  Users,
  FileText,
  Sliders,
  Stethoscope,
  Activity,
} from "lucide-react";

export const Sidebar: React.FC = () => {
  const navItems = [
    { to: "/", label: "Dashboard", icon: LayoutDashboard },
    { to: "/twin", label: "Digital Twin", icon: User },
    { to: "/swarm", label: "Agent Swarm", icon: Users },
    { to: "/plan", label: "Recovery Plan", icon: FileText },
    { to: "/whatif", label: "What-If", icon: Sliders },
    { to: "/clinician", label: "Clinician View", icon: Stethoscope },
  ];

  return (
    <aside className="w-[240px] bg-slate-50 border-r border-slate-200 flex flex-col fixed inset-y-0 left-0 z-30">
      {/* Brand Header */}
      <div className="h-16 flex items-center gap-3 px-5 border-b border-slate-200 bg-white">
        <div className="w-8 h-8 rounded-lg bg-teal-600 flex items-center justify-center text-white font-bold text-sm shadow-sm">
          <Activity className="w-5 h-5" />
        </div>
        <div>
          <h1 className="text-sm font-semibold text-slate-900 tracking-tight">RECOVERY-SWARM</h1>
          <p className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">Decision Support</p>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
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
      </nav>

      {/* Footer Info */}
      <div className="p-4 border-t border-slate-200 bg-slate-100/60 text-[11px] text-slate-500 space-y-1">
        <div className="font-medium text-slate-700">Prototype v1.0</div>
        <div>Synthetic Data Only</div>
      </div>
    </aside>
  );
};
