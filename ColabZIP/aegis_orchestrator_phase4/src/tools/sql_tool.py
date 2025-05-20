import os, sqlite3, pandas as pd

class SQLTool:
    """Lightweight SQLite adapter for analytics demos."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or os.getenv("SQLITE_DB_PATH", "/mnt/data/demo.db")
        self.conn = sqlite3.connect(self.db_path)

    def invoke(self, query: str):
        df = pd.read_sql_query(query, self.conn)
        return df