import os


class EmailTool:
    """يرسل إيميل — يستخدمه Sales Agent وCMO"""

    name = "send_email"
    description = "Send an email via SMTP"

    def __init__(self):
        self.host = os.getenv("SMTP_HOST", "")
        self.port = int(os.getenv("SMTP_PORT", "587") or "587")
        self.user = os.getenv("SMTP_USER", "")
        self.password = os.getenv("SMTP_PASS", "")
        self.sender = os.getenv("SMTP_FROM", self.user)

    async def execute(self, to: str, subject: str, body: str) -> dict:
        """
        يرسل إيميل عبر SMTP (aiosmtplib).
        """
        required = [self.host, self.port, self.sender]
        if not all(required):
            return {
                "sent": False,
                "to": to,
                "subject": subject,
                "error": "Missing SMTP settings: SMTP_HOST/SMTP_PORT/SMTP_FROM",
            }

        try:
            import aiosmtplib  # type: ignore
        except Exception:
            return {
                "sent": False,
                "to": to,
                "subject": subject,
                "error": "aiosmtplib is not installed. Run: pip install aiosmtplib",
            }

        try:
            msg = (
                f"From: {self.sender}\r\n"
                f"To: {to}\r\n"
                f"Subject: {subject}\r\n"
                "Content-Type: text/plain; charset=utf-8\r\n"
                "\r\n"
                f"{body}"
            )

            await aiosmtplib.send(
                msg,
                hostname=self.host,
                port=self.port,
                username=self.user or None,
                password=self.password or None,
                start_tls=True,
            )
            return {"sent": True, "to": to, "subject": subject, "error": None}
        except Exception as e:
            return {"sent": False, "to": to, "subject": subject, "error": str(e)}
