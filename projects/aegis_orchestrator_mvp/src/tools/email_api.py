import os, smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from src.feedback import record as feedback_record

load_dotenv()

class EmailAPI:
    """SMTP email adapter (uses env credentials)."""

    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST")
        self.smtp_port = os.getenv("SMTP_PORT") # Keep as string, smtplib handles conversion
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_pass = os.getenv("SMTP_PASS")

    def invoke(self, subject: str, body: str, to: str, pipeline_id: str = "N/A", variant: str = "N/A", **kwargs): # Updated signature
        if not all([self.smtp_host, self.smtp_port, self.smtp_user, self.smtp_pass]):
            print("[EmailAPI Error] SMTP credentials not fully configured. Check SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS.")
            # Feedback for configuration error
            try:
                feedback_record(pipeline_id=pipeline_id, variant=variant, tool_name="EmailAPI", success=False, output={"error": "SMTP credentials not configured"}, error_message="SMTP credentials not fully configured")
            except Exception as fb_error:
                print(f"[EmailAPI Feedback Error] {fb_error}")
            return {"error": "SMTP credentials not configured"}
        
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.smtp_user
        msg["To"] = to
        msg.set_content(body)
        
        tool_output = {}
        success_status = False
        error_message = None

        try:
            # Convert port to int here, allowing for env var to be just digits or a service name
            port = int(self.smtp_port) if self.smtp_port.isdigit() else self.smtp_port
            with smtplib.SMTP(self.smtp_host, port, timeout=10) as s:
                s.starttls() # Consider making TLS conditional based on port/config
                s.login(self.smtp_user, self.smtp_pass)
                s.send_message(msg)
            print(f"[EmailAPI] Email sent to {to} with subject: {subject}")
            tool_output = {"status": "sent", "to": to, "subject": subject}
            success_status = True
        except Exception as e:
            print(f"[EmailAPI Error] Failed to send email: {e}")
            tool_output = {"error": str(e)}
            error_message = str(e)
            success_status = False
        
        # Record feedback
        try:
            feedback_record(
                pipeline_id=pipeline_id,
                variant=variant,
                tool_name="EmailAPI",
                inputs={"subject": subject, "body": "...", "to": to, **kwargs}, # body might be long
                output=tool_output,
                success=success_status,
                error_message=error_message
            )
        except Exception as fb_error:
            print(f"[EmailAPI Feedback Error] Could not record feedback: {fb_error}")
            
        return tool_output 