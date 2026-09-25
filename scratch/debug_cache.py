import os
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.models.schemas import TwinState
from app.agents.mobility import run_mobility_agent_llm
from app.agents.cache import CACHE_DIR, save_cached_response

os.environ["CACHE_MODE"] = "record"
os.environ["FALLBACK_MODE"] = "false"

scenarios_dir = PROJECT_ROOT / "data" / "scenarios"
with open(scenarios_dir / "meera_day4.json", "r", encoding="utf-8") as f:
    twin = TwinState(**json.load(f))

from app.workflow.debate import run_llm_debate
from app.agents.mobility import run_mobility_agent
from app.agents.inflammation import run_inflammation_agent
from app.agents.medication import rule_based_medication
from app.agents.sleep import rule_based_sleep
from unittest.mock import MagicMock

props = [
    run_mobility_agent(twin),
    run_inflammation_agent(twin),
    rule_based_medication(twin),
    rule_based_sleep(twin),
]
p_res = MagicMock(priority_scores={"mobility": 0.8, "inflammation": 0.7, "medication": 0.3, "sleep": 0.5})

print("Testing run_llm_debate stance calls...")
try:
    d_res = run_llm_debate(twin, props, p_res, fallback=False)
    print("Debate result stances count:", len(d_res.stances))
    for s in d_res.stances:
        print("  Stance:", s)
except Exception as e:
    import traceback
    print("Debate Exception:", type(e).__name__, e)
    traceback.print_exc()
    import traceback
    print("Direct LLM Exception:", type(e).__name__, e)
    traceback.print_exc()

