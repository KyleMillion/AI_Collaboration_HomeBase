"""Initial Planner agent scaffold"""


class Planner:
    """Decomposes natural-language directives into task graphs."""

    def plan(self, instruction: str) -> dict:
        # TODO: integrate LangChain or AutoGen to parse instruction
        # For now, return a placeholder graph
        return {
            "instruction": instruction,
            "tasks": [{"id": "example", "agent": "ExampleAgent", "params": {}}],
        }
