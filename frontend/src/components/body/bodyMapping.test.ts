import { describe, it, expect } from "vitest";
import { twinToBodyParams } from "./bodyMapping";
import type { TwinState } from "../../types";
import type { ScreeningFlag } from "../../types.ext";

const meeraTwin: TwinState = {
  patient_id: "P001",
  profile: {
    name: "Meera Sharma",
    age: 62,
    surgery: "Total Knee Replacement",
    post_op_day: 4,
  },
  observations: {
    pain: 6.0,
    sleep_hours: 4.5,
    steps: 1800,
    swelling: 6.0,
    temperature: 37.1,
    heart_rate: 84,
    crp: 6.2,
  },
  scores: {
    inflammation_score: 6.2,
    mobility_capacity: 5.0,
    sleep_quality: 3.5,
    medication_effectiveness: 5.5,
    complication_risk: 3.2,
    recovery_score: 68,
  },
  trajectory: {
    overall: "slightly_below_expected",
    inflammation: "stable_high",
    mobility: "below_expected",
    sleep: "poor",
  },
  medications: {
    current: ["Paracetamol", "Low-dose opioid at night"],
    response_score: 5.5,
  },
  history: [],
};

describe("twinToBodyParams", () => {
  it("computes exact Meera baseline golden values with 1e-6 tolerance", () => {
    const params = twinToBodyParams(meeraTwin, []);

    expect(params.knee_scale).toBeCloseTo(1.36, 6);
    expect(params.pain_hz).toBeCloseTo(2.0, 6);
    expect(params.pain_intensity).toBeCloseTo(0.6, 6);
    expect(params.heat).toBeCloseTo(0.62, 6);
    expect(params.walk_speed).toBeCloseTo(0.5, 6);

    expect(params.outline).toBe("yellow");
    expect(params.markers).toEqual([]);
    expect(params.site).toBe("knee");
    expect(params.operated_side).toBe("right");
  });

  it("handles clamping for out-of-range observations and scores", () => {
    const extremeTwin: TwinState = {
      ...meeraTwin,
      observations: {
        ...meeraTwin.observations,
        swelling: 15.0, // should clamp to 10 -> knee_scale = 1 + 0.6 = 1.6
        pain: -5.0,     // should clamp to 0 -> pain_hz = 0.5, pain_intensity = 0
      },
      scores: {
        ...meeraTwin.scores,
        inflammation_score: 12.0, // should clamp to 10 -> heat = 1.0
        mobility_capacity: 15.0,  // should clamp to 10 -> walk_speed = 1.0
      },
    };

    const params = twinToBodyParams(extremeTwin);

    expect(params.knee_scale).toBeCloseTo(1.6, 6);
    expect(params.pain_hz).toBeCloseTo(0.5, 6);
    expect(params.pain_intensity).toBeCloseTo(0.0, 6);
    expect(params.heat).toBeCloseTo(1.0, 6);
    expect(params.walk_speed).toBeCloseTo(1.0, 6);
  });

  it("clamps walk_speed below 0.1 to 0", () => {
    const lowMobilityTwin: TwinState = {
      ...meeraTwin,
      scores: {
        ...meeraTwin.scores,
        mobility_capacity: 0.8, // 0.8 / 10 = 0.08 (< 0.1) -> walk_speed = 0
      },
    };

    const params = twinToBodyParams(lowMobilityTwin);
    expect(params.walk_speed).toBeCloseTo(0.0, 6);

    const edgeMobilityTwin: TwinState = {
      ...meeraTwin,
      scores: {
        ...meeraTwin.scores,
        mobility_capacity: 1.0, // 1.0 / 10 = 0.1 (>= 0.1) -> walk_speed = 0.1
      },
    };

    const edgeParams = twinToBodyParams(edgeMobilityTwin);
    expect(edgeParams.walk_speed).toBeCloseTo(0.1, 6);
  });

  it("maps all outline colors correctly according to trajectory.overall", () => {
    const onTrack = twinToBodyParams({
      ...meeraTwin,
      trajectory: { ...meeraTwin.trajectory, overall: "on_track" },
    });
    expect(onTrack.outline).toBe("green");

    const slightlyBelow = twinToBodyParams({
      ...meeraTwin,
      trajectory: { ...meeraTwin.trajectory, overall: "slightly_below_expected" },
    });
    expect(slightlyBelow.outline).toBe("yellow");

    const belowExpected = twinToBodyParams({
      ...meeraTwin,
      trajectory: { ...meeraTwin.trajectory, overall: "below_expected" },
    });
    expect(belowExpected.outline).toBe("orange");

    const deteriorating = twinToBodyParams({
      ...meeraTwin,
      trajectory: { ...meeraTwin.trajectory, overall: "deteriorating" },
    });
    expect(deteriorating.outline).toBe("red");
  });

  it("routes markers to correct regions based on flag_id and evidence", () => {
    const flags: ScreeningFlag[] = [
      {
        flag_id: "SF1",
        title: "Possible infection",
        severity: "urgent",
        evidence: ["Temp 38.2"],
        recommendation: "Review",
        disclaimer: "Disclaimer",
      },
      {
        flag_id: "SF2",
        title: "Possible clot",
        severity: "review",
        evidence: ["Calf swelling"],
        recommendation: "Review",
        disclaimer: "Disclaimer",
      },
      {
        flag_id: "SF2",
        title: "Possible PE",
        severity: "urgent",
        evidence: ["Chest pain reported"],
        recommendation: "Review",
        disclaimer: "Disclaimer",
      },
      {
        flag_id: "SF3",
        title: "Delayed healing",
        severity: "review",
        evidence: ["CRP high"],
        recommendation: "Review",
        disclaimer: "Disclaimer",
      },
      {
        flag_id: "SF4",
        title: "Uncontrolled pain",
        severity: "review",
        evidence: ["Pain 8"],
        recommendation: "Review",
        disclaimer: "Disclaimer",
      },
      {
        flag_id: "SF5",
        title: "Slow mobility",
        severity: "review",
        evidence: ["Steps low"],
        recommendation: "Review",
        disclaimer: "Disclaimer",
      },
    ];

    const params = twinToBodyParams(meeraTwin, flags);
    expect(params.markers).toHaveLength(6);

    expect(params.markers[0]).toEqual({ region: "knee", flag_id: "SF1", severity: "urgent" });
    expect(params.markers[1]).toEqual({ region: "calf", flag_id: "SF2", severity: "review" });
    expect(params.markers[2]).toEqual({ region: "chest", flag_id: "SF2", severity: "urgent" });
    expect(params.markers[3]).toEqual({ region: "knee", flag_id: "SF3", severity: "review" });
    expect(params.markers[4]).toEqual({ region: "knee", flag_id: "SF4", severity: "review" });
    expect(params.markers[5]).toEqual({ region: "legs", flag_id: "SF5", severity: "review" });
  });
});
