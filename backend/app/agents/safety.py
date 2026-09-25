"""Deterministic Rule-Based Safety Guardian for RECOVERY-SWARM.

Enforces rules R1-R8 strictly per CONTRACTS section 5.3 and thresholds.yaml.
No external network or AI model calls anywhere in this module.
"""

from datetime import datetime, timezone
import math
import re
from typing import Any, Dict, List, Optional
from app.config import config
from app.models.schemas import (
    HistoryEntry,
    Plan,
    PlanItem,
    Proposal,
    RuleHit,
    SafetyResult,
    TwinState,
)
from app.twin.engine import compute_slope

OUTCOME_RANK = {
    "escalate": 4,
    "reject": 3,
    "modify": 2,
    "allow": 1,
}

FORBIDDEN_PATTERNS = [
    re.compile(r"\bdose\b", re.IGNORECASE),
    re.compile(r"\bdosage\b", re.IGNORECASE),
    re.compile(r"\bincrease medication\b", re.IGNORECASE),
    re.compile(r"\bdecrease medication\b", re.IGNORECASE),
    re.compile(r"\bstart medication\b", re.IGNORECASE),
    re.compile(r"\bstop medication\b", re.IGNORECASE),
    re.compile(r"\bnew medication\b", re.IGNORECASE),
    re.compile(r"\bprescribe\b", re.IGNORECASE),
    re.compile(r"\bmg\b", re.IGNORECASE),
]


def check_forbidden_terms(text: str) -> bool:
    """Matches forbidden terms case-insensitively using exact word boundaries."""
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.search(text):
            return True
    return False


def parse_timestamp(ts_str: str) -> Optional[datetime]:
    try:
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1] + "+00:00"
        return datetime.fromisoformat(ts_str)
    except Exception:
        return None


def calculate_pain_rise_24h(current_pain: float, current_ts_str: str, history: List[HistoryEntry]) -> float:
    """Calculates pain rise over entries in history within the last 24 hours."""
    if not history:
        return 0.0

    curr_dt = parse_timestamp(current_ts_str)
    min_pain_24h = current_pain

    for entry in history:
        if curr_dt:
            e_dt = parse_timestamp(entry.timestamp)
            if e_dt:
                hours_diff = (curr_dt - e_dt).total_seconds() / 3600.0
                if hours_diff <= 24.0:
                    min_pain_24h = min(min_pain_24h, entry.observations.pain)
        else:
            min_pain_24h = min(min_pain_24h, entry.observations.pain)

    return max(0.0, current_pain - min_pain_24h)


class SafetyGuardian:
    def __init__(self, thresholds: Optional[Dict[str, Any]] = None):
        self.cfg = thresholds or config.thresholds.get("safety_rules", {})

    def evaluate_proposal(self, proposal: Proposal, twin: TwinState) -> List[RuleHit]:
        """Evaluates a single proposal for immediate safety hits during debate."""
        hits: List[RuleHit] = []
        current_steps = twin.observations.steps

        # R4: Step increase > 10%
        if proposal.action_type == "mobility" and proposal.direction == "increase":
            if proposal.target_value is not None and proposal.target_value > current_steps * 1.10:
                max_allowed = math.floor(current_steps * 1.10)
                hits.append(
                    RuleHit(
                        rule_id="R4",
                        outcome="modify",
                        detail=f"Proposed mobility target ({proposal.target_value}) exceeds 10% daily increase limit. Capped at {max_allowed}.",
                    )
                )

        # R5: Medication boundaries
        # Forbidden terms in text
        full_text = f"{proposal.rationale} {' '.join(proposal.evidence)} {' '.join(proposal.risks)}"
        if check_forbidden_terms(full_text):
            hits.append(
                RuleHit(
                    rule_id="R5",
                    outcome="reject",
                    detail="Proposal contains forbidden medication adjustment or dosage terms.",
                )
            )

        # Medication agent action_type restrictions
        if proposal.agent == "medication":
            if proposal.action_type not in ["pain_review", "monitoring", "escalate"]:
                hits.append(
                    RuleHit(
                        rule_id="R5",
                        outcome="reject",
                        detail=f"Medication Response Agent cannot propose action_type '{proposal.action_type}'. Must be pain_review, monitoring, or escalate.",
                    )
                )

        return hits

    def evaluate(
        self,
        twin: TwinState,
        proposals: List[Proposal],
        draft_plan: Optional[Plan] = None,
        history: Optional[List[HistoryEntry]] = None,
        flags: Optional[List[str]] = None,
        missing_fields: Optional[List[str]] = None,
    ) -> SafetyResult:
        """Evaluates full patient state, proposals, and draft plan against rules R1-R8."""
        hist = history if history is not None else twin.history
        combined_flags = set(twin.observations.flags or [])
        if flags:
            combined_flags.update(flags)

        rule_hits: List[RuleHit] = []

        current_ts = hist[-1].timestamp if hist else ""

        # R1: Pain >= 8.0 or 24h pain rise >= 2.0
        pain_24h_rise = calculate_pain_rise_24h(twin.observations.pain, current_ts, hist)
        if twin.observations.pain >= 8.0 or pain_24h_rise >= 2.0:
            rule_hits.append(
                RuleHit(
                    rule_id="R1",
                    outcome="escalate",
                    detail=f"Pain elevated ({twin.observations.pain}/10) or 24h pain rise ({pain_24h_rise:.1f}) exceeds threshold. Escalating to clinician and blocking activity increase.",
                )
            )

        # R2: Swelling >= 6.0 and swelling slope > 0 (requires >= 2 history entries)
        if twin.observations.swelling >= 6.0 and len(hist) >= 1:
            swelling_rising = (twin.observations.swelling > hist[-1].observations.swelling) or (
                len(hist) >= 2 and compute_slope(hist, "swelling") > 0
            )
            if swelling_rising:
                rule_hits.append(
                    RuleHit(
                        rule_id="R2",
                        outcome="modify",
                        detail=f"Swelling is elevated ({twin.observations.swelling}/10) and rising. Capping mobility steps target at current steps ({twin.observations.steps}).",
                    )
                )

        # R3: High fever (temp >= 38.0) or red flags (chest_pain, breathlessness, calf_pain)
        red_flags_r3 = {"chest_pain", "breathlessness", "calf_pain"}
        found_r3_flags = combined_flags.intersection(red_flags_r3)
        if twin.observations.temperature >= 38.0 or found_r3_flags:
            flag_str = f" Red flags: {', '.join(found_r3_flags)}." if found_r3_flags else ""
            rule_hits.append(
                RuleHit(
                    rule_id="R3",
                    outcome="escalate",
                    detail=f"Fever or critical clinical signs detected (Temp: {twin.observations.temperature}°C).{flag_str} Escalating immediately.",
                )
            )

        # R4 & R5 evaluation across proposals
        for p in proposals:
            hits = self.evaluate_proposal(p, twin)
            rule_hits.extend(hits)

        # R5 check on draft plan text if plan provided
        if draft_plan:
            plan_text = f"{draft_plan.explanation} {' '.join([i.action + ' ' + i.reason for i in draft_plan.high_priority + draft_plan.medium_priority])}"
            if check_forbidden_terms(plan_text):
                rule_hits.append(
                    RuleHit(
                        rule_id="R5",
                        outcome="reject",
                        detail="Draft plan text contains forbidden medication dosage or prescription terms.",
                    )
                )

        # R6: Poor sleep (< 4.0h) AND high pain (>= 7.0)
        if twin.observations.sleep_hours < 4.0 and twin.observations.pain >= 7.0:
            rule_hits.append(
                RuleHit(
                    rule_id="R6",
                    outcome="modify",
                    detail=f"Severe sleep debt ({twin.observations.sleep_hours}h) combined with high pain ({twin.observations.pain}/10). Capping activity at current steps ({twin.observations.steps}).",
                )
            )

        # R7: Missing observation fields or low proposal confidence (< 0.5)
        if missing_fields:
            rule_hits.append(
                RuleHit(
                    rule_id="R7",
                    outcome="escalate",
                    detail=f"Missing key observation data: {', '.join(missing_fields)}. Escalating for clinical data check.",
                )
            )
        for p in proposals:
            if p.confidence < 0.5:
                rule_hits.append(
                    RuleHit(
                        rule_id="R7",
                        outcome="escalate",
                        detail=f"Agent '{p.agent}' proposal confidence ({p.confidence}) is below threshold (0.5). Escalating.",
                    )
                )

        # R8: Wound flags (wound_redness, wound_discharge, wound_opening)
        wound_flags_r8 = {"wound_redness", "wound_discharge", "wound_opening"}
        found_r8_flags = combined_flags.intersection(wound_flags_r8)
        if found_r8_flags:
            rule_hits.append(
                RuleHit(
                    rule_id="R8",
                    outcome="escalate",
                    detail=f"Wound infection / complication signs detected: {', '.join(found_r8_flags)}. Escalating for clinical review.",
                )
            )

        # Determine strictest outcome
        if not rule_hits:
            overall_outcome = "allow"
        else:
            overall_outcome = max(
                rule_hits, key=lambda h: OUTCOME_RANK.get(h.outcome, 1)
            ).outcome

        # Build modified plan if outcome is "modify" or "escalate"
        modified_plan: Optional[Plan] = None
        if overall_outcome == "modify":
            target_cap = math.floor(twin.observations.steps * 1.10)
            if any(h.rule_id in ["R2", "R6"] for h in rule_hits):
                target_cap = twin.observations.steps

            base_high = list(draft_plan.high_priority) if draft_plan else []
            base_med = list(draft_plan.medium_priority) if draft_plan else []
            new_high = []
            for item in base_high:
                if "mobility" in item.action.lower():
                    new_high.append(item.model_copy(update={"target": f"{target_cap} steps"}))
                else:
                    new_high.append(item)
            new_med = []
            for item in base_med:
                if "mobility" in item.action.lower():
                    new_med.append(item.model_copy(update={"target": f"{target_cap} steps"}))
                else:
                    new_med.append(item)

            if not new_high and not new_med:
                new_high.append(
                    PlanItem(
                        action="Conservative Mobility",
                        reason="Safety rule modified target step count",
                        target=f"{target_cap} steps",
                    )
                )

            modified_plan = Plan(
                horizon_hours=draft_plan.horizon_hours if draft_plan else 12,
                high_priority=new_high,
                medium_priority=new_med,
                monitoring=draft_plan.monitoring if draft_plan else ["Monitor swelling and pain before further activity increase"],
                safety_status=f"Safety rules applied: {', '.join([h.rule_id for h in rule_hits])}",
                next_reassessment="6 hours",
                expected_score_change=draft_plan.expected_score_change if draft_plan else None,
                explanation=draft_plan.explanation if draft_plan else "Mobility activity modified by Safety Guardian rules.",
                steps_target=target_cap,
            )
        elif overall_outcome == "escalate":
            target_cap = twin.observations.steps
            rules_str = ", ".join([r.rule_id for r in rule_hits]) if rule_hits else "Red flag clinical signs"
            modified_plan = Plan(
                horizon_hours=12,
                high_priority=[
                    PlanItem(
                        action="Hold Activity Increase",
                        reason=f"Clinical escalation triggered ({rules_str}). Activity increases blocked.",
                        target=f"{target_cap} steps (capped)",
                    )
                ],
                medium_priority=[],
                monitoring=["Immediate clinician evaluation required", "Monitor pain, swelling, and vital signs"],
                safety_status=f"Safety escalation: {rules_str}",
                next_reassessment="Immediate",
                expected_score_change="Reassessment pending clinician review",
                explanation="Automatic escalation triggered by Safety Guardian rules. Activity progression suspended pending clinical review.",
                steps_target=target_cap,
            )

        return SafetyResult(
            result=overall_outcome,
            rules_triggered=rule_hits,
            modified_plan=modified_plan,
        )
