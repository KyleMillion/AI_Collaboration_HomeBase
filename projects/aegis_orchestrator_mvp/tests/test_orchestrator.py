"""
Orchestrator integration smoke-tests (no real Prefect runtime needed).

Strategy
--------
1.  Create an in-memory dummy 'prefect' module that exposes
    no-op `flow` and `task` decorators plus a stub `get_run_logger`.
2.  Insert the dummy into `sys.modules` **before** importing `orchestrator`.
3.  Monkey-patch `registry.get()` so the Orchestrator uses mock
    agent classes with predictable behaviour.
"""

import sys, types, json, os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import sqlite3 # For re-opening connection

# ----------------------------------------------------------------------
# Adjust sys.path to include the parent of 'src' directory (i.e., aegis_orchestrator_mvp)
_current_file_dir = os.path.dirname(os.path.abspath(__file__)) # .../tests
_project_mvp_root_dir = os.path.dirname(_current_file_dir)    # .../aegis_orchestrator_mvp
if _project_mvp_root_dir not in sys.path:
    sys.path.insert(0, _project_mvp_root_dir)
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
# 1.  Dummy Prefect module
# Must be done AFTER sys.path adjustment if orchestrator imports prefect, 
# but BEFORE orchestrator import.
dummy_prefect = types.ModuleType("prefect")
dummy_prefect_deployments = types.ModuleType("prefect.deployments") # Create dummy deployments submodule

def _passthrough_deco(*d_args, **d_kwargs):
    """Return function unchanged (acts like @flow / @task)."""
    def real_deco(fn):
        return fn
    return real_deco

dummy_prefect.flow = _passthrough_deco
dummy_prefect.task = _passthrough_deco
dummy_prefect.get_run_logger = lambda: MagicMock()
dummy_prefect_deployments.run_deployment = MagicMock() # Add mock for run_deployment
dummy_prefect.deployments = dummy_prefect_deployments # Attach deployments submodule to prefect dummy

sys.modules["prefect"] = dummy_prefect
sys.modules["prefect.deployments"] = dummy_prefect_deployments # Add deployments submodule to sys.modules
# ----------------------------------------------------------------------

# Now safe to import orchestrator from src package
from src.orchestrator import build_flow, deploy # Updated import

# Import feedback module to manage its connection state for these tests
from src import feedback

# ----------------------------------------------------------------------
class _MockAgent:
    """Minimal agent that records its params and returns success."""
    calls = []
    def __init__(self): ...
    def invoke(self, **params):
        _MockAgent.calls.append(params)
        return {"ok": True}

# ----------------------------------------------------------------------
def _simple_graph():
    """Return a task graph that calls one mock agent."""
    return {
        "id": "pipeline.test.unit",
        "tasks": [
            {"id": "t1", "agent": "MockAgent", "params": {"x": 1}}
        ],
        "trigger_instruction": "unit-test"
    }

# ----------------------------------------------------------------------
@pytest.fixture(autouse=True)
def ensure_feedback_db_connection():
    """Ensure the feedback database connection is open before each test and closes after."""
    # This path should align with how test_feedback.py sets it up or where feedback.py expects it.
    # Assuming TEST_DB_FILE is a convention or feedback.py has a configurable path.
    # For simplicity, using the same path logic as in test_feedback.py
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    data_path = os.path.join(project_root, "data")
    test_db_file_for_orchestrator_tests = os.path.join(data_path, "test_feedback.db") # Ensure this is the same DB file used by test_feedback

    # If feedback.con is closed or None, re-initialize it.
    # This is a simplistic check. A more robust way might involve checking `feedback.con.closed` if it were a pysqlite3 connection object
    # or just attempting to connect.
    try:
        # Check if connection is usable, e.g., by trying a simple query
        feedback.con.execute("SELECT 1 FROM ab_stats LIMIT 1").fetchone() 
    except (sqlite3.ProgrammingError, AttributeError, sqlite3.OperationalError) as e:
        # print(f"DEBUG: Orchestrator tests re-opening feedback DB: {e}")
        feedback.con = sqlite3.connect(test_db_file_for_orchestrator_tests)
        # Ensure schema exists if we just created/reconnected the DB
        # This might be redundant if test_feedback.py always leaves a schema-initialized DB
        feedback.con.executescript(feedback._schema)
        feedback.con.commit()
    
    yield # Run the test
    
    # No explicit close here, to let test_feedback.py's tearDownClass handle the final close and cleanup.
    # If test_orchestrator runs *after* test_feedback, this is an issue. 
    # The order of test file execution by pytest is not guaranteed unless specified.
    # A more robust solution involves a session-scoped fixture for DB setup/teardown.

# ----------------------------------------------------------------------
def test_build_and_run_flow(monkeypatch):
    _MockAgent.calls.clear()
    # Patch target updated to src.orchestrator.registry.get
    with patch("src.orchestrator.registry.get", return_value=_MockAgent):
        flow_fn = build_flow(_simple_graph())
        flow_fn()
        # The orchestrator now adds 'pipeline_id' and 'variant' to task params
        expected_params = {
            "x": 1,
            "pipeline_id": "pipeline.test.unit", # From _simple_graph
            "variant": "default" # Default from feedback.best_variant when no data
        }
        assert _MockAgent.calls == [expected_params]

# ----------------------------------------------------------------------
def test_deploy_creates_file(tmp_path, monkeypatch):
    _MockAgent.calls.clear()
    # Patch target updated to src.orchestrator.registry.get
    with patch("src.orchestrator.registry.get", return_value=_MockAgent):
        graph = _simple_graph()
        file_path = deploy(graph, flows_dir=tmp_path)
        assert Path(file_path).exists()
        assert "def dynamic_flow" in Path(file_path).read_text() 