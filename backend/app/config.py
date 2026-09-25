"""Configuration loader for RECOVERY-SWARM.

Loads backend/thresholds.yaml and environment settings (.env).
"""

import os
from pathlib import Path
from typing import Any, Dict
import yaml
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

THRESHOLDS_PATH = BASE_DIR / "thresholds.yaml"


def load_thresholds(path: Path = THRESHOLDS_PATH) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Thresholds file not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class Config:
    def __init__(self, thresholds_path: Path = THRESHOLDS_PATH):
        self.thresholds: Dict[str, Any] = load_thresholds(thresholds_path)
        self.llm_api_key: str = os.getenv("LLM_API_KEY", "")
        self.llm_model: str = os.getenv("LLM_MODEL", "claude-3-5-sonnet-20241022")
        self.database_url: str = os.getenv("DATABASE_URL", "sqlite:///./recovery.db")
        self.fallback_mode: bool = (
            os.getenv("FALLBACK_MODE", "false").lower() == "true"
        )
        self.temperature: float = float(os.getenv("TEMPERATURE", "0.1"))


config = Config()
