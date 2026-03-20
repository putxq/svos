import os
import re
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger("svos.email_tool")


class EmailTool:
    """
    يرسل إيميل — يستخدمه CMO, Sales Agent, وأي وكيل يحتاج تواصل.
    يدعم: نص عادي + HTML.
    """

    name = "send_email"
    description = "Send an email via SMTP (plain text or HTML)"

    def __init__(self):
        self.host = os.getenv("SMTP_HOST", "")
        self.port = int(os.getenv("SMTP_PORT", "587") or "587")
        self.user = os.getenv("SMTP_USER", "")
        self.password = os.getenv("SMTP_PASS", "")
        self.sender = os.getenv("SMTP_FROM", "") or self.user

    def _validate_email(self, email: str) -> bool:
        """تحقق بسيط من صيغة الإيميل."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email.strip()))

    def _check_config(self) -> str | None:
        """يتحقق إن الإعدادات موجودة ويرجع رسالة خطأ واضحة."""
        missing = []

        if not self.host:
            missing.append("SMTP_HOST")
        if not self.sender:
            missing.append("SMTP_FROM (or SMTP_USER)")

        if missing:
            return (
                f"Missing SMTP settings: {', '.join(missing)}.\n"
                f"Add to .env:\n"
                f"  SMTP_HOST=smtp.gmail.com\n"
                f"  SMTP_PORT=587\n"
                f"  SMTP_USER=your@email.com\n"
                f"  SMTP_PASS=your-app-password\n"
                f"  SMTP_FROM=your@email.com\n"
                f"\n"
                f"For Gmail: use App Password from https://myaccount.google.com/apppasswords"
            )

        return None

    async def execute(
        self,
        to: str,
        subject: str,
        body: str,
        html: str | None = None,
    ) -> dict:
        """
        يرسل إيميل عبر SMTP.
        - to: عنوان المستلم
        - subject: الموضوع
        - body: النص العادي
        - html: (اختياري) نسخة HTML
        """
        # Check config
        config_error = self._check_config()
        if config_error:
            return {"sent": False, "to": to, "subject": subject, "error": config_error}

        # Validate email
        if not self._validate_email(to):
            return {"sent": False, "to": to, "subject": subject, "error": f"Invalid email address: {to}"}

        # Check aiosmtplib
        try:
            import aiosmtplib
        except ImportError:
            return {
                "sent": False,
                "to": to,
                "subject": subject,
                "error": "aiosmtplib not installed. Run: pip install aiosmtplib",
            }

        try:
            # Build message
            if html:
                msg = MIMEMultipart("alternative")
                msg.attach(MIMEText(body, "plain", "utf-8"))
                msg.attach(MIMEText(html, "html", "utf-8"))
            else:
                msg = MIMEText(body, "plain", "utf-8")

            msg["From"] = self.sender
            msg["To"] = to
            msg["Subject"] = subject

            # Send
            await aiosmtplib.send(
                msg,
                hostname=self.host,
                port=self.port,
                username=self.user or None,
                password=self.password or None,
                start_tls=True,
            )

            logger.info(f"Email sent: to={to}, subject={subject}")
            return {"sent": True, "to": to, "subject": subject, "error": None}

        except aiosmtplib.SMTPAuthenticationError:
            return {
                "sent": False,
                "to": to,
                "subject": subject,
                "error": (
                    "SMTP authentication failed. Check SMTP_USER and SMTP_PASS.\n"
                    "For Gmail: use App Password, not your regular password."
                ),
            }

        except Exception as e:
            logger.error(f"Email failed: {e}")
            return {"sent": False, "to": to, "subject": subject, "error": str(e)}

    async def send_report(self, to: str, report_title: str, report_body: str) -> dict:
        """اختصار لإرسال تقارير الوكلاء."""
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #1a1a2e; color: #00d4ff; padding: 20px; text-align: center;">
                <h1 style="margin: 0;">SVOS Report</h1>
                <p style="margin: 5px 0; opacity: 0.8;">{report_title}</p>
            </div>
            <div style="padding: 20px; background: #f5f5f5;">
                <pre style="white-space: pre-wrap; font-size: 14px;">{report_body}</pre>
            </div>
            <div style="padding: 10px; text-align: center; color: #888; font-size: 12px;">
                Sent by SVOS — Sovereign Ventures Operating System
            </div>
        </div>
        """

        return await self.execute(
            to=to,
            subject=f"[SVOS] {report_title}",
            body=report_body,
            html=html,
        )
