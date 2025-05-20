class SQLTool:
    """Adapter for SQLTool. Provides a unified invoke() interface."""

    def __init__(self, credentials: dict | None = None):
        self.credentials = credentials or {}

    def invoke(self, **params):
        # TODO: Implement API interaction
        print(f"[SQLTool] invoked with", params)
        # Return dummy response
        return {"status": "ok", "detail": "stub response"}