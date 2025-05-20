import json
import os
from dotenv import load_dotenv
from langchain_community.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

load_dotenv()

class PlannerAgent:
    """Agent that uses an LLM to generate a task graph from a high-level prompt."""
    _sys = SystemMessage(content="""
You are a task-graph planner. Given a high-level directive, you must convert it into a structured JSON object representing a sequence of tasks to be executed by an orchestration engine. 
Each task in the graph must have an 'id', an 'agent' (the class name of the agent/tool to use, e.g., 'SlackAPI', 'EmailAPI', 'SQLTool', 'PlannerAgent'), and 'params' (a dictionary of parameters for that agent). 
If the directive implies sub-planning or delegation, you can use 'PlannerAgent' as an agent for a task, with its 'prompt' parameter containing the sub-directive. 
Ensure the output is ONLY the JSON object, with no other text, preamble, or explanation. The root of the JSON object should have an 'id' (a descriptive pipeline name, e.g., 'pipeline.sales.quarterly_report') and a 'tasks' array. If the input prompt is simple and can be handled by a single existing tool, create a single-task graph. If the prompt seems to be a direct command that an existing tool can handle without planning, just output a graph with that single tool invocation. If the prompt is ambiguous or too complex to break down directly, you can use the 'EchoAgent' or 'SlackAPI' to return the raw prompt or ask for clarification. The available tools are: SlackAPI, EmailAPI, SQLTool, PlannerAgent.
""")

    def __init__(self, model="gpt-4o-mini", temp=0.1):
        # OPENAI_API_KEY will be picked up by ChatOpenAI from the environment via dotenv
        self.llm = ChatOpenAI(model_name=model, temperature=temp)

    def invoke(self, prompt: str, pipeline_id: str = "N/A", variant: str = "N/A", **kwargs) -> dict:
        # pipeline_id and variant are included for potential use in feedback or advanced logic, not directly used by LLM call here.
        # kwargs are also accepted for future flexibility.
        enriched_prompt = f"Directive: {prompt}\nAvailable Tools: SlackAPI, EmailAPI, SQLTool, PlannerAgent. Consider if the directive requires a multi-step plan or can be a single tool call. If it looks like a direct command for a tool, plan just that one tool. If complex, break it down. If it requires further planning, use PlannerAgent."
        
        print(f"[PlannerAgent] Invoking LLM with prompt: {enriched_prompt[:100]}...") # Log snippet
        
        try:
            resp = self.llm.invoke([self._sys, HumanMessage(content=enriched_prompt)]).content
            print(f"[PlannerAgent] LLM raw response: {resp[:100]}...") # Log snippet
            
            # Attempt to find JSON within potentially verbose LLM output
            # Look for the first '{' and the last '}'
            json_start = resp.find('{')
            json_end = resp.rfind('}')
            
            if json_start != -1 and json_end != -1 and json_start < json_end:
                json_str = resp[json_start : json_end+1]
                parsed_graph = json.loads(json_str)
                print(f"[PlannerAgent] Parsed graph: {str(parsed_graph)[:100]}...")
                return parsed_graph
            else:
                print("[PlannerAgent] LLM response was not valid JSON or not found. Falling back.")
                # Fallback: wrap in single-task graph to echo the raw response
                return {
                    "id": f"pipeline.fallback.echo_raw_response_for_{pipeline_id.replace('.', '_')}", 
                    "tasks":[{"id":"task.echo_raw_llm_response","agent":"SlackAPI","params":{"message":f"Planner LLM Fallback: Could not parse plan from LLM for prompt '{prompt}'. Raw LLM response: {resp}"}}]
                }

        except json.JSONDecodeError as e:
            print(f"[PlannerAgent] JSONDecodeError: {e}. Raw response: {resp}. Falling back.")
            # Fallback: wrap in single-task graph to echo the error and raw response
            return {
                "id": f"pipeline.fallback.json_decode_error_for_{pipeline_id.replace('.', '_')}", 
                "tasks":[{"id":"task.echo_json_error","agent":"SlackAPI","params":{"message":f"Planner LLM Error: Could not decode JSON from LLM for prompt '{prompt}'. Error: {e}. Raw LLM response: {resp}"}}]
            }
        except Exception as e:
            print(f"[PlannerAgent] Unexpected error: {e}. Falling back.")
            # Fallback for any other unexpected errors
            return {
                "id": f"pipeline.fallback.unexpected_error_for_{pipeline_id.replace('.', '_')}", 
                "tasks":[{"id":"task.echo_unexpected_error","agent":"SlackAPI","params":{"message":f"Planner LLM Unexpected Error: {e} for prompt '{prompt}'."}}]
            } 