"""
Lightweight reward & A/B tracker.
Writes results to Prometheus via custom metrics and
persists variant stats in `feedback.db` (SQLite).
"""

import sqlite3, time
from prometheus_client import Counter
from pathlib import Path # Added for Path

VARIANT_METRIC = Counter("variant_success_total",
                         "Success count per variant",
                         ["pipeline_id", "variant"])

# _DB = "/mnt/data/feedback.db" # This path might need to be configurable or relative to the project
_PROJECT_ROOT = Path(__file__).resolve().parent.parent # projects/aegis_orchestrator_mvp/
_DB_PATH = _PROJECT_ROOT / "data"
_DB_FILE = _DB_PATH / "feedback.db"

_schema = """
CREATE TABLE IF NOT EXISTS ab_stats (
  pipeline TEXT,
  variant  TEXT,
  success  INTEGER,
  failure  INTEGER,
  updated  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (pipeline, variant)
);
"""

# Ensure the directory for the SQLite DB exists
_DB_PATH.mkdir(parents=True, exist_ok=True)

con = sqlite3.connect(_DB_FILE)
con.execute(_schema)
con.commit()

# Ensure the connection is closed when the module is unloaded or program exits
# This is a bit tricky with global connections, but good practice to consider.
# For simple scripts, it might be okay, but for long-running apps, manage connections carefully.

def record(pipeline_id: str, variant: str, success: bool, tool_name: str = "N/A", inputs: dict = None, output: dict = None, error_message: str = None):
    """Records the outcome of a particular variant execution."""
    VARIANT_METRIC.labels(pipeline_id, variant).inc() # Prometheus metric
    
    # Ensure inputs/outputs are serializable if they are being stored or logged elsewhere in future.
    # For now, they are mostly for context.
    
    print(f"[Feedback Record] Pipeline: {pipeline_id}, Variant: {variant}, Success: {success}, Tool: {tool_name}")
    if error_message:
        print(f"[Feedback Record Error] {error_message}")

    with con: # SQLite database update
        cur = con.cursor()
        # Check if row exists
        cur.execute("SELECT success, failure FROM ab_stats WHERE pipeline = ? AND variant = ?", (pipeline_id, variant))
        row = cur.fetchone()

        if row:
            current_success = row[0]
            current_failure = row[1]
            if success:
                current_success += 1
            else:
                current_failure += 1
            cur.execute("""
                UPDATE ab_stats 
                SET success = ?, failure = ?, updated = CURRENT_TIMESTAMP
                WHERE pipeline = ? AND variant = ?
            """, (current_success, current_failure, pipeline_id, variant))
        else:
            # Insert new row
            if success:
                cur.execute("INSERT INTO ab_stats (pipeline, variant, success, failure) VALUES (?, ?, 1, 0)", (pipeline_id, variant))
            else:
                cur.execute("INSERT INTO ab_stats (pipeline, variant, success, failure) VALUES (?, ?, 0, 1)", (pipeline_id, variant))
        con.commit() # Explicit commit after insert/update

def best_variant(pipeline: str, default: str = "default") -> str:
    """
    Return the variant with highest success-rate (>=20 trials) or `default`.
    """
    # Ensure we use the global `con` established in the module.
    # No need to sqlite3.connect() here again if `con` is module-level.
    cur = con.execute(
        """SELECT variant,
                  success, failure,
                  (success * 1.0) / NULLIF(success + failure, 0) AS rate,
                  (success + failure)                            AS n
           FROM ab_stats
           WHERE pipeline = ?
           ORDER BY rate DESC, n DESC -- Added n DESC as a tie-breaker for high rates
           LIMIT 5""",
        (pipeline,),
    )
    rows = cur.fetchall()
    for v, s, f, r, n in rows:
        if n >= 20:        # only trust variants with enough data
            print(f"[Best Variant] For pipeline '{pipeline}', selected '{v}' (rate: {r:.2f}, trials: {n})")
            return v
    print(f"[Best Variant] For pipeline '{pipeline}', no variant met criteria. Defaulting to '{default}'. Found: {rows}")
    return default

# Example of how to potentially close the connection (can be tricky with web apps/long running services)
# import atexit
# def close_db():
#     if con:
#         con.close()
# atexit.register(close_db) 