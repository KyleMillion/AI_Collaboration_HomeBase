"""Dynamic Orchestrator — converts task graph into Prefect flow and deploys."""
import json, inspect, types, importlib.util, pathlib, uuid
from typing import Dict
from prefect import flow, task
from .metrics import REQUEST_COUNT, REQUEST_LATENCY


def _make_task(task_spec):
    @task(name=task_spec["id"])
    def generic():
        print(f"Executing {task_spec}")
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