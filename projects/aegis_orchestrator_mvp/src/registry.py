"""
Agent Registry
==============
• Central lookup for every agent/tool the orchestrator can invoke.
• Supports hot-swap upgrades while flows are running.

Manifest file: `agents.yaml` (same folder).
Yaml schema:
  - id: "SlackAPI"
    module: "tools.slack_api"
    classname: "SlackAPI"
    version: "0.1.0"
    status: "active"   # active | beta | deprecated
    default_params: {}

The registry exposes:
  get(agent_id)          -> returns loaded class (lazy import)
  upgrade(agent_id, ...) -> swap version & reload
  list(status="active")  -> iterate known agents
"""

from importlib import import_module
from pathlib import Path
import yaml, threading

_LOCK_TIMEOUT = 5 # seconds

# Path to the YAML file, relative to this script's location
_REG_PATH = Path(__file__).resolve().parent / "agents.yaml" # Corrected filename

_lock = threading.RLock()
_cache = {}       # agent_id -> class


def _load_manifest():
    if not _REG_PATH.exists():
        raise FileNotFoundError(f"Missing agent manifest {_REG_PATH}")
    with open(_REG_PATH) as f:
        return {d["id"]: d for d in yaml.safe_load(f)}


def get(agent_id: str):
    with _lock:
        if agent_id in _cache:
            return _cache[agent_id]
        manifest = _load_manifest().get(agent_id)
        if not manifest or manifest["status"] == "deprecated":
            raise KeyError(f"Agent '{agent_id}' not found/available")

        module_path = manifest["module"]
        class_name = manifest["classname"]
        
        # Ensure module path is absolute from project root perspective (e.g., src.tools.module)
        # The paths in agents.yaml are relative to src/ (e.g. tools.slack_api)
        # When registry.py is in src/, and tests add project_mvp_root to sys.path,
        # import_module needs "src.tools.slack_api"
        if not module_path.startswith("src."):
            full_module_path = f"src.{module_path}"
        else:
            full_module_path = module_path

        try:
            mod = import_module(full_module_path) # Use prepended path
            agent_class = getattr(mod, class_name)
            _cache[agent_id] = agent_class
            return agent_class
        except ImportError as e:
            raise ImportError(f"Could not import module {full_module_path} for agent {agent_id}: {e}")
        except AttributeError as e:
            raise AttributeError(f"Could not find class {class_name} in module {full_module_path} for agent {agent_id}: {e}")


def upgrade(agent_id: str, new_version: str, new_module: str = None, new_class: str = None):
    """
    Hot-swap an agent implementation.
    Gemini: write the persistence back to YAML then `get()` will reload next call.
    """
    with _lock:
        manifest = _load_manifest()
        item = manifest.get(agent_id) or {}
        item["version"] = new_version
        if new_module: item["module"] = new_module
        if new_class:  item["classname"] = new_class
        manifest[agent_id] = item
        with open(_REG_PATH, "w") as f:
            yaml.safe_dump(list(manifest.values()), f)
        _cache.pop(agent_id, None)   # clear cache 