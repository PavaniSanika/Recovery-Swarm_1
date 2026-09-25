"""Script to check Google Gemini LLM API connectivity, model name, token usage, and response time.

Usage:
    .\\backend\\.venv\\Scripts\\python.exe scripts/check_llm.py
"""

from pathlib import Path
import sys
import time
import os
from dotenv import load_dotenv

# Locate project root and backend/.env
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
backend_dir = project_root / "backend"
env_path = backend_dir / ".env"

if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

api_key = os.getenv("LLM_API_KEY", "").strip()
model_name = os.getenv("LLM_MODEL", "").strip()

if not api_key or api_key == "your_key_here":
    print("Status: FAILED")
    print("Error Type: MissingConfigError")
    print("Error Message: LLM_API_KEY is missing or placeholder in backend/.env")
    sys.exit(1)

if not model_name:
    print("Status: FAILED")
    print("Error Type: MissingConfigError")
    print("Error Message: LLM_MODEL is missing in backend/.env")
    sys.exit(1)

try:
    from google import genai
    from google.genai import types
    from google.genai import errors
except ImportError:
    print("Status: FAILED")
    print("Error Type: ImportError")
    print("Error Message: google-genai package is not installed.")
    sys.exit(1)

start_time = time.time()

try:
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model_name,
        contents="Reply with the single word OK",
        config=types.GenerateContentConfig(
            max_output_tokens=20,
        ),
    )
    elapsed = time.time() - start_time

    reply_text = response.text.strip() if response.text else ""
    
    prompt_tokens = 0
    candidates_tokens = 0
    total_tokens = 0

    if hasattr(response, "usage_metadata") and response.usage_metadata:
        prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
        candidates_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0
        total_tokens = getattr(response.usage_metadata, "total_token_count", 0) or (prompt_tokens + candidates_tokens)

    print("Status: SUCCESS")
    print(f"Model Used: {model_name}")
    print(f"Reply Text: {reply_text}")
    print(f"Token Usage: Input={prompt_tokens}, Output={candidates_tokens}, Total={total_tokens}")
    print(f"Elapsed Time: {elapsed:.2f} seconds")
    sys.exit(0)

except errors.APIError as e:
    print("Status: FAILED")
    print("Error Type: APIError")
    print(f"Error Message: Google GenAI API error ({e.code if hasattr(e, 'code') else 'API_ERROR'}).")
    sys.exit(1)

except Exception as e:
    print("Status: FAILED")
    print(f"Error Type: {type(e).__name__}")
    print(f"Error Message: API call failed ({type(e).__name__}).")
    sys.exit(1)
