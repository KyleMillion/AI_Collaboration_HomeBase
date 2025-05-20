import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
from src.feedback import record as feedback_record

load_dotenv()


class SlackAPI:
    """Encapsulates Slack API interactions."""

    def __init__(self):
        self.client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
        self.default_channel = os.getenv("SLACK_DEFAULT_CHANNEL", "#general")

    def invoke(
        self,
        message: str,
        channel: str = None,
        pipeline_id: str = "N/A",
        variant: str = "N/A",
        **kwargs,
    ):
        target_channel = channel or self.default_channel
        tool_output = {}
        success_status = False
        error_message = None

        # Use effective_pipeline_id and effective_variant for feedback
        effective_pipeline_id = pipeline_id or "UnknownPipeline"
        effective_variant = variant or "UnknownVariant"

        try:
            response = self.client.chat_postMessage(
                channel=target_channel, text=message
            )
            tool_output["slack_response"] = response.data
            success_status = response.get("ok", False)
            if not success_status:
                error_message = response.get("error", "Unknown Slack API error")
                tool_output["error"] = error_message
        except SlackApiError as e:
            tool_output["error"] = str(e.response["error"])
            error_message = str(e.response["error"])
            success_status = False
        except Exception as e:
            tool_output["error"] = str(e)
            error_message = str(e)
            success_status = False

        # Record feedback
        try:
            feedback_record(
                pipeline_id=effective_pipeline_id,
                variant=effective_variant,
                success=success_status,
                tool_name="SlackAPI",
                inputs={"message": message, "channel": target_channel, **kwargs},
                output=tool_output,
                error_message=error_message,
            )
        except Exception as fb_error:
            # Log or handle feedback recording errors gracefully, e.g., if DB is unavailable
            print(f"[SlackAPI Feedback Error] {fb_error}")
            # Optionally, include this feedback error in the tool_output if critical
            # tool_output["feedback_error"] = str(fb_error)

        return tool_output
