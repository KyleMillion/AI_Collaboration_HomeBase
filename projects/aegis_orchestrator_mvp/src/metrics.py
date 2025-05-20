from prometheus_client import Counter, Histogram, start_http_server
import time, os

REQUEST_COUNT = Counter('agent_task_total', 'Total tasks executed', ['task_id'])
REQUEST_LATENCY = Histogram('agent_task_duration_seconds', 'Task execution time', ['task_id'])
FLOW_OUTPUT_TOKEN_COUNT = Counter(
    'flow_output_token_count',
    'Number of output tokens for a given flow.',
    ['flow_id']
)

COST_ESTIMATE = Histogram(
    'flow_cost_usd',
    'Estimated compute/API cost per flow',
    ['flow_id']
)

def start_metrics_server(port: int = None):
    port = port or int(os.getenv("METRICS_PORT", "8000"))
    try:
        start_http_server(port)
        print(f"[Metrics] Prometheus exporter running on port {port}")
    except OSError as e:
        print(f"[Metrics Error] Could not start Prometheus exporter on port {port}: {e}. Port might be in use.")
        print("[Metrics Error] Ensure METRICS_PORT environment variable is set if default is taken.") 