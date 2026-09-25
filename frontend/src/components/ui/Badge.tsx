import React from "react";
import { getStatusStyle, StatusSemantic } from "../../utils/statusColor";

export interface BadgeProps {
  children: React.ReactNode;
  variant?: StatusSemantic | "neutral" | string;
  size?: "sm" | "md";
  dot?: boolean;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant,
  size = "md",
  dot = false,
  className = "",
}) => {
  const style = variant && variant !== "neutral"
    ? getStatusStyle(variant)
    : {
        badge: "bg-slate-100 text-slate-700 border-slate-200",
        dotBg: "bg-slate-400",
      };

  const sizeStyles = size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-1 text-xs";

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-medium rounded-full border ${style.badge} ${sizeStyles} ${className}`}
    >
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${style.dotBg}`} />}
      {children}
    </span>
  );
};
