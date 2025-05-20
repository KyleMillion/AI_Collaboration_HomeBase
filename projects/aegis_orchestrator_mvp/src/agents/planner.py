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
    from langchain.chat_models import ChatOpenAI # Corrected import
    from langchain.chains import LLMChain
    from langchain.prompts import PromptTemplate
    _HAS_LANGCHAIN = True
except ImportError:
    _HAS_LANGCHAIN = False

# --- Heuristic templates -------------------------------------------------

_PIPELINE_HEURISTICS = [
    {
        "pattern": re.compile(r"\bonboard\b", re.I),
        "pipeline_id": "pipeline.onboarding.v0"
    },
    {
        "pattern": re.compile(r"\banaly(ze|sis)\b.*\bsales\b", re.I),
        "pipeline_id": "pipeline.analytics.v0"
    },
    {
        "pattern": re.compile(r"\bfeedback\b|\breview\b", re.I),
        "pipeline_id": "pipeline.feedback.v0"
    },
]

# --- LangChain prompt -----------------------------------------------------

_PROMPT_STR = """You are an AI planning assistant.
Break the following instruction into a JSON task graph.

Guidelines:
- Identify high‑level tasks and order them logically.
- For each task, assign a generic agent role (e.g. DataAgent, Writer, Validator).
- If a task maps to a known tool, specify it (e.g. FormAPI, SlackAPI, EmailAPI, CalendarAPI, SQLTool, PlotAPI, SurveyAPI, OktaAPI, CRMAPI).
- Output a JSON object with keys: id, tasks (list of objects {id, agent, tool, params}).

Instruction: {instruction}
"""

# --- Predefined Pipeline Definitions --------------------------------------
_PIPELINE_DEFINITIONS = {
    "pipeline.onboarding.v0": {
        "id": "pipeline.onboarding.v0",
        "description": "Handles new entity (employee/client) onboarding.",
        "tasks": [
            {"id": "collect_info", "agent": "DataGatherer", "tool": "FormAPI", "params": {"form_id": "onboarding_form"}},
            {"id": "provision_accounts", "agent": "Provisioner", "tool": ["OktaAPI", "SlackAPI", "CRMAPI"], "params": {"role_template": "standard_user"}, "parallel": True},
            {"id": "configure_settings", "agent": "Configurator", "tool": "CalendarAPI", "params": {"meeting_type": "orientation"}},
            {"id": "quality_check", "agent": "Validator", "tool": "PingCheck", "params": {}, "retry": 2},
            {"id": "send_notification", "agent": "Notifier", "tool": "EmailAPI", "params": {"template_id": "welcome_email"}}
        ],
        "post_hook": "survey.feedback.onboarding",
        "kpi": ["time_to_ready", "setup_errors", "feedback_score"]
    },
    "pipeline.analytics.v0": {
        "id": "pipeline.analytics.v0",
        "description": "Handles data analysis and reporting.",
        "tasks": [
            {"id": "plan_analysis", "agent": "Planner", "tool": None, "params": {}},
            {"id": "fetch_data", "agent": "DataAgent", "tool": "SQLTool", "params": {"query_template": "quarterly_sales"}},
            {"id": "analyze_data", "agent": "Analyst", "tool": "PandasExec", "params": {}}, # Assuming PandasExec is a conceptual tool for now
            {"id": "visualize_data", "agent": "Visualizer", "tool": "PlotAPI", "params": {}},
            {"id": "draft_report", "agent": "Writer", "tool": "LLMCompose", "params": {}}, # Assuming LLMCompose is a conceptual tool
            {"id": "review_report", "agent": "Reviewer", "tool": "CrossCheck", "params": {}} # Assuming CrossCheck is conceptual
        ],
        "kpi": ["report_latency", "accuracy_flag", "engagement_ctr"]
    },
    "pipeline.feedback.v0": {
        "id": "pipeline.feedback.v0",
        "description": "Handles feedback collection and processing.",
        "tasks": [
            {"id": "collect_feedback", "agent": "FeedbackCollector", "tool": "SurveyAPI", "params": {"survey_id": "general_feedback"}},
            {"id": "analyze_feedback", "agent": "FeedbackAnalyzer", "tool": "SentimentAnalysis", "params": {}}, # Conceptual
            {"id": "generate_report", "agent": "ReportGenerator", "tool": "LLMCompose", "params": {"report_type": "feedback_summary"}}
        ],
        "kpi": ["satisfaction_score", "common_issues_identified"]
    }
}

class Planner:
    """Planner agent produces task graphs from NL instructions."""

    def __init__(self, use_llm: bool = True, temperature: float = 0.2, llm_model_name: str = "gpt-4o-mini"):
        self.use_llm = use_llm and _HAS_LANGCHAIN
        if self.use_llm:
            # Ensure OPENAI_API_KEY is set in environment if using OpenAI models
            llm = ChatOpenAI(model_name=llm_model_name, temperature=temperature)
            prompt = PromptTemplate.from_template(_PROMPT_STR)
            self.chain = LLMChain(llm=llm, prompt=prompt)

    # ---------------------------------------------------------------------
    def heuristic_plan(self, instruction: str) -> Dict:
        """Use rule‑based matching to map to predefined pipeline."""
        for rule in _PIPELINE_HEURISTICS:
            if rule["pattern"].search(instruction):
                pipeline_id = rule["pipeline_id"]
                if pipeline_id in _PIPELINE_DEFINITIONS:
                    graph = _PIPELINE_DEFINITIONS[pipeline_id].copy() # Return a copy
                    graph["trigger_instruction"] = instruction
                    graph["generated_by"] = "heuristic"
                    graph["timestamp"] = datetime.utcnow().isoformat()
                    return graph
        # fallback generic
        return {
            "id": f"pipeline.generic.{uuid.uuid4().hex[:6]}",
            "trigger_instruction": instruction,
            "generated_by": "heuristic_fallback",
            "tasks": [
                {"id": "respond", "agent": "LLMResponder", "params": {"note": "No template match; manual design required"}}
            ],
            "timestamp": datetime.utcnow().isoformat()
        }

    # ---------------------------------------------------------------------
    def llm_plan(self, instruction: str) -> Dict:
        """Use LLM to decompose instruction into task graph."""
        if not self.use_llm:
            raise RuntimeError("LangChain/OpenAI not available or not configured for LLM planning.")
        try:
            result = self.chain.run(instruction=instruction).strip()
            graph = json.loads(result)
        except json.JSONDecodeError:
            # if the model didn't respond with JSON, wrap it for inspection
            graph = {
                "id": f"pipeline.llm_parse_error.{uuid.uuid4().hex[:6]}",
                "trigger_instruction": instruction,
                "generated_by": "llm_non_json_output",
                "raw_output": result
            }
        except Exception as e:
            # Catch other LLM or chain related errors
            graph = {
                "id": f"pipeline.llm_error.{uuid.uuid4().hex[:6]}",
                "trigger_instruction": instruction,
                "generated_by": "llm_exception",
                "error_details": str(e)
            }
        graph.setdefault("timestamp", datetime.utcnow().isoformat())
        return graph

    # ---------------------------------------------------------------------
    def plan(self, instruction: str) -> Dict:
        """Main entry — decide strategy."""
        if self.use_llm:
            try:
                return self.llm_plan(instruction)
            except Exception as e: # Fallback on any LLM planning error
                print(f"[Planner Warning] LLM planning failed: {e}. Falling back to heuristic plan.")
                pass # Fall through to heuristic_plan
        return self.heuristic_plan(instruction) 