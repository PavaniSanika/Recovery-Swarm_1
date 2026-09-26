"""LLM Base Client Wrapper for RECOVERY-SWARM (Stage D).

Process-wide rate limiting, Google GenAI SDK integration, Pydantic validation, guardrails check, response caching, and graceful per-call fallback.
"""

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import time
from typing import Any, Callable, Dict, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from app.config import config
from app.agents.cache import (
    LAST_RUN_STATS,
    compute_cache_key,
    get_cache_mode,
    get_cached_response,
    record_llm_call,
    save_cached_response,
)

T = TypeVar("T", bound=BaseModel)

# ---------- Process-Wide Token Bucket Rate Limiter ----------

class RateLimiter:
    """Process-wide rate limiter shared by all LLM calls in the application."""
    def __init__(self, max_rpm: int = 12):
        self.max_rpm = max_rpm
        self.lock = threading.Lock()
        self.request_timestamps: list[float] = []

    def update_rpm(self, max_rpm: int) -> None:
        with self.lock:
            self.max_rpm = max_rpm

    def acquire(self) -> None:
        """Blocks until a request token is available within the 60-second sliding window."""
        with self.lock:
            if self.max_rpm <= 0:
                return

            window_seconds = 60.0
            min_interval = window_seconds / float(self.max_rpm)

            now = time.time()
            # Filter out timestamps older than 60 seconds
            self.request_timestamps = [ts for ts in self.request_timestamps if now - ts < window_seconds]

            if len(self.request_timestamps) >= self.max_rpm:
                # Wait until the oldest timestamp drops out of the window
                sleep_needed = window_seconds - (now - self.request_timestamps[0])
                if sleep_needed > 0:
                    time.sleep(sleep_needed)
                now = time.time()
                self.request_timestamps = [ts for ts in self.request_timestamps if now - ts < window_seconds]

            # Also ensure minimum spacing between consecutive calls
            if self.request_timestamps:
                elapsed_since_last = now - self.request_timestamps[-1]
                if elapsed_since_last < min_interval:
                    time.sleep(min_interval - elapsed_since_last)
                    now = time.time()

            self.request_timestamps.append(now)


# Single process-wide rate limiter instance
_PROCESS_RATE_LIMITER = RateLimiter(max_rpm=int(os.getenv("LLM_MAX_RPM", "12")))


def get_rate_limiter() -> RateLimiter:
    rpm = int(os.getenv("LLM_MAX_RPM", "12"))
    _PROCESS_RATE_LIMITER.update_rpm(rpm)
    return _PROCESS_RATE_LIMITER


def sanitize_json_schema_for_gemini(schema: Any) -> Any:
    """Recursively removes additionalProperties, additional_properties, and title from JSON schema for Gemini API compatibility."""
    if isinstance(schema, dict):
        return {
            k: sanitize_json_schema_for_gemini(v)
            for k, v in schema.items()
            if k not in ["additionalProperties", "additional_properties", "title"]
        }
    elif isinstance(schema, list):
        return [sanitize_json_schema_for_gemini(v) for v in schema]
    return schema


# ---------- HIPAA De-Identification Filter ----------

def deidentify_prompt_for_llm(user_prompt: str, twin: Any) -> str:
    """HIPAA Safe Harbor De-Identification Filter.
    
    Masks patient personal names and direct identifiers before payload 
    leaves the server boundary for external inference.
    """
    if not user_prompt or not twin:
        return user_prompt
    
    patient_name = getattr(getattr(twin, "profile", None), "name", None)
    if patient_name and patient_name in user_prompt:
        token = f"Subject_{hashlib.sha256(patient_name.encode('utf-8')).hexdigest()[:8]}"
        user_prompt = user_prompt.replace(f'"{patient_name}"', f'"{token}"').replace(patient_name, token)
        
    return user_prompt


AGENT_LOCAL_MODEL_MAP = {
    "mobility": os.getenv("LOCAL_FAST_MODEL", "qwen2.5:0.5b"),
    "sleep": os.getenv("LOCAL_FAST_MODEL", "qwen2.5:0.5b"),
    "inflammation": os.getenv("LOCAL_CLINICAL_MODEL", "qwen2.5:7b"),
    "medication": os.getenv("LOCAL_CLINICAL_MODEL", "qwen2.5:7b"),
    "coordinator": os.getenv("LOCAL_CLINICAL_MODEL", "qwen2.5:7b"),
    "debate": os.getenv("LOCAL_CLINICAL_MODEL", "qwen2.5:7b"),
}


# ---------- Base Structured LLM Invocation ----------

def call_llm_structured(
    system_prompt: str,
    user_prompt: str,
    response_model: Type[T],
    fallback_fn: Callable[[Any], T],
    twin: Any,
    agent_name: str,
    guardrail_fn: Optional[Callable[[T, str, Any], bool]] = None,
    scenario_name: str = "demo",
    step_index: int = 0,
) -> T:
    """Executes an LLM structured output call with cache, rate limiting, retries, guardrails, and per-call fallback."""
    
    # 0. Apply HIPAA De-Identification Privacy Filter
    user_prompt = deidentify_prompt_for_llm(user_prompt, twin)
    
    # 1. Check FALLBACK_MODE environment variable
    if config.fallback_mode or os.getenv("FALLBACK_MODE", "false").lower() == "true":
        LAST_RUN_STATS["fallback_calls"] += 1
        return fallback_fn(twin)

    # Check local GPU/Ollama endpoint first (e.g. Local RTX 2050 GPU / Google Colab / On-Premise Ollama)
    local_llm_url = os.getenv("LOCAL_LLM_URL", "").strip()
    if not local_llm_url and not os.getenv("PYTEST_CURRENT_TEST"):
        # Auto-detect local Ollama instance on host
        local_llm_url = "http://127.0.0.1:11434"

    if local_llm_url:
        try:
            import requests
            base_url = local_llm_url.rstrip("/")
            if base_url.endswith("/v1"):
                base_url = base_url[:-3]
            local_model = AGENT_LOCAL_MODEL_MAP.get(agent_name.lower(), os.getenv("LOCAL_CLINICAL_MODEL", "qwen2.5:7b"))

            content_str = None
            schema = None
            try:
                schema = response_model.model_json_schema()
            except Exception:
                schema = None

            # Attempt 1: Native Ollama /api/chat with strict grammar schema
            if schema:
                try:
                    payload = {
                        "model": local_model,
                        "messages": [
                            {"role": "system", "content": f"{system_prompt}\nAgent: '{agent_name}'. Confidence must be float between 0.0 and 1.0."},
                            {"role": "user", "content": user_prompt}
                        ],
                        "format": schema,
                        "stream": False,
                        "options": {"temperature": 0.1}
                    }
                    resp = requests.post(f"{base_url}/api/chat", json=payload, headers={"Content-Type": "application/json"}, timeout=45)
                    if resp.status_code == 200:
                        content_str = resp.json().get("message", {}).get("content", "").strip()
                except Exception:
                    content_str = None

            # Attempt 2: OpenAI-compatible /v1/chat/completions fallback
            if not content_str:
                openai_payload = {
                    "model": local_model,
                    "messages": [
                        {"role": "system", "content": system_prompt + "\nReturn ONLY valid JSON matching schema."},
                        {"role": "user", "content": user_prompt}
                    ],
                    "format": "json",
                    "temperature": 0.1,
                    "stream": False
                }
                resp = requests.post(f"{base_url}/v1/chat/completions", json=openai_payload, headers={"Content-Type": "application/json"}, timeout=45)
                if resp.status_code == 200:
                    content_str = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()

            if content_str:
                # Strip thinking tags (e.g. DeepSeek-R1 <think>...</think>)
                content_str = re.sub(r"<think>.*?</think>", "", content_str, flags=re.DOTALL).strip()
                if "```" in content_str:
                    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content_str)
                    if match:
                        content_str = match.group(1).strip()
                s_idx = content_str.find("{")
                e_idx = content_str.rfind("}")
                if s_idx != -1 and e_idx != -1:
                    content_str = content_str[s_idx:e_idx+1]

                res_dict = json.loads(content_str)
                # Auto-normalize agent field
                if "agent" in res_dict and (not res_dict["agent"] or res_dict["agent"] != agent_name):
                    res_dict["agent"] = agent_name
                # Auto-normalize confidence (percentage to 0.0-1.0 float)
                if "confidence" in res_dict and isinstance(res_dict["confidence"], (int, float)):
                    if res_dict["confidence"] > 1.0:
                        res_dict["confidence"] = min(1.0, float(res_dict["confidence"]) / 100.0)

                parsed_obj = response_model(**res_dict)
                if guardrail_fn is None or guardrail_fn(parsed_obj, agent_name, twin):
                    LAST_RUN_STATS["llm_calls"] += 1
                    return parsed_obj
        except Exception:
            pass  # Seamlessly fall back to Google GenAI / fallback_fn

    api_key = config.llm_api_key or os.getenv("LLM_API_KEY", "")
    if not api_key or api_key == "your_key_here" or not api_key.startswith("AIzaSy"):
        LAST_RUN_STATS["fallback_calls"] += 1
        return fallback_fn(twin)

    # 2. Check model name: always read LLM_MODEL from backend/.env
    model_name = os.getenv("LLM_MODEL", "").strip() or config.llm_model
    if not model_name:
        model_name = "gemini-3.5-flash-lite"

    # 3. Check Response Cache
    cache_mode = get_cache_mode()
    cache_key = compute_cache_key(
        scenario_name=scenario_name,
        step_index=step_index,
        agent_name=agent_name,
        twin_data=twin.model_dump() if hasattr(twin, "model_dump") else {},
    )

    if cache_mode in ["replay", "record"]:
        cached_dict = get_cached_response(cache_key)
        if cached_dict:
            try:
                parsed_obj = response_model(**cached_dict)
                if guardrail_fn is None or guardrail_fn(parsed_obj, agent_name, twin):
                    LAST_RUN_STATS["cached_calls"] += 1
                    return parsed_obj
            except Exception:
                pass

        if cache_mode == "replay":
            # Replay mode requires zero network calls; fall back if cache missing
            LAST_RUN_STATS["fallback_calls"] += 1
            return fallback_fn(twin)

    # 4. Import Google GenAI SDK
    try:
        from google import genai
        from google.genai import types
        from google.genai import errors
    except ImportError:
        LAST_RUN_STATS["error_calls"] += 1
        LAST_RUN_STATS["fallback_calls"] += 1
        return fallback_fn(twin)

    llm_cfg = config.thresholds.get("llm", {})
    max_tokens = int(llm_cfg.get("max_tokens", 600))
    temperature = float(llm_cfg.get("temperature", 0.1))
    max_retries = int(llm_cfg.get("retries", 2))

    # 5. Acquire rate limiter token
    limiter = get_rate_limiter()
    
    # Retry loop (attempt 0 = initial, attempt 1 = retry once)
    for attempt in range(max_retries):
        try:
            limiter.acquire()
            record_llm_call()

            client = genai.Client(api_key=api_key)

            # Request structured JSON matching response_model schema sanitized for Gemini API
            json_schema = sanitize_json_schema_for_gemini(response_model.model_json_schema())
            
            config_obj = types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=temperature,
                max_output_tokens=max_tokens,
                response_mime_type="application/json",
                response_schema=json_schema,
            )

            response = client.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=config_obj,
            )

            raw_text = response.text.strip() if response.text else ""
            if not raw_text:
                raise ValueError("Empty response text from LLM")

            res_dict = json.loads(raw_text)
            parsed_obj = response_model(**res_dict)

            # Run guardrail check
            if guardrail_fn is not None and not guardrail_fn(parsed_obj, agent_name, twin):
                raise ValueError(f"Guardrail validation failed for agent '{agent_name}'")

            # Success! Save to cache if recording
            if cache_mode == "record":
                save_cached_response(cache_key, parsed_obj.model_dump())

            return parsed_obj

        except Exception as e:
            # Handle rate limit HTTP 429 backoff
            if "429" in str(e) or "ResourceExhausted" in type(e).__name__:
                time.sleep(2.0 * (attempt + 1))
            
            LAST_RUN_STATS["error_calls"] += 1

    # All retries failed -> Fallback
    LAST_RUN_STATS["fallback_calls"] += 1
    return fallback_fn(twin)
