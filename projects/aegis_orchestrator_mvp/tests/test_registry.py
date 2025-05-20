import unittest
from unittest.mock import patch, mock_open
import os
import sys
import yaml
import importlib  # Added for reload

# Adjust path to import from src
# This assumes tests are run from 'projects/aegis_orchestrator_mvp/' or 'AI_Collaboration_HomeBase/'
# If 'AI_Collaboration_HomeBase/', then 'projects.aegis_orchestrator_mvp.src' is needed
# If 'projects/aegis_orchestrator_mvp/', then 'src' is needed.

# Robustly add 'src' to sys.path, assuming 'tests' is sibling to 'src'
# and this test file is in 'tests'
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # This should be 'aegis_orchestrator_mvp'
src_path = os.path.join(project_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)
if project_root not in sys.path:  # For `from src.agents...` or `from src.tools...`
    sys.path.insert(0, project_root)

# Try to import, handling potential issues if structure is different than assumed
try:
    from src.registry import get, upgrade, _REG_PATH, _cache
    from src.tools.slack_api import SlackAPI
    from src.tools.email_api import EmailAPI
    from src.tools.sql_tool import SQLTool
    from src.agents.planner_agent import PlannerAgent
    import src.registry  # Ensure registry is imported to be reloaded
except ImportError as e:
    print(f"Error importing modules for test_registry.py: {e}")

    # Define stubs if imports fail, to allow basic test structure to be parsed
    class SlackAPI:
        pass

    class EmailAPI:
        pass

    class SQLTool:
        pass

    class PlannerAgent:
        pass

    def get(arg):
        return None

    def upgrade(arg1, arg2):
        pass

    _REG_PATH = ""
    _cache = {}

# Original content of agents.yaml for mocking _load_manifest
ORIGINAL_AGENTS_YAML_CONTENT = [
    {
        "id": "SlackAPI",
        "module": "tools.slack_api",
        "classname": "SlackAPI",
        "version": "0.1.0",
        "status": "active",
    },
    {
        "id": "EmailAPI",
        "module": "tools.email_api",
        "classname": "EmailAPI",
        "version": "0.1.0",
        "status": "active",
    },
    {
        "id": "SQLTool",
        "module": "tools.sql_tool",
        "classname": "SQLTool",
        "version": "0.1.0",
        "status": "active",
    },
    {
        "id": "PlannerAgent",
        "module": "agents.planner_agent",
        "classname": "PlannerAgent",
        "version": "0.1.0",
        "status": "active",
    },
]


class TestAgentRegistry(unittest.TestCase):

    def setUp(self):
        if "src.registry" in sys.modules:
            importlib.reload(sys.modules["src.registry"])
            self.registry_module = sys.modules["src.registry"]
            self.registry_module._cache.clear()
        else:
            # This case should ideally not happen if imports at top are correct
            # and sys.path is set up. Forcing an import here might be too late
            # or mask underlying issues. If this branch is hit, imports are broken.
            try:
                import src.registry

                self.registry_module = src.registry
                self.registry_module._cache.clear()
            except ImportError:
                self.registry_module = None  # Mark as unavailable
                print("Critical Error: src.registry could not be imported in setUp.")

    @patch("src.registry._load_manifest")
    def test_get_existing_agent_slack(self, mock_load_manifest):
        self.assertIsNotNone(self.registry_module, "Registry module not loaded")
        fresh_data_list = [dict(item) for item in ORIGINAL_AGENTS_YAML_CONTENT]
        mock_load_manifest.return_value = {d["id"]: d for d in fresh_data_list}
        agent_class = self.registry_module.get("SlackAPI")
        self.assertIsNotNone(agent_class, "get('SlackAPI') returned None")
        self.assertEqual(agent_class.__name__, "SlackAPI")

    @patch("src.registry._load_manifest")
    def test_get_existing_agent_email(self, mock_load_manifest):
        self.assertIsNotNone(self.registry_module, "Registry module not loaded")
        fresh_data_list = [dict(item) for item in ORIGINAL_AGENTS_YAML_CONTENT]
        mock_load_manifest.return_value = {d["id"]: d for d in fresh_data_list}
        agent_class = self.registry_module.get("EmailAPI")
        self.assertIsNotNone(agent_class, "get('EmailAPI') returned None")
        self.assertEqual(agent_class.__name__, "EmailAPI")

    @patch("src.registry._load_manifest")
    def test_get_existing_agent_sql(self, mock_load_manifest):
        self.assertIsNotNone(self.registry_module, "Registry module not loaded")
        fresh_data_list = [dict(item) for item in ORIGINAL_AGENTS_YAML_CONTENT]
        mock_load_manifest.return_value = {d["id"]: d for d in fresh_data_list}
        agent_class = self.registry_module.get("SQLTool")
        self.assertIsNotNone(agent_class, "get('SQLTool') returned None")
        self.assertEqual(agent_class.__name__, "SQLTool")

    @patch("src.registry._load_manifest")
    def test_get_existing_agent_planner(self, mock_load_manifest):
        self.assertIsNotNone(self.registry_module, "Registry module not loaded")
        fresh_data_list = [dict(item) for item in ORIGINAL_AGENTS_YAML_CONTENT]
        mock_load_manifest.return_value = {d["id"]: d for d in fresh_data_list}
        agent_class = self.registry_module.get("PlannerAgent")
        self.assertIsNotNone(agent_class, "get('PlannerAgent') returned None")
        self.assertEqual(agent_class.__name__, "PlannerAgent")
        # Check module FQN instead of identity due to potential reloads
        self.assertEqual(agent_class.__module__, "src.agents.planner_agent")
        # Original PlannerAgent imported at top of test file for type hinting/reference
        self.assertEqual(PlannerAgent.__module__, "src.agents.planner_agent")

    @patch("src.registry._load_manifest")
    def test_get_non_existent_agent(self, mock_load_manifest):
        self.assertIsNotNone(self.registry_module, "Registry module not loaded")
        fresh_data_list = [dict(item) for item in ORIGINAL_AGENTS_YAML_CONTENT]
        mock_load_manifest.return_value = {d["id"]: d for d in fresh_data_list}
        with self.assertRaises(KeyError):
            self.registry_module.get("NonExistentAgent")

    @patch("src.registry._load_manifest")
    def test_get_deprecated_agent(self, mock_load_manifest):
        self.assertIsNotNone(self.registry_module, "Registry module not loaded")
        fresh_data_list = [dict(item) for item in ORIGINAL_AGENTS_YAML_CONTENT]
        mock_manifest_data_for_test = {d["id"]: d for d in fresh_data_list}
        target_agent_id = "SlackAPI"
        mock_manifest_data_for_test[target_agent_id]["status"] = "deprecated"
        mock_load_manifest.return_value = mock_manifest_data_for_test
        with self.assertRaises(KeyError):
            self.registry_module.get(target_agent_id)

    @patch("src.registry._load_manifest")
    def test_get_caching(self, mock_load_manifest):
        self.assertIsNotNone(self.registry_module, "Registry module not loaded")
        fresh_data_list = [dict(item) for item in ORIGINAL_AGENTS_YAML_CONTENT]
        mock_load_manifest.return_value = {d["id"]: d for d in fresh_data_list}
        agent1 = self.registry_module.get("SlackAPI")
        agent2 = self.registry_module.get("SlackAPI")
        self.assertIs(agent1, agent2)
        mock_load_manifest.assert_called_once()

    @patch("yaml.safe_dump")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.registry._load_manifest")
    def test_upgrade_agent(self, mock_load_manifest, mock_file_open, mock_yaml_dump):
        self.assertIsNotNone(self.registry_module, "Registry module not loaded")
        initial_manifest_list = [dict(item) for item in ORIGINAL_AGENTS_YAML_CONTENT]
        mock_load_manifest.return_value = {d["id"]: d for d in initial_manifest_list}
        new_version = "0.2.0"
        new_module_path = "tools.slack_api_v2"
        self.assertIn("SlackAPI", mock_load_manifest.return_value)
        self.registry_module.upgrade(
            "SlackAPI", new_version, new_module=new_module_path
        )
        mock_yaml_dump.assert_called_once()
        written_data_list = mock_yaml_dump.call_args[0][0]
        written_data_map = {d["id"]: d for d in written_data_list}
        self.assertEqual(written_data_map["SlackAPI"]["version"], new_version)
        self.assertEqual(written_data_map["SlackAPI"]["module"], new_module_path)
        self.assertNotIn("SlackAPI", self.registry_module._cache)

    def test_reg_path_location(self):
        self.assertIsNotNone(self.registry_module, "Registry module not loaded")
        reg_path_obj = self.registry_module._REG_PATH.resolve()
        self.assertEqual(
            reg_path_obj.name,
            "agents.yaml",
            f"Filename should be agents.yaml, got {reg_path_obj.name}",
        )
        self.assertEqual(
            reg_path_obj.parent.name,
            "src",
            f"Parent dir should be src, got {reg_path_obj.parent.name}",
        )
        # Check if the grandparent directory is aegis_orchestrator_mvp
        self.assertEqual(
            reg_path_obj.parent.parent.name,
            "aegis_orchestrator_mvp",
            f"Grandparent should be aegis_orchestrator_mvp, got {reg_path_obj.parent.parent.name}",
        )

    # Add a test for list functionality if it's implemented in registry.py
    # def test_list_agents(self, mock_load_manifest):
    #     ...


if __name__ == "__main__":
    unittest.main()
