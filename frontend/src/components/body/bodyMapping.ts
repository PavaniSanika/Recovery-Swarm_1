import type { TwinState } from "../../types";
import type {
  BodyParams,
  BodyMarker,
  BodyRegion,
  OutlineColor,
  ScreeningFlag,
} from "../../types.ext";

function clamp(val: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, val));
}

export function twinToBodyParams(
  twin: TwinState,
  flags: ScreeningFlag[] = []
): BodyParams {
  const swelling = clamp(twin.observations.swelling, 0, 10);
  const knee_scale = 1 + 0.06 * swelling;

  const pain = clamp(twin.observations.pain, 0, 10);
  const pain_hz = 0.5 + 0.25 * pain;
  const pain_intensity = pain / 10;

  const inflammation = clamp(twin.scores.inflammation_score, 0, 10);
  const heat = inflammation / 10;

  const mobility = clamp(twin.scores.mobility_capacity, 0, 10);
  const rawWalkSpeed = mobility / 10;
  const walk_speed = rawWalkSpeed < 0.1 ? 0 : rawWalkSpeed;

  let outline: OutlineColor = "green";
  switch (twin.trajectory.overall) {
    case "on_track":
      outline = "green";
      break;
    case "slightly_below_expected":
      outline = "yellow";
      break;
    case "below_expected":
      outline = "orange";
      break;
    case "deteriorating":
      outline = "red";
      break;
    default:
      outline = "green";
  }

  const markers: BodyMarker[] = (flags || []).map((flag) => {
    let region: BodyRegion = "knee";
    if (flag.flag_id === "SF1" || flag.flag_id === "SF3" || flag.flag_id === "SF4") {
      region = "knee";
    } else if (flag.flag_id === "SF2") {
      const hasChestOrBreath = flag.evidence.some((e) => {
        const lower = e.toLowerCase();
        return lower.includes("chest") || lower.includes("breath");
      });
      region = hasChestOrBreath ? "chest" : "calf";
    } else if (flag.flag_id === "SF5") {
      region = "legs";
    }

    return {
      region,
      flag_id: flag.flag_id,
      severity: flag.severity,
    };
  });

  return {
    knee_scale,
    pain_hz,
    pain_intensity,
    heat,
    walk_speed,
    outline,
    markers,
    site: "knee",
    operated_side: "right",
  };
}
