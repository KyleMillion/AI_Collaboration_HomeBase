"""Example Prefect flow to verify infrastructure and basic orchestration concepts."""
from prefect import flow, task
import sys
import os
import json

# Ensure src directory is in path for imports when running this flow directly
# This helps locate the orchestrator and other modules if the CWD is the project root or flows/
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '../src'))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

@task
def initial_setup_task():
    print("Performing initial setup checks or tasks...")
    # Example: Check for environment variables or configurations
    required_vars = ["OPENAI_API_KEY", "SLACK_WEBHOOK_URL"] # Add more as needed
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"[Hello Flow - WARNING] Missing environment variables: {missing_vars}. Some tools might not work.")
    else:
        print("[Hello Flow] Required environment variables seem to be present.")
    return {"setup_status": "complete", "missing_vars": missing_vars}

@task
def report_generation_task(setup_info: dict):
    print(f"Reporting generation based on setup: {setup_info}")
    # This task could later be replaced by a call to the orchestrator with a specific plan
    return {"report_status": "generated"}

@flow(name="hello_aegis_orchestrator_flow")
def hello_flow():
    print("Hello from Aegis Orchestrator MVP! This flow demonstrates basic structure.")
    
    # Start metrics server if not already started (conceptual)
    # In a real deployment, metrics server would run as a separate process or on app startup.
    # from metrics import start_metrics_server
    # start_metrics_server() # Be cautious with this in a flow, might be better in main script

    setup_results = initial_setup_task()
    report_results = report_generation_task(setup_results)
    
    print(f"Flow complete. Setup: {setup_results}, Report: {report_results}")

if __name__ == "__main__":
    # This allows running the flow directly using `python flows/hello_flow.py`
    # It will also allow Prefect to discover and register it.
    hello_flow() # For direct execution
    
    # Example of using the orchestrator directly (for testing purposes)
    # Ensure you are in the project root directory or have PYTHONPATH set correctly for these imports
    print("\n--- Testing Orchestrator directly --- ")
    try:
        from agents import Planner
        from orchestrator import deploy

        print("Initializing Planner (heuristic mode)...")
        planner = Planner(use_llm=False) # Set use_llm=True and ensure OPENAI_API_KEY is set to test LLM planning
        
        instruction = "onboard new employee John Doe"
        print(f"Planning for instruction: '{instruction}'")
        graph = planner.plan(instruction)
        print(f"Generated graph: {json.dumps(graph, indent=2)}")
        
        print("Deploying graph to a Prefect flow script...")
        flow_file_path = deploy(graph, flows_dir="./projects/aegis_orchestrator_mvp/flows") # Ensure this path is correct relative to execution
        print(f"Orchestrator deployed flow to: {flow_file_path}")
        print(f"You can now try running: prefect deploy {flow_file_path}")
        print(f"Or, if Prefect server is running, execute: python {flow_file_path}")

    except ImportError as e:
        print(f"Could not run orchestrator test from hello_flow.py: {e}")
        print("Ensure you are in the project root or PYTHONPATH includes the 'src' directory.")
    except Exception as e:
        print(f"An error occurred during orchestrator test: {e}") 