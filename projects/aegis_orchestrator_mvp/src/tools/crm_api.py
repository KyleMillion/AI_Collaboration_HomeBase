import os


class CRMAPI:
    """Adapter for CRM API. (STUB)"""

    def __init__(self, credentials: dict | None = None):
        self.credentials = credentials or {}
        print(
            "[CRMAPI STUB] Initialized. Ensure CRM env vars/creds are set for real implementation."
        )

    def invoke(self, **params):
        action = params.get("action", "get_contact_details")
        contact_id = params.get("contact_id")
        print(f"[CRMAPI STUB] Invoked with action: {action}, params: {params}")
        # TODO: Implement actual CRM API interaction
        return {
            "status": "ok",
            "detail": f"CRMAPI STUB: action '{action}' on contact '{contact_id}' simulated.",
        }
