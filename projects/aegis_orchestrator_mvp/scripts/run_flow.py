#!/usr/bin/env python
import requests
import json
import os
import sys

# Ensure src directory is in path for imports
# This assumes the script is run from a context where 'src' is a sibling of 'scripts' or in PYTHONPATH
# For n8n Execute Command, paths might need to be absolute or relative to /workspace (mapped volume)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR) # Should be aegis_orchestrator_mvp
SRC_PATH = os.path.join(PROJECT_ROOT, "src")

if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)
if PROJECT_ROOT not in sys.path: # To allow `from src...` if PROJECT_ROOT is the base for modules
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env")) # Load .env from project root

from src.agents.planner_agent import PlannerAgent
from src.orchestrator import build_flow, deploy # deploy might not be needed for direct execution
from prefect import flow as prefect_flow # For type hinting if needed

# Base URL for the Prefect Orion API (or Prefect Server/Cloud)
PREFECT_API_URL = os.getenv("PREFECT_API_URL", "http://localhost:4200/api") # Adjust if your Prefect API is elsewhere
DEPLOYMENT_ID = os.getenv("N8N_TARGET_DEPLOYMENT_ID") # Specific deployment to trigger

# Data passed from n8n (typically as JSON in the request body)
# n8n's HTTP Request node can send this as 'JSON/RAW Parameters'
input_data = sys.stdin.read()

try:
    params = json.loads(input_data)
except json.JSONDecodeError:
    print(json.dumps({"error": "Invalid JSON input", "received_data": input_data}))
    sys.exit(1)

if not DEPLOYMENT_ID:
    print(json.dumps({"error": "N8N_TARGET_DEPLOYMENT_ID environment variable not set."}))
    sys.exit(1)

api_endpoint = f"{PREFECT_API_URL}/deployments/{DEPLOYMENT_ID}/create_flow_run"

headers = {
    "Content-Type": "application/json"
}
# Add PREFECT_API_KEY if your server requires it
if os.getenv("PREFECT_API_KEY"):
    headers["Authorization"] = f'bearer {os.getenv("PREFECT_API_KEY")}'

# Construct the payload for creating a flow run
# The `parameters` field will be passed to your Prefect flow's parameters
# Ensure your Prefect flow is designed to accept these (e.g., a `graph` parameter)
payload = {
    "parameters": params, # Pass the full n8n output as parameters to the flow
    "state": {
        "type": "SCHEDULED",
        "message": "Flow run triggered by n8n webhook."
    }
    # Add other options like `name`, `tags` if needed
}

def main():
    """Entry point for the n8n webhook trigger script."""
    print("[run_flow.py] Starting execution...")

    prompt = os.getenv("BODY") # n8n will set this from the webhook body

    if not prompt:
        print("[run_flow.py] Error: No prompt received in BODY environment variable.")
        sys.exit(1)

    print(f"[run_flow.py] Received prompt: {prompt}")

    try:
        # 1. Get task graph from PlannerAgent
        print("[run_flow.py] Initializing PlannerAgent...")
        planner = PlannerAgent() # Uses OPENAI_API_KEY from .env via load_dotenv
        print("[run_flow.py] Invoking PlannerAgent...")
        graph_json = planner.invoke(prompt, pipeline_id=f"n8n_triggered_flow_for_{prompt[:20].replace(' ','_')}")
        print(f"[run_flow.py] PlannerAgent returned graph: {json.dumps(graph_json, indent=2)}")

        if not graph_json or not isinstance(graph_json, dict) or "tasks" not in graph_json:
            print("[run_flow.py] Error: PlannerAgent returned an invalid or empty graph.")
            # Potentially send a Slack message back with the error using a direct tool call if critical
            sys.exit(1)

        # 2. Build the Prefect flow from the graph
        print("[run_flow.py] Building Prefect flow...")
        # The build_flow function from orchestrator.py returns a Prefect flow object
        dynamic_prefect_flow = build_flow(graph_json)
        print(f"[run_flow.py] Prefect flow '{dynamic_prefect_flow.name}' built successfully.")

        # 3. Execute the flow directly
        # For n8n, we want to run this synchronously and get a result if possible, 
        # or at least kick it off.
        # Direct execution is simpler than `run_deployment` for this context.
        print(f"[run_flow.py] Executing Prefect flow '{dynamic_prefect_flow.name}'...")
        flow_run_result = dynamic_prefect_flow() # Execute the flow
        print(f"[run_flow.py] Flow '{dynamic_prefect_flow.name}' execution completed.")
        print(f"[run_flow.py] Flow run result: {flow_run_result}") # This will be the output of the flow

        # Output something that n8n can pick up (e.g., final status or key results)
        # n8n Execute Command node captures stdout.
        print(json.dumps({"status": "success", "flow_name": dynamic_prefect_flow.name, "result": flow_run_result}))

    except Exception as e:
        error_message = f"[run_flow.py] Error during execution: {str(e)}"
        print(error_message)
        # Output error in JSON format for n8n
        print(json.dumps({"status": "error", "message": error_message}))
        sys.exit(1)

if __name__ == "__main__":
    main() 