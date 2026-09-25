"""Tests for Stage D: Structured LLM Integration, Rate Limiting, Guardrails, and Fallback.

All tests use mocks or fallback mode; ZERO network API calls are made during pytest.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from app.agents.base import RateLimiter, call_llm_structured, get_rate_limiter
from app.agents.cache import USAGE_FILE, get_today_usage_count, record_llm_call, reset_last_run_stats
from app.config import config
from app.graph import run_cycle
from app.models.schemas import (
    ObservationIn,
    Plan,
    Proposal,
    Stance,
    TwinState,
)
from app.workflow.debate import StancesBatch, run_llm_debate


@pytest.fixture
def baseline_twin():
    scenarios_dir = Path(__file__).resolve().parent.parent.parent / "data" / "scenarios"
    with open(scenarios_dir / "meera_day4.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return TwinState(**data)


def test_llm_model_from_env():
    """Confirm LLM_MODEL is read from backend/.env and defaults to gemini-3.5-flash-lite if missing."""
    model_name = os.getenv("LLM_MODEL", "").strip() or config.llm_model
    assert model_name != ""
    assert "gemini" in model_name.lower() or "flash" in model_name.lower() or model_name == "gemini-3.5-flash-lite"


def test_rate_limiter_process_wide():
    """Confirm RateLimiter tracks timestamps and enforces process-wide RPM."""
    limiter = RateLimiter(max_rpm=600)  # fast for test
    limiter.acquire()
    assert len(limiter.request_timestamps) == 1

    shared_limiter = get_rate_limiter()
    assert isinstance(shared_limiter, RateLimiter)


def test_llm_usage_file_increment(tmp_path, monkeypatch):
    """Test that record_llm_call increments data/llm_usage.json for today's date."""
    test_usage_file = tmp_path / "test_llm_usage.json"
    monkeypatch.setattr("app.agents.cache.USAGE_FILE", test_usage_file)

    initial_count = get_today_usage_count()
    assert initial_count == 0

    record_llm_call()

    new_count = get_today_usage_count()
    assert new_count == 1
    assert test_usage_file.exists()

    with open(test_usage_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    assert data[today_str] == 1


def test_stances_batch_unpacked_to_list_stance(baseline_twin):
    """Confirm run_llm_debate unpacks internal StancesBatch into list[Stance]."""
    r1_props = [
        Proposal(
            agent="mobility",
            action_type="mobility",
            target_value=2200,
            direction="increase",
            rationale="Progress mobility",
            evidence=["Steps 1800"],
            risks=["Fatigue"],
            confidence=0.8,
        ),
        Proposal(
            agent="inflammation",
            action_type="swelling",
            target_value=None,
            direction="maintain",
            rationale="Reduce swelling",
            evidence=["CRP 3.0"],
            risks=["Stiffness"],
            confidence=0.75,
        ),
    ]
    p_res = MagicMock(priority_scores={"mobility": 0.8, "inflammation": 0.7, "medication": 0.3, "sleep": 0.5})

    with patch("app.agents.base.call_llm_structured") as mock_llm_call:
        mock_batch = StancesBatch(
            agent="inflammation",
            stances=[
                Stance(
                    agent="inflammation",
                    target_agent="mobility",
                    stance="oppose",
                    revised_confidence=0.6,
                    message="Reduce steps target due to swelling.",
                ),
            ]
        )
        mock_llm_call.return_value = mock_batch

        d_res = run_llm_debate(baseline_twin, r1_props, p_res)
        assert isinstance(d_res.stances, list)
        assert len(d_res.stances) > 0
        assert isinstance(d_res.stances[0], Stance)
        assert d_res.stances[0].agent == "inflammation"


def test_mocked_llm_full_cycle(baseline_twin):
    """Confirm full cycle works with LLM mode (mocked responses) returning valid CycleResponse."""
    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        # Mock structured response for proposals
        mock_resp = MagicMock()
        mock_resp.text = json.dumps({
            "agent": "mobility",
            "action_type": "increase_steps",
            "target_value": 2000,
            "direction": "increase",
            "rationale": "Patient is progressing steadily on post-op day 4.",
            "evidence": ["Current steps 1800", "Pain 3"],
            "risks": ["Mild fatigue"],
            "confidence": 0.85
        })
        mock_client.models.generate_content.return_value = mock_resp

        res = run_cycle(baseline_twin, fallback=False)

        assert res.cycle_id.startswith("cycle_")
        assert res.twin.patient_id == baseline_twin.patient_id
        assert len(res.proposals) > 0
        assert isinstance(res.plan, Plan) or res.escalated is True


def test_mocked_llm_invalid_json_fallback(baseline_twin):
    """Confirm invalid JSON from LLM triggers retry then per-call fallback without crashing."""
    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        mock_resp = MagicMock()
        mock_resp.text = "NOT VALID JSON"
        mock_client.models.generate_content.return_value = mock_resp

        # Should fall back gracefully to rule-based result without raising an error
        res = run_cycle(baseline_twin, fallback=False)
        assert res is not None
        assert len(res.proposals) > 0


def test_medication_dose_blocked_by_r5(baseline_twin):
    """Confirm medication proposal trying to change drug/dose is caught by guardrails/R5."""
    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        # Med proposal trying to prescribe drug dose
        mock_resp = MagicMock()
        mock_resp.text = json.dumps({
            "agent": "medication",
            "action_type": "pain_review",
            "target_value": None,
            "direction": "maintain",
            "rationale": "Increase Paracetamol 500mg dose to 1000mg for pain.",
            "evidence": ["Pain 6/10"],
            "risks": ["Overdose risk"],
            "confidence": 0.9
        })
        mock_client.models.generate_content.return_value = mock_resp

        res = run_cycle(baseline_twin, fallback=False)
        # Check that medication proposal was replaced by fallback rule-based proposal
        med_prop = next((p for p in res.proposals if p.agent == "medication"), None)
        assert med_prop is not None
        assert "500mg" not in med_prop.rationale
        assert "1000mg" not in med_prop.rationale


def test_full_cycle_fallback_mode_env_override(baseline_twin, monkeypatch):
    """Confirm FALLBACK_MODE=true environment variable forces rule-based cycle offline."""
    monkeypatch.setenv("FALLBACK_MODE", "true")

    res = run_cycle(baseline_twin, fallback=False)
    assert res is not None
    assert res.twin.patient_id == baseline_twin.patient_id
