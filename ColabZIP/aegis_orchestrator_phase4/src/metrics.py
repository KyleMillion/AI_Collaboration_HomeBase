from prometheus_client import Counter, Histogram, start_http_server
import time, os

REQUEST_COUNT = Counter("agent_task_total", "Total tasks executed", ["task_id"])
REQUEST_LATENCY = Histogram(
    "agent_task_duration_seconds", "Task execution time", ["task_id"]
)


def start_metrics_server(port: int = None):
    port = port or int(os.getenv("METRICS_PORT", "8000"))
    start_http_server(port)
    print(f"[Metrics] Prometheus exporter running on port {port}")
