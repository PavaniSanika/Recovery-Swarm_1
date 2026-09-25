"""Plan Generator for RECOVERY-SWARM.

Workflow component transforming a swarm Decision and SafetyResult into a user-facing 6-12 hour Plan.
Adds no actions that are not present in the decided actions.
"""

import os
from typing import Any, List, Optional
from pydantic import BaseModel
from app.agents.base import call_llm_structured
from app.agents.coordinator import Decision
from app.config import config
from app.models.schemas import Plan, PlanItem, PriorityResult, SafetyResult



def build_plan(
    decision: Decision,
    safety_result: Optional[SafetyResult] = None,
    priority_result: Optional[PriorityResult] = None,
    horizon_hours: int = 12,
) -> Plan:
    """Builds a typed Plan from a swarm Decision and optional SafetyResult."""
    if safety_result and safety_result.modified_plan is not None:
        mod_plan = safety_result.modified_plan
        if mod_plan.steps_target is not None:
            new_target_str = f"{mod_plan.steps_target} steps"
            new_high = []
            for item in mod_plan.high_priority:
                if "mobility" in item.action.lower():
                    new_high.append(item.model_copy(update={"target": new_target_str}))
                else:
                    new_high.append(item)
            new_med = []
            for item in mod_plan.medium_priority:
                if "mobility" in item.action.lower():
                    new_med.append(item.model_copy(update={"target": new_target_str}))
                else:
                    new_med.append(item)
            return mod_plan.model_copy(update={"high_priority": new_high, "medium_priority": new_med})
        return mod_plan

    high_priority: List[PlanItem] = []
    medium_priority: List[PlanItem] = []
    monitoring: List[str] = []

    roles = priority_result.roles if priority_result else {}

    for p in decision.decided_actions:
        action_title = f"{p.action_type.replace('_', ' ').capitalize()} ({p.direction})"
        target_str = f"{int(p.target_value)} steps" if p.target_value is not None else None

        item = PlanItem(
            action=action_title,
            reason=p.rationale,
            target=target_str,
        )

        role = roles.get(p.agent, "supporting")
        if role == "lead":
            high_priority.append(item)
        else:
            medium_priority.append(item)

        if p.risks:
            monitoring.append(f"Monitor for {p.risks[0].lower()}")

    if not monitoring:
        monitoring.append("Monitor pain and swelling before further activity progression")

    if safety_result and safety_result.rules_triggered:
        rules_str = ", ".join([r.rule_id for r in safety_result.rules_triggered])
        safety_status = f"Safety rules triggered: {rules_str}"
    else:
        safety_status = "No predefined safety rule triggered."

    return Plan(
        horizon_hours=horizon_hours,
        high_priority=high_priority,
        medium_priority=medium_priority,
        monitoring=monitoring,
        safety_status=safety_status,
        next_reassessment="6 hours",
        expected_score_change="+2 to +4 points over 12 hours",
        explanation=decision.explanation,
        steps_target=decision.steps_target,
    )


class PlanExplanationOutput(BaseModel):
    explanation: str


def build_llm_plan(
    decision: Decision,
    safety_result: Optional[SafetyResult] = None,
    priority_result: Optional[PriorityResult] = None,
    horizon_hours: int = 12,
    twin: Optional[Any] = None,
    scenario_name: str = "demo",
    step_index: int = 0,
) -> Plan:
    """Stage D LLM Plan Generator: rewords and explains actions in approved decision without inventing new actions or violating R5/screening labels."""
    base_plan = build_plan(decision, safety_result, priority_result, horizon_hours)

    if config.fallback_mode or os.getenv("FALLBACK_MODE", "false").lower() == "true":
        return base_plan

    system_prompt = (
        "You are the Plan Generator for RECOVERY-SWARM.\n"
        "Your task is to reword and explain the approved recovery plan actions into a clear, patient-friendly summary.\n"
        "CRITICAL RULES:\n"
        "1. You MAY ONLY reword and explain actions already in the approved decision.\n"
        "2. DO NOT add or invent any new actions, targets, or numbers.\n"
        "3. DO NOT mention medications, doses, drugs, or prescriptions (Rule R5).\n"
        "4. DO NOT use diagnostic terms (diagnosed, diagnosis, confirmed, etc.).\n"
        "5. Output valid JSON matching PlanExplanationOutput schema: {'explanation': '...'}"
    )

    decided_summary = [f"{p.agent}: {p.action_type} ({p.direction}) - {p.rationale}" for p in decision.decided_actions]
    user_prompt = (
        f"Approved Target: {decision.steps_target}\n"
        f"Approved Actions: {'; '.join(decided_summary)}\n"
        f"Base Explanation: {base_plan.explanation}\n"
        "Generate a clear 2-3 sentence explanation summarizing this approved plan."
    )

    def guardrail(out: PlanExplanationOutput, agent: str, state_twin: Any) -> bool:
        exp = out.explanation.lower()
        forbidden_words = ["dose", "mg", "pill", "prescription", "medication", "diagnos", "diagnosed", "confirmed"]
        if any(w in exp for w in forbidden_words):
            return False
        return True

    try:
        res = call_llm_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=PlanExplanationOutput,
            fallback_fn=lambda t: PlanExplanationOutput(explanation=base_plan.explanation),
            twin=twin or decision,
            agent_name="plan_generator",
            guardrail_fn=guardrail,
            scenario_name=scenario_name,
            step_index=step_index,
        )
        return base_plan.model_copy(update={"explanation": res.explanation})
    except Exception:
        return base_plan

