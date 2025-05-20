import os


class OktaAPI:
    """Adapter for Okta API. (STUB)"""

    def __init__(self, credentials: dict | None = None):
        self.credentials = credentials or {}
        print(
            "[OktaAPI STUB] Initialized. Ensure Okta env vars/creds are set for real implementation."
        )

    def invoke(self, **params):
        action = params.get("action", "get_user")
        user_id = params.get("user_id")
        print(f"[OktaAPI STUB] Invoked with action: {action}, params: {params}")
        # TODO: Implement actual Okta API interaction based on action
        return {
            "status": "ok",
            "detail": f"OktaAPI STUB: action '{action}' on user '{user_id}' simulated.",
        }
