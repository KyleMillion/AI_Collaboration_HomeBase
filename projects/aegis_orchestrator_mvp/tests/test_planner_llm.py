import unittest
from unittest.mock import patch, MagicMock
import json
import os
import sys

# Adjust path to import from src
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir) # This should be 'aegis_orchestrator_mvp'
src_path = os.path.join(project_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.agents.planner_agent import PlannerAgent

# Canned JSON response for mocking ChatOpenAI
CANNED_LLM_RESPONSE_JSON = {
    "id": "pipeline.test.onboard_user",
    "trigger_instruction": "Onboard a new user named Test User with email test@example.com",
    "tasks": [
        {
            "id": "task_1_create_user_account",
            "agent": "OktaAPI", 
            "params": {"username": "test@example.com", "displayName": "Test User"},
            "dependencies": []
        },
        {
            "id": "task_2_send_welcome_email",
            "agent": "EmailAPI",
            "params": {
                "to": "test@example.com", 
                "subject": "Welcome to Our Platform!", 
                "body": "Hello Test User, welcome!"
            },
            "dependencies": ["task_1_create_user_account"]
        },
        {
            "id": "task_3_notify_slack",
            "agent": "SlackAPI",
            "params": {"channel": "#new-users", "message": "New user onboarded: Test User (test@example.com)"},
            "dependencies": ["task_1_create_user_account"]
        }
    ]
}

CANNED_LLM_RESPONSE_STR = json.dumps(CANNED_LLM_RESPONSE_JSON)

class TestPlannerAgentLLM(unittest.TestCase):

    @patch('src.agents.planner_agent.ChatOpenAI')
    def test_invoke_llm_successful_parse(self, MockChatOpenAI):
        """Test PlannerAgent.invoke with a mock LLM that returns valid JSON."""
        # Configure the mock ChatOpenAI instance
        mock_llm_instance = MockChatOpenAI.return_value
        mock_response = MagicMock()
        mock_response.content = CANNED_LLM_RESPONSE_STR
        mock_llm_instance.invoke.return_value = mock_response # Updated to .invoke

        planner = PlannerAgent(model="gpt-test-mock") # Use a distinct model name for test
        prompt = "Onboard a new user named Test User with email test@example.com"
        
        # Set OPENAI_API_KEY in environment for the test context if not already set by .env
        # This ensures ChatOpenAI initializes correctly even if .env is not loaded in test setup path
        original_api_key = os.getenv("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = "test_api_key_for_planner_llm_test"
        
        try:
            result_graph = planner.invoke(prompt)
        finally:
            # Restore original API key if it was set, otherwise remove the test one
            if original_api_key is not None:
                os.environ["OPENAI_API_KEY"] = original_api_key
            else:
                del os.environ["OPENAI_API_KEY"]

        # Assertions
        MockChatOpenAI.assert_called_once_with(model_name="gpt-test-mock", temperature=0.1)
        mock_llm_instance.invoke.assert_called_once() # Check that the invoke method was called
        self.assertIsInstance(result_graph, dict)
        self.assertEqual(result_graph["id"], CANNED_LLM_RESPONSE_JSON["id"])
        self.assertEqual(len(result_graph["tasks"]), len(CANNED_LLM_RESPONSE_JSON["tasks"]))
        self.assertEqual(result_graph["tasks"][0]["agent"], CANNED_LLM_RESPONSE_JSON["tasks"][0]["agent"])

    @patch('src.agents.planner_agent.ChatOpenAI')
    def test_invoke_llm_json_decode_error_fallback(self, MockChatOpenAI):
        """Test PlannerAgent.invoke fallback when LLM returns non-JSON string."""
        mock_llm_instance = MockChatOpenAI.return_value
        mock_response = MagicMock()
        mock_response.content = "This is not JSON."
        mock_llm_instance.invoke.return_value = mock_response # Updated to .invoke

        planner = PlannerAgent(model="gpt-test-mock-fallback")
        prompt = "Do something complex that results in non-JSON"
        pipeline_id_for_test = "test_pipeline_json_error"

        original_api_key = os.getenv("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = "test_api_key_for_planner_llm_fallback_test"
        
        try:
            result_graph = planner.invoke(prompt, pipeline_id=pipeline_id_for_test)
        finally:
            if original_api_key is not None:
                os.environ["OPENAI_API_KEY"] = original_api_key
            else:
                del os.environ["OPENAI_API_KEY"]

        MockChatOpenAI.assert_called_once_with(model_name="gpt-test-mock-fallback", temperature=0.1)
        self.assertIsInstance(result_graph, dict)
        self.assertTrue(result_graph["id"].startswith("pipeline.fallback.echo_raw_response_for_"))
        self.assertEqual(len(result_graph["tasks"]), 1)
        self.assertEqual(result_graph["tasks"][0]["agent"], "SlackAPI")
        self.assertIn("Planner LLM Fallback", result_graph["tasks"][0]["params"]["message"])
        self.assertIn("This is not JSON.", result_graph["tasks"][0]["params"]["message"])

if __name__ == '__main__':
    unittest.main() 