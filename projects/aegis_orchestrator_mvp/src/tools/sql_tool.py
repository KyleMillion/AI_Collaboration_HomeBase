import os, sqlite3
import pandas as pd # Ensure pandas is listed in requirements.txt
from src.feedback import record as feedback_record # Changed from ..feedback and aliased

class SQLTool:
    """Lightweight SQLite adapter for analytics demos."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or os.getenv("SQLITE_DB_PATH", "./aegis_demo.db") # Default to local file
        # Connection is established in invoke to ensure it's fresh and thread-safe if used in threaded env

    def invoke(self, query: str, pipeline_id: str = "N/A", variant: str = "N/A", **kwargs): # Updated signature
        tool_output = {}
        success_status = False
        error_message = None
        
        try:
            # Ensure DB path directory exists if not using in-memory
            if self.db_path != ":memory:":
                db_dir = os.path.dirname(self.db_path)
                if db_dir and not os.path.exists(db_dir):
                    os.makedirs(db_dir)
            
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                # For SELECT queries, return DataFrame. For others (INSERT, UPDATE, DELETE), return status.
                if query.strip().upper().startswith("SELECT"):
                    df = pd.read_sql_query(query, conn)
                    # Convert DataFrame to a more universally serializable format (list of dicts)
                    tool_output = {"status": "ok", "data": df.to_dict(orient="records")}
                    success_status = True
                else:
                    cursor = conn.cursor()
                    cursor.execute(query)
                    conn.commit()
                    tool_output = {"status": "ok", "rows_affected": cursor.rowcount}
                    success_status = True
        except Exception as e:
            print(f"[SQLTool Error] Failed to execute query '{query}': {e}")
            tool_output = {"error": str(e), "query": query}
            error_message = str(e)
            success_status = False
            
        # Record feedback
        try:
            # For data, maybe summarize if too large, or indicate size
            output_for_feedback = tool_output
            if success_status and "data" in tool_output and isinstance(tool_output["data"], list):
                if len(tool_output["data"]) > 5: # Arbitrary limit for verbosity
                     output_for_feedback = {**tool_output, "data": f"{len(tool_output['data'])} rows returned (sample: {tool_output['data'][:2]}...)"}

            feedback_record(
                pipeline_id=pipeline_id,
                variant=variant,
                tool_name="SQLTool",
                inputs={"query": query, **kwargs},
                output=output_for_feedback,
                success=success_status,
                error_message=error_message
            )
        except Exception as fb_error:
            print(f"[SQLTool Feedback Error] Could not record feedback: {fb_error}")
            
        return tool_output 