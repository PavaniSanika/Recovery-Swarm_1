import React, { useState, useEffect, useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Html } from "@react-three/drei";
import * as THREE from "three";
import type { TwinState } from "../../types";
import type { ScreeningFlag, BodyParams } from "../../types.ext";
import { BODY_DISCLAIMER } from "../../types.ext";
import { twinToBodyParams } from "./bodyMapping";
import { BodyFallback2D } from "./BodyFallback2D";

interface BodyTwin3DProps {
  twin: TwinState;
  simulatedTwin?: TwinState | null;
  flags?: ScreeningFlag[];
  className?: string;
}

const OUTLINE_HEX_MAP: Record<string, string> = {
  green: "#10b981",
  yellow: "#f59e0b",
  orange: "#f97316",
  red: "#ef4444",
};

// Check WebGL availability
function isWebGLAvailable(): boolean {
  try {
    const canvas = document.createElement("canvas");
    return !!(
      window.WebGLRenderingContext &&
      (canvas.getContext("webgl") || canvas.getContext("experimental-webgl"))
    );
  } catch (e) {
    return false;
  }
}

// Single Mannequin 3D Mesh Component
interface MannequinProps {
  params: BodyParams;
  isGhost?: boolean;
}

const Mannequin: React.FC<MannequinProps> = ({ params, isGhost = false }) => {
  const leftLegRef = useRef<THREE.Group>(null);
  const rightLegRef = useRef<THREE.Group>(null);
  const leftArmRef = useRef<THREE.Group>(null);
  const rightArmRef = useRef<THREE.Group>(null);
  const pulseRef = useRef<THREE.Mesh>(null);

  const opacity = isGhost ? 0.45 : 1.0;
  const transparent = isGhost;

  // Heat color interpolation
  const heatColor = useMemo(() => {
    const base = new THREE.Color("#475569");
    const heatTint = new THREE.Color("#ef4444");
    return base.clone().lerp(heatTint, params.heat * 0.7);
  }, [params.heat]);

  const outlineColor = OUTLINE_HEX_MAP[params.outline] || "#10b981";

  // Animation Loop for Walking & Pain Pulse
  useFrame(({ clock }) => {
    const time = clock.getElapsedTime();

    // Walking animation if walk_speed > 0
    if (params.walk_speed > 0) {
      const angle = Math.sin(time * params.walk_speed * 4) * 0.4;
      if (leftLegRef.current) leftLegRef.current.rotation.x = angle;
      if (rightLegRef.current) rightLegRef.current.rotation.x = -angle;
      if (leftArmRef.current) leftArmRef.current.rotation.x = -angle * 0.7;
      if (rightArmRef.current) rightArmRef.current.rotation.x = angle * 0.7;
    }

    // Pain Pulse animation
    if (pulseRef.current) {
      const pulsePhase = (Math.sin(time * params.pain_hz * Math.PI * 2) + 1) / 2;
      const scale = (0.2 + pulsePhase * 0.15 * params.pain_intensity) * params.knee_scale;
      pulseRef.current.scale.set(scale, scale, scale);
      if (pulseRef.current.material) {
        (pulseRef.current.material as THREE.MeshStandardMaterial).opacity =
          (0.4 + pulsePhase * 0.5 * params.pain_intensity) * opacity;
      }
    }
  });

  return (
    <group position={isGhost ? [0.6, 0, 0] : [0, 0, 0]}>
      {/* Trajectory Base Ring */}
      <mesh position={[0, -1.9, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.9, 1.05, 32]} />
        <meshBasicMaterial color={outlineColor} opacity={opacity * 0.8} transparent />
      </mesh>

      {/* Head */}
      <mesh position={[0, 1.6, 0]}>
        <sphereGeometry args={[0.24, 16, 16]} />
        <meshStandardMaterial color="#64748b" opacity={opacity} transparent={transparent} />
      </mesh>

      {/* Neck */}
      <mesh position={[0, 1.3, 0]}>
        <cylinderGeometry args={[0.08, 0.09, 0.15, 12]} />
        <meshStandardMaterial color="#475569" opacity={opacity} transparent={transparent} />
      </mesh>

      {/* Torso (with Heat Tint) */}
      <mesh position={[0, 0.75, 0]}>
        <cylinderGeometry args={[0.3, 0.22, 0.95, 16]} />
        <meshStandardMaterial color={heatColor} opacity={opacity} transparent={transparent} />
      </mesh>

      {/* Hips */}
      <mesh position={[0, 0.2, 0]}>
        <sphereGeometry args={[0.24, 16, 16]} />
        <meshStandardMaterial color="#334155" opacity={opacity} transparent={transparent} />
      </mesh>

      {/* Left Arm */}
      <group ref={leftArmRef} position={[-0.38, 1.1, 0]}>
        <mesh position={[0, -0.4, 0]}>
          <capsuleGeometry args={[0.06, 0.6, 8, 8]} />
          <meshStandardMaterial color="#475569" opacity={opacity} transparent={transparent} />
        </mesh>
      </group>

      {/* Right Arm */}
      <group ref={rightArmRef} position={[0.38, 1.1, 0]}>
        <mesh position={[0, -0.4, 0]}>
          <capsuleGeometry args={[0.06, 0.6, 8, 8]} />
          <meshStandardMaterial color="#475569" opacity={opacity} transparent={transparent} />
        </mesh>
      </group>

      {/* Left Leg (Non-Operated) */}
      <group ref={leftLegRef} position={[-0.16, 0.1, 0]}>
        <mesh position={[0, -0.9, 0]}>
          <capsuleGeometry args={[0.08, 1.3, 8, 8]} />
          <meshStandardMaterial color="#475569" opacity={opacity} transparent={transparent} />
        </mesh>
      </group>

      {/* Right Leg (OPERATED RIGHT KNEE) */}
      <group ref={rightLegRef} position={[0.16, 0.1, 0]}>
        {/* Upper Thigh */}
        <mesh position={[0, -0.4, 0]}>
          <capsuleGeometry args={[0.08, 0.5, 8, 8]} />
          <meshStandardMaterial color="#475569" opacity={opacity} transparent={transparent} />
        </mesh>

        {/* OPERATED RIGHT KNEE (Scaled by knee_scale) */}
        <mesh position={[0, -0.75, 0]} scale={[params.knee_scale, params.knee_scale, params.knee_scale]}>
          <sphereGeometry args={[0.11, 16, 16]} />
          <meshStandardMaterial color="#f43f5e" opacity={opacity} transparent={transparent} />
        </mesh>

        {/* Red Pain Pulse Sphere */}
        {!isGhost && (
          <mesh ref={pulseRef} position={[0, -0.75, 0]}>
            <sphereGeometry args={[1, 16, 16]} />
            <meshStandardMaterial color="#ef4444" transparent />
          </mesh>
        )}

        {/* Lower Leg & Calf */}
        <mesh position={[0, -1.2, 0]}>
          <capsuleGeometry args={[0.075, 0.5, 8, 8]} />
          <meshStandardMaterial color="#475569" opacity={opacity} transparent={transparent} />
        </mesh>
      </group>

      {/* Region Markers (Drei HTML Popups on 3D Body) */}
      {!isGhost &&
        params.markers.map((marker, idx) => {
          let pos: [number, number, number] = [0.16, -0.65, 0.15]; // Knee
          if (marker.region === "calf") pos = [0.16, -1.2, 0.15];
          else if (marker.region === "chest") pos = [0, 0.8, 0.35];
          else if (marker.region === "legs") pos = [-0.16, -1.2, 0.15];

          const isUrgent = marker.severity === "urgent";

          return (
            <group key={idx} position={pos}>
              <Html distanceFactor={8} center>
                <div
                  className={`px-1.5 py-0.5 rounded-full text-[9px] font-bold text-white flex items-center gap-1 shadow-md border ${
                    isUrgent ? "bg-red-600 border-red-400" : "bg-amber-500 border-amber-300"
                  }`}
                >
                  <span>!</span>
                  <span>{marker.flag_id}</span>
                </div>
              </Html>
            </group>
          );
        })}
    </group>
  );
};

export const BodyTwin3D: React.FC<BodyTwin3DProps> = ({
  twin,
  simulatedTwin,
  flags = [],
  className = "",
}) => {
  const [webglSupported, setWebglSupported] = useState<boolean>(true);
  const [simpleView, setSimpleView] = useState<boolean>(false);

  useEffect(() => {
    setWebglSupported(isWebGLAvailable());
  }, []);

  const params = useMemo(() => twinToBodyParams(twin, flags), [twin, flags]);
  const ghostParams = useMemo(
    () => (simulatedTwin ? twinToBodyParams(simulatedTwin, flags) : null),
    [simulatedTwin, flags]
  );

  // Fallback to 2D SVG if WebGL unavailable or user toggles simple view
  if (!webglSupported || simpleView) {
    return (
      <div className="relative">
        <BodyFallback2D
          twin={twin}
          simulatedTwin={simulatedTwin}
          flags={flags}
          className={className}
        />
        {webglSupported && (
          <button
            onClick={() => setSimpleView(false)}
            className="absolute top-4 right-4 bg-indigo-600 hover:bg-indigo-500 text-white text-xs px-2.5 py-1 rounded font-medium shadow"
          >
            Switch to 3D View
          </button>
        )}
      </div>
    );
  }

  const outlineHex = OUTLINE_HEX_MAP[params.outline] || "#10b981";

  return (
    <div className={`flex flex-col bg-slate-900/90 text-slate-100 rounded-xl p-4 border border-slate-700/80 shadow-lg ${className}`}>
      {/* Header with Simple View Toggle */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
        <div className="flex items-center gap-2">
          <div
            className="w-3 h-3 rounded-full animate-pulse"
            style={{ backgroundColor: outlineHex }}
          />
          <span className="font-semibold text-sm text-slate-200">3D Body Twin</span>
          <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-950 text-indigo-300 border border-indigo-800">
            Interactive 3D
          </span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setSimpleView(true)}
            className="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs px-2.5 py-1 rounded font-medium border border-slate-600 transition-colors"
          >
            Simple View (2D)
          </button>
        </div>
      </div>

      {/* 3D Canvas */}
      <div className="relative h-80 bg-slate-950/80 rounded-lg border border-slate-800/80 overflow-hidden">
        <Canvas
          camera={{ position: [0, 0.4, 3.8], fov: 45 }}
          dpr={[1, 2]}
          gl={{ antialias: true, powerPreference: "high-performance" }}
          onCreated={({ gl }) => {
            gl.setClearColor(new THREE.Color("#020617"));
          }}
        >
          <ambientLight intensity={0.7} />
          <directionalLight position={[3, 5, 4]} intensity={1.2} />
          <pointLight position={[-3, -2, -2]} intensity={0.4} />

          {/* Primary Mannequin */}
          <Mannequin params={params} />

          {/* Ghost Body (Simulated Twin) */}
          {ghostParams && <Mannequin params={ghostParams} isGhost={true} />}

          <OrbitControls
            enablePan={false}
            minDistance={2.5}
            maxDistance={6.0}
            maxPolarAngle={Math.PI / 2 + 0.1}
          />
        </Canvas>

        {/* Operated Side Tag */}
        <div className="absolute top-2 right-2 bg-slate-900/90 border border-slate-700/80 px-2.5 py-1 rounded text-[11px] font-medium text-slate-300 flex items-center gap-1.5 shadow-sm">
          <span className="w-2 h-2 rounded-full bg-rose-500" />
          Operated: <strong className="text-slate-100">Right Knee</strong>
        </div>

        {/* Ghost Body Label */}
        {ghostParams && (
          <div className="absolute bottom-2 right-2 bg-slate-800/90 border border-slate-600 px-2.5 py-1 rounded text-[11px] text-slate-300 shadow">
            Ghost Body: <strong className="text-indigo-300">Simulated Twin (45% opacity)</strong>
          </div>
        )}
      </div>

      {/* Metric Legend */}
      <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
        <div className="bg-slate-950/40 p-2 rounded border border-slate-800">
          <span className="text-slate-400 block text-[10px] uppercase font-semibold">Swelling</span>
          <span className="font-mono text-rose-300 font-bold">{twin.observations.swelling.toFixed(1)}</span>
          <span className="text-slate-400 text-[10px] block">
            knee +{Math.round((params.knee_scale - 1) * 100)}%
          </span>
        </div>
        <div className="bg-slate-950/40 p-2 rounded border border-slate-800">
          <span className="text-slate-400 block text-[10px] uppercase font-semibold">Pain</span>
          <span className="font-mono text-red-300 font-bold">{twin.observations.pain.toFixed(1)}</span>
          <span className="text-slate-400 text-[10px] block">{params.pain_hz.toFixed(2)} Hz pulse</span>
        </div>
        <div className="bg-slate-950/40 p-2 rounded border border-slate-800">
          <span className="text-slate-400 block text-[10px] uppercase font-semibold">Inflammation</span>
          <span className="font-mono text-amber-300 font-bold">
            {twin.scores.inflammation_score.toFixed(1)}
          </span>
          <span className="text-slate-400 text-[10px] block">heat tint {Math.round(params.heat * 100)}%</span>
        </div>
        <div className="bg-slate-950/40 p-2 rounded border border-slate-800">
          <span className="text-slate-400 block text-[10px] uppercase font-semibold">Mobility</span>
          <span className="font-mono text-emerald-300 font-bold">
            {twin.scores.mobility_capacity.toFixed(1)}
          </span>
          <span className="text-slate-400 text-[10px] block">
            walk speed {params.walk_speed.toFixed(2)}
          </span>
        </div>
      </div>

      {/* BODY_DISCLAIMER */}
      <div className="mt-3 pt-2 border-t border-slate-800 text-center">
        <p className="text-[11px] text-slate-400 italic">{BODY_DISCLAIMER}</p>
      </div>
    </div>
  );
};
