import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger("svos.tools.email")


class EmailTool:
    """Send real emails via SMTP."""

    name = "email"
    description = "Send emails with subject, body, and optional HTML"
    allowed_roles = ["CEO", "CMO", "COO", "CFO"]

    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_pass = os.getenv("SMTP_PASS", "")
        self.from_email = os.getenv("SMTP_FROM", self.smtp_user)
        self.configured = bool(self.smtp_user and self.smtp_pass)

        if self.configured:
            logger.info("EmailTool initialized with SMTP credentials")
        else:
            logger.warning("EmailTool: Missing SMTP credentials - dry-run mode")

    def send(self, to: str, subject: str, body: str, html: str = None) -> dict:
        """
        Send an email.

        Args:
            to: Recipient email
            subject: Email subject
            body: Plain text body
            html: Optional HTML body

        Returns:
            dict with status
        """
        if not self.configured:
            logger.info(f"[DRY-RUN] Email to {to}: {subject}")
            return {
                "status": "dry-run",
                "to": to,
                "subject": subject,
                "message": "Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM.",
            }

        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = self.from_email
            msg["To"] = to
            msg["Subject"] = subject

            msg.attach(MIMEText(body, "plain"))
            if html:
                msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)

            logger.info(f"Email sent to {to} | Subject: {subject}")
            return {"status": "sent", "to": to, "subject": subject}
        except Exception as e:
            logger.error(f"Email failed to {to}: {e}")
            return {"status": "error", "to": to, "error": str(e)}

    def send_bulk(self, recipients: list[dict]) -> list[dict]:
        """
        Send emails to multiple recipients.

        Args:
            recipients: list of {'to': '...', 'subject': '...', 'body': '...', 'html': '...(optional)'}
        """
        return [self.send(**r) for r in recipients]
