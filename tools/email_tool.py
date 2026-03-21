import os
import logging
import smtplib
import socket
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
        self.smtp_timeout = int(os.getenv("SMTP_TIMEOUT", "15"))
        self.configured = bool(self.smtp_user and self.smtp_pass)

        if self.configured:
            logger.info("EmailTool initialized with SMTP credentials")
        else:
            logger.warning("EmailTool: Missing SMTP credentials - dry-run mode")

    def _build_message(self, to: str, subject: str, body: str, html: str = None) -> MIMEMultipart:
        msg = MIMEMultipart("alternative")
        msg["From"] = self.from_email
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        if html:
            msg.attach(MIMEText(html, "html"))
        return msg

    def _send_via_smtp(self, port: int, msg: MIMEMultipart) -> None:
        use_ssl = port == 465
        if use_ssl:
            with smtplib.SMTP_SSL(self.smtp_host, port, timeout=self.smtp_timeout) as server:
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            return

        with smtplib.SMTP(self.smtp_host, port, timeout=self.smtp_timeout) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(self.smtp_user, self.smtp_pass)
            server.send_message(msg)

    def send(self, to: str, subject: str, body: str, html: str = None) -> dict:
        """Send an email."""
        if not self.configured:
            logger.info(f"[DRY-RUN] Email to {to}: {subject}")
            return {
                "status": "dry-run",
                "to": to,
                "subject": subject,
                "message": "Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM.",
            }

        msg = self._build_message(to, subject, body, html)
        ports_to_try = [self.smtp_port]
        for p in (587, 2525, 465):
            if p not in ports_to_try:
                ports_to_try.append(p)

        last_error = None
        for port in ports_to_try:
            try:
                self._send_via_smtp(port, msg)
                logger.info(f"Email sent to {to} | Subject: {subject} | Port: {port}")
                return {"status": "sent", "to": to, "subject": subject, "port": port}
            except (socket.timeout, TimeoutError) as e:
                last_error = f"timeout on port {port}: {e}"
                logger.warning(f"Email timeout on {self.smtp_host}:{port} -> {e}")
            except Exception as e:
                last_error = f"{type(e).__name__} on port {port}: {e}"
                logger.warning(f"Email attempt failed on {self.smtp_host}:{port} -> {e}")

        logger.error(f"Email failed to {to}: {last_error}")
        return {"status": "error", "to": to, "error": last_error or "unknown email error"}

    def send_bulk(self, recipients: list[dict]) -> list[dict]:
        return [self.send(**r) for r in recipients]
