import React from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Button } from "./ui/Button";
import { Building2, ArrowLeft } from "lucide-react";

interface HospitalInspectionBannerProps {
  patientId: string;
  patientName?: string;
}

export const HospitalInspectionBanner: React.FC<HospitalInspectionBannerProps> = ({
  patientId,
  patientName,
}) => {
  const { role } = useAuth();

  if (role !== "hospital") return null;

  return (
    <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 flex flex-wrap items-center justify-between gap-2 text-xs text-emerald-900 shadow-sm mb-4">
      <div className="flex items-center space-x-2">
        <Building2 className="w-4 h-4 text-emerald-600 shrink-0" />
        <span>
          <strong>Hospital Staff Mode:</strong> Inspecting Individual Patient Record for{" "}
          <strong className="text-emerald-950 font-semibold">
            {patientName ? `${patientName} (${patientId})` : patientId}
          </strong>
        </span>
      </div>
      <Link to="/hospital">
        <Button
          size="sm"
          variant="outline"
          className="border-emerald-300 text-emerald-800 bg-white hover:bg-emerald-100 text-[11px] gap-1.5 h-7 font-medium"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Return to Ward Overview</span>
        </Button>
      </Link>
    </div>
  );
};
