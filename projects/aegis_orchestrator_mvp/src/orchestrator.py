"""Dynamic Orchestrator — converts task graph into Prefect flow and deploys."""
import json, inspect, types, importlib.util, pathlib, uuid
from typing import Dict
import time
import os

from prefect import flow, task, get_run_logger
from prefect.deployments import run_deployment

from . import risk # Assuming risk.py is in the same directory or accessible via python path
from .metrics import REQUEST_COUNT, REQUEST_LATENCY, FLOW_OUTPUT_TOKEN_COUNT, COST_ESTIMATE # Removed FLOW_INPUT_TOKEN_COUNT
from .feedback import record as feedback_record # Changed import
from .feedback import best_variant as feedback_best_variant # Added for A/B variant selection

# Dynamically import all tools from the .tools submodule
_TOOL_CLASSES = {}
try:
    from . import tools as tool_module # Relative import for tools submodule
    for tool_name in tool_module.__all__: # Relies on __all__ in tools/__init__.py
        _TOOL_CLASSES[tool_name] = getattr(tool_module, tool_name)
except ImportError as e:
    print(f"[Orchestrator Warning] Could not import tools submodule or specific tools: {e}")

# Add conceptual/placeholder tools not in dedicated files (if any)
_TOOL_CLASSES.update({
    "FormAPI": lambda **p: print(f"[Tool Stub] FormAPI invoked with {p}"), 
    "PingCheck": lambda **p: print(f"[Tool Stub] PingCheck invoked with {p}"),
    "PandasExec": lambda **p: print(f"[Tool Stub] PandasExec invoked with {p}"), 
    "LLMCompose": lambda **p: print(f"[Tool Stub] LLMCompose invoked with {p}"),
    "CrossCheck": lambda **p: print(f"[Tool Stub] CrossCheck invoked with {p}"), 
    "SentimentAnalysis": lambda **p: print(f"[Tool Stub] SentimentAnalysis invoked with {p}"),
})

# load adapters dynamically via registry
from . import registry

def _make_task(task_spec: Dict):
    task_id = task_spec["id"]
    agent_cls = task_spec["__agent_cls"]
    instance  = agent_cls()
    result    = instance.invoke(**task_spec.get("params", {}))
    print(f"[{task_id}] → {result}")

    @task(name=task_id)
    def generic_task_execution():
        with REQUEST_LATENCY.labels(task_id).time():
            REQUEST_COUNT.labels(task_id).inc()
            print(f"Executing task_id: {task_id} with agent: {agent_cls.__name__}")
            
            if not result:
                print(f"  No result returned for task {task_id}.")
                return {"status": "no_result_returned"}

            return result
    return generic_task_execution

def _review_gate(instruction: str):
    @task(name="human_approval_gate") # Changed name for clarity
    def gate():
        score = risk.score_instruction(instruction)
        if risk.requires_review(score):
            print(f"[Review Gate] Risk score {score:.2f} >= threshold. Manual review would be required.")
            # In a real scenario, this might raise an error to halt the Prefect flow or send a notification.
            # For now, just printing the status.
            # raise Interruption(f"REVIEW REQUIRED — Risk score {score:.2f}. Escalate to human.")
            return {"status": "requires_review", "risk_score": score}
        else:
            print(f"[Review Gate] Risk score {score:.2f} < threshold. Auto‑approved.")
            return {"status": "auto_approved", "risk_score": score}
    return gate

def build_flow(graph: Dict):
    trigger_instruction = graph.get('trigger_instruction', 'No instruction provided')
    flow_id_for_feedback = graph.get("id", f"flow-{uuid.uuid4().hex[:6]}") # Capture flow_id for feedback
    
    # Determine the variant for this pipeline run
    # This variant will be passed to all tasks if not overridden by task-specific variant logic
    pipeline_level_variant = feedback_best_variant(flow_id_for_feedback)
    print(f"[Orchestrator] Using variant '{pipeline_level_variant}' for pipeline '{flow_id_for_feedback}'")

    # Create the review gate task first
    review_task_instance = _review_gate(trigger_instruction)
    
    tasks = {}
    for t in graph.get("tasks", []):
        agent_cls = registry.get(t["agent"])
        t["__agent_cls"] = agent_cls    # keep for runtime invocation
        
        # Set or override the variant for the task
        # Priority: task-specific variant > pipeline-level determined variant > "default" (if best_variant returns it)
        # For simplicity now, we'll just ensure "variant" is in params.
        # The agent/tool's invoke method is expected to pick up "variant" and "pipeline_id"
        if "params" not in t:
            t["params"] = {}
        t["params"].setdefault("variant", pipeline_level_variant)
        t["params"].setdefault("pipeline_id", flow_id_for_feedback) # Ensure pipeline_id is also passed

        tasks[t["id"]] = _make_task(t)

    @flow(name=graph.get("id", f"flow-{uuid.uuid4().hex[:6]}"))
    def dynamic_flow():
        import time # Ensure time is imported
        start_time = time.time() # Record start time of the flow
        # pipeline_run_id = str(uuid.uuid4()) # Unique ID for this specific run; No longer directly passed to simplified feedback.record

        logger = get_run_logger()
        logger.info(f"Starting flow with graph: {graph}")

        # Initial feedback record for pipeline start
        try:
            feedback_record(
                pipeline_id=flow_id_for_feedback,
                variant=pipeline_level_variant, 
                success=True, 
                tool_name="PipelineStart", 
                inputs={"graph_id": graph.get("id", "unknown_graph"), "trigger_instruction": trigger_instruction}
            )
        except Exception as fb_error:
            logger.error(f"[Feedback Error] Could not record pipeline_start: {fb_error}")

        approval_result = review_task_instance() 
        
        # Naive linear execution, preserving order from the graph.
        # TODO: Implement conditional logic based on approval_result if needed.
        # TODO: Implement actual parallel task execution if specified in graph.
        
        all_task_outputs = {}
        flow_success = True # Assume success, set to False on error
        flow_error_message = None

        # if approval_result.get("status") == "auto_approved": # Example conditional logic
        for t_spec in graph.get("tasks", []):
            task_id = t_spec["id"]
            if task_id in tasks:
                try:
                    # Pass previous task outputs if needed (conceptual for now)
                    # Pass pipeline_id and variant to the task execution context if possible
                    # For now, tools handle this internally via their invoke signature
                    all_task_outputs[task_id] = tasks[task_id]()
                    if isinstance(all_task_outputs[task_id], dict) and all_task_outputs[task_id].get("error"):
                        flow_success = False # If any task has an error, mark flow as failed
                        if not flow_error_message: flow_error_message = f"Error in task {task_id}"
                except Exception as task_exec_error:
                    logger.error(f"[Flow Error] Task {task_id} execution failed: {task_exec_error}")
                    all_task_outputs[task_id] = {"error": str(task_exec_error)}
                    flow_success = False
                    if not flow_error_message: flow_error_message = f"Exception in task {task_id}: {str(task_exec_error)}"
            else:
                logger.warning(f"[Flow Warning] Task ID {task_id} defined in graph but not generated or found in task instances.")
                # Consider if this should mark the flow as unsuccessful
                # flow_success = False 
                # if not flow_error_message: flow_error_message = f"Task {task_id} not found"

        duration = time.time() - start_time # Calculate duration
        # naive cost: $0.0005/sec as placeholder, now from env var
        cost_rate_per_sec = float(os.getenv("COST_RATE_PER_SEC", "0.0005"))
        COST_ESTIMATE.labels(flow_id=graph["id"]).observe(round(duration * cost_rate_per_sec, 4))
        logger.info(f"Flow completed. All task outputs: {all_task_outputs}")

        # Final feedback record for pipeline end
        try:
            feedback_record(
                pipeline_id=flow_id_for_feedback,
                variant=pipeline_level_variant, 
                success=flow_success,
                tool_name="PipelineEnd",
                output=all_task_outputs, # Pass the collected task outputs
                error_message=flow_error_message
                # No direct metrics field in feedback.record; could be part of output if needed
            )
        except Exception as fb_error:
            logger.error(f"[Feedback Error] Could not record pipeline_end: {fb_error}")

        return all_task_outputs

    return dynamic_flow

def deploy(graph: Dict, flows_dir: str = None):
    flow_obj = build_flow(graph)
    flows_dir_path = pathlib.Path(flows_dir or "flows")
    flows_dir_path.mkdir(parents=True, exist_ok=True)
    
    # Sanitize flow_id for use as a filename
    flow_id = graph.get('id', f"flow-{uuid.uuid4().hex[:6]}")
    safe_flow_id_filename = "".join(c if c.isalnum() or c in ('_', '-', '.') else '_' for c in flow_id) + ".py"
    file_path = flows_dir_path / safe_flow_id_filename
    
    # Construct the full source code for the deployable flow file
    flow_source_code = inspect.getsource(flow_obj)
    
    # Add necessary imports to the generated flow script
    # This is a basic approach; more robust dependency tracking might be needed
    imports_header = (
        "from prefect import flow, task\n"
        "import sys\n"
        "import os\n"
        "# Ensure src directory is in path for imports if running script directly\n"
        "sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))\n"
        "try:\n"
        "    from metrics import REQUEST_COUNT, REQUEST_LATENCY, start_metrics_server\n"
        "    from risk import score_instruction, requires_review\n"
        "    # Import tool classes (adjust relative path if orchestrator.py moves)\n"
        "    from tools import OktaAPI, SlackAPI, CRMAPI, CalendarAPI, EmailAPI, SQLTool, PlotAPI, SurveyAPI\n"
        "    # Add other direct tool imports or a dynamic loader if complex\n"
        "except ImportError as e:\n"
        "    print(f\"Error importing modules in generated flow: {e}. Ensure PYTHONPATH is correct.\")\n"
        "    # Define stubs if imports fail, to allow basic flow structure to run\n"
        "    def REQUEST_COUNT(*args, **kwargs): return type('DummyCounter', (), {'inc': lambda: None, 'labels': lambda *a, **k: REQUEST_COUNT})()\n"
        "    def REQUEST_LATENCY(*args, **kwargs): return type('DummyHistogram', (), {'time': lambda: type('DummyTimer', (), {'__enter__': lambda: None, '__exit__': lambda *a: None})(), 'labels': lambda *a, **k: REQUEST_LATENCY})()\n"
        "    def score_instruction(instr): return 0.0\n"
        "    def requires_review(score, threshold=0.6): return False\n"
        "    class OktaAPI: def invoke(self, **p): print(f'OktaAPI STUB: {p}'); return {}"
        "    # ... add stubs for all other tools as needed ...\n"
        "\n"
    )
    
    full_script_content = imports_header + flow_source_code
    
    with open(file_path, "w") as f:
        f.write(full_script_content)
    print(f"[Orchestrator] Flow '{flow_id}' written to: {file_path}")
    return str(file_path) 