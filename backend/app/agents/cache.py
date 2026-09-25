"""Response Cache, Usage Tracker, and Statistics for RECOVERY-SWARM (Stage D).

Manages CACHE_MODE=off|record|replay, data/llm_usage.json tracking, and LAST_RUN_STATS.
"""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
USAGE_FILE = DATA_DIR / "llm_usage.json"

CACHE_DIR.mkdir(parents=True, exist_ok=True)

LAST_RUN_STATS: Dict[str, int] = {
    "llm_calls": 0,
    "fallback_calls": 0,
    "cached_calls": 0,
    "error_calls": 0,
}


def reset_last_run_stats() -> None:
    """Resets LAST_RUN_STATS counters for a new cycle run."""
    global LAST_RUN_STATS
    LAST_RUN_STATS = {
        "llm_calls": 0,
        "fallback_calls": 0,
        "cached_calls": 0,
        "error_calls": 0,
    }


def get_cache_mode() -> str:
    """Returns lowercased CACHE_MODE: 'off', 'record', or 'replay'."""
    return os.getenv("CACHE_MODE", "off").lower()


def compute_cache_key(
    scenario_name: str,
    step_index: int,
    agent_name: str,
    twin_data: Dict[str, Any],
    prompt_version: str = "v1",
) -> str:
    """Generates a unique cache key based on scenario, step, agent, twin observations, and prompt version."""
    payload = {
        "scenario": scenario_name,
        "step": step_index,
        "agent": agent_name,
        "obs": twin_data.get("observations", {}),
        "prompt_version": prompt_version,
    }
    raw_json = json.dumps(payload, sort_keys=True)
    digest = hashlib.sha256(raw_json.encode("utf-8")).hexdigest()[:16]
    return f"{scenario_name}_s{step_index}_{agent_name}_{digest}"


def get_cached_response(cache_key: str) -> Optional[Dict[str, Any]]:
    """Retrieves cached response dict if cache file exists."""
    cache_path = CACHE_DIR / f"{cache_key}.json"
    if cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def save_cached_response(cache_key: str, data: Dict[str, Any]) -> None:
    """Saves response dict to cache directory."""
    cache_path = CACHE_DIR / f"{cache_key}.json"
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def record_llm_call() -> None:
    """Increments LAST_RUN_STATS and records real non-cached LLM call in data/llm_usage.json."""
    LAST_RUN_STATS["llm_calls"] += 1

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    usage_data: Dict[str, int] = {}

    if USAGE_FILE.exists():
        try:
            with open(USAGE_FILE, "r", encoding="utf-8") as f:
                usage_data = json.load(f)
        except Exception:
            usage_data = {}

    usage_data[today_str] = usage_data.get(today_str, 0) + 1

    try:
        with open(USAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(usage_data, f, indent=2)
    except Exception:
        pass


def get_today_usage_count() -> int:
    """Reads today's LLM call count from data/llm_usage.json."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if USAGE_FILE.exists():
        try:
            with open(USAGE_FILE, "r", encoding="utf-8") as f:
                usage_data = json.load(f)
                return usage_data.get(today_str, 0)
        except Exception:
            return 0
    return 0
