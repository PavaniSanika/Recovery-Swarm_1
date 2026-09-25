import React from "react";
import type { TwinState } from "../../types";
import type { ScreeningFlag, OutlineColor } from "../../types.ext";
import { BODY_DISCLAIMER } from "../../types.ext";
import { twinToBodyParams } from "./bodyMapping";

interface BodyFallback2DProps {
  twin: TwinState;
  simulatedTwin?: TwinState | null;
  flags?: ScreeningFlag[];
  className?: string;
}

const OUTLINE_COLOR_MAP: Record<OutlineColor, { border: string; glow: string; label: string }> = {
  green: { border: "border-emerald-500", glow: "shadow-emerald-500/20", label: "On Track" },
  yellow: { border: "border-amber-400", glow: "shadow-amber-400/20", label: "Slightly Below Expected" },
  orange: { border: "border-orange-500", glow: "shadow-orange-500/20", label: "Below Expected" },
  red: { border: "border-red-600", glow: "shadow-red-600/30", label: "Deteriorating" },
};

export const BodyFallback2D: React.FC<BodyFallback2DProps> = ({
  twin,
  simulatedTwin,
  flags = [],
  className = "",
}) => {
  const params = twinToBodyParams(twin, flags);
  const ghostParams = simulatedTwin ? twinToBodyParams(simulatedTwin, flags) : null;

  const outlineConfig = OUTLINE_COLOR_MAP[params.outline] || OUTLINE_COLOR_MAP.green;

  // Real metric values for legend
  const swellingVal = twin.observations.swelling;
  const painVal = twin.observations.pain;
  const inflamVal = twin.scores.inflammation_score;
  const mobVal = twin.scores.mobility_capacity;

  return (
    <div className={`flex flex-col bg-slate-900/90 text-slate-100 rounded-xl p-4 border ${outlineConfig.border} shadow-lg ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full bg-${params.outline === "yellow" ? "amber" : params.outline === "green" ? "emerald" : params.outline === "orange" ? "orange" : "red"}-500 animate-pulse`} />
          <span className="font-semibold text-sm text-slate-200">2D Body Twin Visualization</span>
          <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
            Simple View
          </span>
        </div>
        <div className="text-xs text-slate-400 font-mono">
          Trajectory: <span className="font-semibold text-slate-200">{outlineConfig.label}</span>
        </div>
      </div>

      {/* Main Body Canvas */}
      <div className="relative flex justify-center items-center py-6 bg-slate-950/60 rounded-lg border border-slate-800/80 min-h-[320px] overflow-hidden">
        {/* Heat Tint Ambient Backdrop */}
        <div
          className="absolute inset-0 pointer-events-none transition-opacity duration-500"
          style={{
            background: `radial-gradient(circle at 55% 65%, rgba(239, 68, 68, ${params.heat * 0.35}) 0%, rgba(245, 158, 11, ${params.heat * 0.15}) 40%, transparent 70%)`,
          }}
        />

        <svg viewBox="0 0 200 360" className="h-72 w-auto drop-shadow-xl z-10 overflow-visible">
          <defs>
            {/* Pulsing animation style */}
            <style>{`
              @keyframes pulseRing {
                0% { r: 6px; opacity: ${params.pain_intensity * 0.9}; }
                50% { r: ${10 * params.knee_scale}px; opacity: ${params.pain_intensity * 0.4}; }
                100% { r: 6px; opacity: ${params.pain_intensity * 0.9}; }
              }
              .pain-pulse {
                animation: pulseRing ${1 / params.pain_hz}s infinite ease-in-out;
              }
            `}</style>
          </defs>

          {/* GHOST BODY (Simulated Twin overlay at 45% opacity) */}
          {ghostParams && (
            <g opacity="0.45" transform="translate(10, 0)">
              {/* Head */}
              <circle cx="90" cy="40" r="18" fill="#64748b" stroke="#94a3b8" strokeWidth="1.5" />
              {/* Torso */}
              <path d="M 72 62 L 108 62 L 102 160 L 78 160 Z" fill="#475569" stroke="#94a3b8" strokeWidth="1.5" />
              {/* Left Leg */}
              <line x1="84" y1="160" x2="80" y2="280" stroke="#64748b" strokeWidth="10" strokeLinecap="round" />
              {/* Right Leg (Simulated Operated) */}
              <g transform="translate(96, 220) scale(1)">
                <circle cx="0" cy="0" r={8 * ghostParams.knee_scale} fill="#f43f5e" opacity="0.6" />
              </g>
              <line x1="96" y1="160" x2="100" y2="280" stroke="#64748b" strokeWidth="10" strokeLinecap="round" />
            </g>
          )}

          {/* PRIMARY BODY */}
          {/* Head */}
          <circle cx="100" cy="40" r="20" fill="#334155" stroke="#64748b" strokeWidth="2" />
          {/* Neck */}
          <rect x="94" y="60" width="12" height="10" fill="#334155" />

          {/* Torso with Heat Tint */}
          <path
            d="M 75 70 L 125 70 L 118 170 L 82 170 Z"
            fill={`rgba(${Math.round(51 + params.heat * 180)}, ${Math.round(65 - params.heat * 40)}, 85, 0.85)`}
            stroke="#64748b"
            strokeWidth="2"
          />

          {/* Left Arm */}
          <line x1="72" y1="75" x2="52" y2="160" stroke="#475569" strokeWidth="10" strokeLinecap="round" />
          {/* Right Arm */}
          <line x1="128" y1="75" x2="148" y2="160" stroke="#475569" strokeWidth="10" strokeLinecap="round" />

          {/* Left Leg (Non-operated) */}
          <line x1="90" y1="170" x2="85" y2="290" stroke="#475569" strokeWidth="12" strokeLinecap="round" />
          <circle cx="87" cy="230" r="7" fill="#64748b" />

          {/* Right Leg (OPERATED RIGHT KNEE) */}
          <line x1="110" y1="170" x2="115" y2="290" stroke="#475569" strokeWidth="12" strokeLinecap="round" />

          {/* OPERATED RIGHT KNEE NODE (scaled by knee_scale) */}
          <g transform="translate(113, 230)">
            {/* Swelling representation */}
            <circle
              cx="0"
              cy="0"
              r={7 * params.knee_scale}
              fill={`rgba(244, 63, 94, ${0.4 + params.pain_intensity * 0.4})`}
              stroke="#f43f5e"
              strokeWidth="2"
            />
            {/* Red Pain Pulse */}
            <circle cx="0" cy="0" className="pain-pulse" fill="#ef4444" />
            <circle cx="0" cy="0" r="3" fill="#ffffff" />
          </g>

          {/* Feet */}
          <ellipse cx="82" cy="295" rx="8" ry="4" fill="#334155" />
          <ellipse cx="118" cy="295" rx="8" ry="4" fill="#334155" />

          {/* Region Markers Overlay */}
          {params.markers.map((marker, idx) => {
            let coords = { x: 100, y: 100 };
            if (marker.region === "knee") coords = { x: 113, y: 230 };
            else if (marker.region === "calf") coords = { x: 115, y: 265 };
            else if (marker.region === "chest") coords = { x: 100, y: 100 };
            else if (marker.region === "legs") coords = { x: 85, y: 265 };

            const isUrgent = marker.severity === "urgent";

            return (
              <g key={idx} transform={`translate(${coords.x}, ${coords.y})`}>
                <circle
                  cx="0"
                  cy="0"
                  r="9"
                  fill={isUrgent ? "#dc2626" : "#f59e0b"}
                  stroke="#ffffff"
                  strokeWidth="1.5"
                />
                <text
                  x="0"
                  y="3"
                  textAnchor="middle"
                  fill="#ffffff"
                  fontSize="8"
                  fontWeight="bold"
                >
                  !
                </text>
              </g>
            );
          })}
        </svg>

        {/* Operated Side Badge */}
        <div className="absolute top-2 right-2 bg-slate-900/90 border border-slate-700/80 px-2.5 py-1 rounded text-[11px] font-medium text-slate-300 flex items-center gap-1.5 shadow-sm">
          <span className="w-2 h-2 rounded-full bg-rose-500" />
          Operated: <strong className="text-slate-100">Right Knee</strong>
        </div>

        {/* Ghost Body Badge (if What-If active) */}
        {ghostParams && (
          <div className="absolute bottom-2 right-2 bg-slate-800/90 border border-slate-600 px-2 py-0.5 rounded text-[10px] text-slate-300">
            Ghost Body: 45% Opacity (Simulated)
          </div>
        )}
      </div>

      {/* Legend showing real metric values */}
      <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
        <div className="bg-slate-950/40 p-2 rounded border border-slate-800">
          <span className="text-slate-400 block text-[10px] uppercase font-semibold">Swelling</span>
          <span className="font-mono text-rose-300 font-bold">{swellingVal.toFixed(1)}</span>
          <span className="text-slate-400 text-[10px] block">knee +{Math.round((params.knee_scale - 1) * 100)}%</span>
        </div>
        <div className="bg-slate-950/40 p-2 rounded border border-slate-800">
          <span className="text-slate-400 block text-[10px] uppercase font-semibold">Pain</span>
          <span className="font-mono text-red-300 font-bold">{painVal.toFixed(1)}</span>
          <span className="text-slate-400 text-[10px] block">{params.pain_hz.toFixed(2)} Hz pulse</span>
        </div>
        <div className="bg-slate-950/40 p-2 rounded border border-slate-800">
          <span className="text-slate-400 block text-[10px] uppercase font-semibold">Inflammation</span>
          <span className="font-mono text-amber-300 font-bold">{inflamVal.toFixed(1)}</span>
          <span className="text-slate-400 text-[10px] block">heat tint {Math.round(params.heat * 100)}%</span>
        </div>
        <div className="bg-slate-950/40 p-2 rounded border border-slate-800">
          <span className="text-slate-400 block text-[10px] uppercase font-semibold">Mobility</span>
          <span className="font-mono text-emerald-300 font-bold">{mobVal.toFixed(1)}</span>
          <span className="text-slate-400 text-[10px] block">walk speed {params.walk_speed.toFixed(2)}</span>
        </div>
      </div>

      {/* REQUIRED DISCLAIMER */}
      <div className="mt-3 pt-2 border-t border-slate-800 text-center">
        <p className="text-[11px] text-slate-400 italic">
          {BODY_DISCLAIMER}
        </p>
      </div>
    </div>
  );
};
