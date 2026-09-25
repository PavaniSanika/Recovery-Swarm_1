export type StatusSemantic = "on_track" | "caution" | "below_expected" | "deteriorating";

export interface StatusStyle {
  bg: string;
  text: string;
  border: string;
  badge: string;
  dotBg: string;
}

export const STATUS_STYLES: Record<StatusSemantic, StatusStyle> = {
  on_track: {
    bg: "bg-emerald-50",
    text: "text-emerald-700",
    border: "border-emerald-200",
    badge: "bg-emerald-50 text-emerald-700 border-emerald-200",
    dotBg: "bg-emerald-500",
  },
  caution: {
    bg: "bg-amber-50",
    text: "text-amber-700",
    border: "border-amber-200",
    badge: "bg-amber-50 text-amber-700 border-amber-200",
    dotBg: "bg-amber-500",
  },
  below_expected: {
    bg: "bg-orange-50",
    text: "text-orange-700",
    border: "border-orange-200",
    badge: "bg-orange-50 text-orange-700 border-orange-200",
    dotBg: "bg-orange-500",
  },
  deteriorating: {
    bg: "bg-red-50",
    text: "text-red-700",
    border: "border-red-200",
    badge: "bg-red-50 text-red-700 border-red-200",
    dotBg: "bg-red-500",
  },
};

/**
  Map any system value (trajectory, safety result, screening severity, risk level)
  to one of the four canonical status semantics:
  - green (on_track)
  - yellow (caution)
  - orange (below_expected)
  - red (deteriorating)
 */
export function getStatusSemantic(value: string | null | undefined): StatusSemantic {
  if (!value) return "on_track";
  const val = value.toLowerCase();

  // Green / On Track / Allow
  if (
    val === "on_track" ||
    val === "allow" ||
    val === "improving" ||
    val === "good" ||
    val === "info"
  ) {
    return "on_track";
  }

  // Yellow / Slightly Below / Caution / Fair / Review
  if (
    val === "slightly_below_expected" ||
    val === "caution" ||
    val === "fair" ||
    val === "stable_high" ||
    val === "review"
  ) {
    return "caution";
  }

  // Orange / Below Expected / Modify
  if (
    val === "below_expected" ||
    val === "modify" ||
    val === "poor" ||
    val === "declining"
  ) {
    return "below_expected";
  }

  // Red / Deteriorating / Escalate / Reject / Urgent / Worsening
  if (
    val === "deteriorating" ||
    val === "escalate" ||
    val === "reject" ||
    val === "urgent" ||
    val === "worsening" ||
    val === "vetoing"
  ) {
    return "deteriorating";
  }

  return "on_track";
}

export function getStatusStyle(value: string | null | undefined): StatusStyle {
  const semantic = getStatusSemantic(value);
  return STATUS_STYLES[semantic];
}
