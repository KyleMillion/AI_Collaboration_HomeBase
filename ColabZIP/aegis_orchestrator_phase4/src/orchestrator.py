"""Dynamic Orchestrator — converts task graph into Prefect flow and deploys."""
import json, inspect, types, importlib.util, pathlib, uuid
from typing import Dict
from prefect import flow, task
import json
from . import risk
from .metrics import REQUEST_COUNT, REQUEST_LATENCY

# Attempt to import all known tools
# This is a simple approach; a more robust plugin system might be needed for many tools
_TOOL_CLASSES = {}
try:
    from ..tools import okta_api, slack_api, crm_api, calendar_api, email_api, sql_tool, plot_api, survey_api
    _TOOL_CLASSES = {
        "OktaAPI": okta_api.OktaAPI,
        "SlackAPI": slack_api.SlackAPI,
        "CRMAPI": crm_api.CRMAPI,
        "CalendarAPI": calendar_api.CalendarAPI,
        "EmailAPI": email_api.EmailAPI,
        "SQLTool": sql_tool.SQLTool,
        "PlotAPI": plot_api.PlotAPI,
        "SurveyAPI": survey_api.SurveyAPI,
        # Conceptual/Placeholder tools for now
        "FormAPI": lambda: print("[Tool Stub] FormAPI invoked"), 
        "PingCheck": lambda: print("[Tool Stub] PingCheck invoked"),
        "PandasExec": lambda: print("[Tool Stub] PandasExec invoked"),
        "LLMCompose": lambda: print("[Tool Stub] LLMCompose invoked"),
        "CrossCheck": lambda: print("[Tool Stub] CrossCheck invoked"),
        "SentimentAnalysis": lambda: print("[Tool Stub] SentimentAnalysis invoked"),
    }
except ImportError as e:
    print(f"[Orchestrator Warning] Could not import one or more tools: {e}")


def _make_task(task_spec):
    task_id = task_spec["id"]
    agent_name = task_spec.get("agent", "GenericAgent")
    tool_names = task_spec.get("tool")
    params = task_spec.get("params", {})

    @task(name=task_id)
    def generic():
        with REQUEST_LATENCY.labels(task_id).time():
            REQUEST_COUNT.labels(task_id).inc()
            print(f"Executing task_id: {task_id} with agent: {agent_name} and tool(s): {tool_names}")
            
            if not tool_names:
                print(f"  No tool specified for task {task_id}.")
                return

            # Handle single tool or list of tools (for parallel execution concept)
            if not isinstance(tool_names, list):
                tools_to_run = [tool_names]
            else:
                tools_to_run = tool_names

            results = []
            for tool_name in tools_to_run:
                if tool_name in _TOOL_CLASSES:
                    try:
                        tool_instance = _TOOL_CLASSES[tool_name]()
                        # Simplistic parameter passing for now
                        # Assumes invoke method can handle missing params or uses defaults
                        print(f"  Invoking tool: {tool_name} with params: {params}")
                        result = tool_instance.invoke(**params) if hasattr(tool_instance, 'invoke') else tool_instance()
                        results.append({tool_name: result})
                        print(f"  Tool {tool_name} result: {result}")
                    except Exception as e:
                        print(f"  Error invoking tool {tool_name}: {e}")
                        results.append({tool_name: {"error": str(e)}})
                else:
                    print(f"  Tool {tool_name} not found in _TOOL_CLASSES.")
                    results.append({tool_name: {"error": "Tool not found"}})
            return results
    return generic

def build_flow(graph: Dict):
    tasks = {}
    for t in graph.get("tasks", []):
        tasks[t["id"]] = _make_task(t)

    @flow(name=graph.get("id", f"flow-{uuid.uuid4().hex[:6]}"))
    def dynamic_flow():
        # naive linear execution preserve order
        for t in graph.get("tasks", []):
            tasks[t["id"]]()
    return dynamic_flow

def deploy(graph: Dict, flows_dir: str = None):
    flow_obj = build_flow(graph)
    # Serialize as script file for Prefect CLI
    flows_dir = pathlib.Path(flows_dir or "flows")
    flows_dir.mkdir(parents=True, exist_ok=True)
    file_path = flows_dir/ f"{graph.get('id','flow')}.py"
    source = inspect.getsource(flow_obj)
    with open(file_path, "w") as f:
        f.write(source)
    return file_path
def _review_gate(instruction: str):
    @task(name="human_approval")
    def gate():
        score = risk.score_instruction(instruction)
        if risk.requires_review(score):
            raise RuntimeError(f"✅ REVIEW REQUIRED — Risk score {score:.2f}. Escalate to human.")
        else:
            print(f"[Review] Risk score {score:.2f} — auto‑approved.")
    return gate
