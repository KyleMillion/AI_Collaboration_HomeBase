"""Planner Agent — converts NLP directives into JSON task graphs.

Design:
  1. Simple keyword / regex heuristic to map instructions to pipeline templates.
     (Acts as a fallback if LLM is unavailable.)
  2. Optional LangChain LLMChain for open‑ended decomposition.
  3. Returns a task graph dict consumable by the Orchestrator.
"""

import re, json, uuid
from datetime import datetime
from typing import Dict, List

try:
    from langchain.chat_models import ChatOpenAI
    from langchain.chains import LLMChain
    from langchain.prompts import PromptTemplate

    _HAS_LANGCHAIN = True
except ImportError:
    _HAS_LANGCHAIN = False

# --- Heuristic templates -------------------------------------------------

_PIPELINE_HEURISTICS = [
    {
        "pattern": re.compile(r"\bonboard\b", re.I),
        "pipeline_id": "pipeline.onboarding.v0",
    },
    {
        "pattern": re.compile(r"\banaly(ze|sis)\b.*\bsales\b", re.I),
        "pipeline_id": "pipeline.analytics.v0",
    },
    {
        "pattern": re.compile(r"\bfeedback\b|\breview\b", re.I),
        "pipeline_id": "pipeline.feedback.v0",
    },
]

# --- LangChain prompt -----------------------------------------------------

_PROMPT_STR = """You are an AI planning assistant.
Break the following instruction into a JSON task graph.

Guidelines:
- Identify high‑level tasks and order them logically.
- For each task, assign a generic agent role (e.g. DataAgent, Writer, Validator).
- Output a JSON object with keys: id, tasks (list of objects {id, agent, params}).

Instruction: {instruction}
"""


class Planner:
    """Planner agent produces task graphs from NL instructions."""

    def __init__(self, use_llm: bool = True, temperature: float = 0.2):
        self.use_llm = use_llm and _HAS_LANGCHAIN
        if self.use_llm:
            llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=temperature)
            prompt = PromptTemplate.from_template(_PROMPT_STR)
            self.chain = LLMChain(llm=llm, prompt=prompt)

    # ---------------------------------------------------------------------
    def heuristic_plan(self, instruction: str) -> Dict:
        """Use rule‑based matching to map to predefined pipeline."""
        for rule in _PIPELINE_HEURISTICS:
            if rule["pattern"].search(instruction):
                return {
                    "id": rule["pipeline_id"],
                    "trigger_instruction": instruction,
                    "generated_by": "heuristic",
                    "timestamp": datetime.utcnow().isoformat(),
                }
        # fallback generic
        return {
            "id": f"pipeline.generic.{uuid.uuid4().hex[:6]}",
            "trigger_instruction": instruction,
            "generated_by": "heuristic_fallback",
            "tasks": [
                {
                    "id": "respond",
                    "agent": "LLMResponder",
                    "params": {"note": "No template match; manual design required"},
                }
            ],
            "timestamp": datetime.utcnow().isoformat(),
        }

    # ---------------------------------------------------------------------
    def llm_plan(self, instruction: str) -> Dict:
        """Use LLM to decompose instruction into task graph."""
        if not self.use_llm:
            raise RuntimeError("LangChain/OpenAI not available in this environment.")
        result = self.chain.run(instruction=instruction).strip()
        try:
            graph = json.loads(result)
        except json.JSONDecodeError:
            # if the model didn't respond with JSON, wrap it
            graph = {
                "id": f"pipeline.llm.{uuid.uuid4().hex[:6]}",
                "trigger_instruction": instruction,
                "generated_by": "llm_non_json",
                "raw_output": result,
            }
        graph.setdefault("timestamp", datetime.utcnow().isoformat())
        return graph

    # ---------------------------------------------------------------------
    def plan(self, instruction: str) -> Dict:
        """Main entry — decide strategy."""
        if self.use_llm:
            try:
                return self.llm_plan(instruction)
            except Exception:
                # fallback to heuristic
                pass
        return self.heuristic_plan(instruction)
