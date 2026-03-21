import os
import logging
from twilio.rest import Client

logger = logging.getLogger("svos.tools.whatsapp")


class WhatsAppTool:
    """Send real WhatsApp messages via Twilio API."""

    name = "whatsapp"
    description = "Send WhatsApp messages to real phone numbers"
    allowed_roles = ["CEO", "CMO", "COO"]

    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.from_number = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
        self.client = None

        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)
            logger.info("WhatsAppTool initialized with Twilio credentials")
        else:
            logger.warning("WhatsAppTool: Missing Twilio credentials - will run in dry-run mode")

    def send(self, to: str, body: str) -> dict:
        """
        Send a WhatsApp message.

        Args:
            to: Phone number with country code, e.g. '+966501234567'
            body: Message text

        Returns:
            dict with status, sid, and message
        """
        to_whatsapp = f"whatsapp:{to}" if not to.startswith("whatsapp:") else to

        if not self.client:
            logger.info(f"[DRY-RUN] WhatsApp to {to}: {body[:80]}...")
            return {
                "status": "dry-run",
                "sid": None,
                "to": to,
                "body_preview": body[:80],
                "message": "No Twilio credentials configured. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM.",
            }

        try:
            message = self.client.messages.create(
                from_=self.from_number,
                body=body,
                to=to_whatsapp
            )
            logger.info(f"WhatsApp sent to {to} | SID: {message.sid} | Status: {message.status}")
            return {
                "status": message.status,
                "sid": message.sid,
                "to": to,
                "body_preview": body[:80]
            }
        except Exception as e:
            logger.error(f"WhatsApp send failed to {to}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "to": to
            }

    def send_bulk(self, recipients: list[dict]) -> list[dict]:
        """
        Send WhatsApp to multiple recipients.

        Args:
            recipients: list of {'to': '+966...', 'body': '...'}

        Returns:
            list of send results
        """
        results = []
        for r in recipients:
            result = self.send(to=r["to"], body=r["body"])
            results.append(result)
        return results
