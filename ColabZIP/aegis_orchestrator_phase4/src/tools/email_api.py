import os, smtplib
from email.message import EmailMessage


class EmailAPI:
    """SMTP email adapter (uses env credentials)."""

    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_pass = os.getenv("SMTP_PASS")

    def invoke(self, subject: str, body: str, to: str):
        if not all([self.smtp_host, self.smtp_user, self.smtp_pass]):
            raise ValueError("SMTP credentials not configured")
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.smtp_user
        msg["To"] = to
        msg.set_content(body)
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as s:
            s.starttls()
            s.login(self.smtp_user, self.smtp_pass)
            s.send_message(msg)
        return {"status": "sent", "to": to}
