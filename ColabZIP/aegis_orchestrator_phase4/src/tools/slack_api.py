import os, json, requests

class SlackAPI:
    """Simple Slack adapter using Incoming Webhooks."""

    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")

    def invoke(self, **params):
        if not self.webhook_url:
            raise ValueError("Slack webhook URL not set")
        text = params.get("text") or params.get("message") or "Hello from Aegis!"
        payload = {"text": text}
        resp = requests.post(self.webhook_url, json=payload, timeout=5)
        resp.raise_for_status()
        return {"status": "ok", "slack_ts": json.loads(resp.text).get("ts")}