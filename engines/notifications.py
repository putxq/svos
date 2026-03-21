"""
SVOS Notification Engine — Alerts and Events for the Customer.

Types: approval_needed, meeting_completed, review_done, cycle_summary, system_alert, hr_action
Storage: workspace/tenants/{customer_id}/notifications.json

Lightweight — no push, no email. Just stored alerts the dashboard reads.
Webhook support for external integrations (Zapier, n8n, Slack).
"""

import json
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("svos.notifications")

MAX_NOTIFICATIONS = 100


class NotificationEngine:
    """Manages notifications for a tenant."""

    def __init__(self, customer_id: str):
        self.customer_id = customer_id
        self._path = self._get_path()
        self._notifications = self._load()

    def _get_path(self) -> Path:
        from core.tenant import get_tenant_dir
        d = get_tenant_dir(self.customer_id)
        return d / "notifications.json"

    def _load(self) -> list[dict]:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text("utf-8"))
                return data if isinstance(data, list) else []
            except Exception:
                pass
        return []

    def _save(self):
        # Keep last N
        if len(self._notifications) > MAX_NOTIFICATIONS:
            self._notifications = self._notifications[-MAX_NOTIFICATIONS:]
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._notifications, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def add(
        self,
        type: str,
        title: str,
        message: str = "",
        data: dict = None,
        priority: str = "normal",  # low, normal, high, urgent
    ) -> dict:
        """Add a notification."""
        notif = {
            "id": f"notif_{uuid.uuid4().hex[:8]}",
            "type": type,
            "title": title[:200],
            "message": message[:500],
            "data": data or {},
            "priority": priority,
            "read": False,
            "created_at": datetime.utcnow().isoformat(),
        }
        self._notifications.append(notif)
        self._save()
        logger.info(f"Notification [{type}] for {self.customer_id}: {title[:50]}")
        return notif

    def get_unread(self) -> list[dict]:
        return [n for n in self._notifications if not n.get("read")]

    def get_all(self, limit: int = 50) -> list[dict]:
        return list(reversed(self._notifications[-limit:]))

    def mark_read(self, notification_id: str) -> bool:
        for n in self._notifications:
            if n["id"] == notification_id:
                n["read"] = True
                n["read_at"] = datetime.utcnow().isoformat()
                self._save()
                return True
        return False

    def mark_all_read(self) -> int:
        count = 0
        for n in self._notifications:
            if not n.get("read"):
                n["read"] = True
                n["read_at"] = datetime.utcnow().isoformat()
                count += 1
        if count:
            self._save()
        return count

    def get_summary(self) -> dict:
        unread = [n for n in self._notifications if not n.get("read")]
        urgent = [n for n in unread if n.get("priority") == "urgent"]
        high = [n for n in unread if n.get("priority") == "high"]
        return {
            "total": len(self._notifications),
            "unread": len(unread),
            "urgent": len(urgent),
            "high_priority": len(high),
            "latest": unread[:5] if unread else [],
        }


# ── Convenience: send notifications from anywhere ──

def notify(customer_id: str, type: str, title: str, message: str = "",
           data: dict = None, priority: str = "normal") -> dict:
    """Quick notify from any module."""
    engine = NotificationEngine(customer_id)
    return engine.add(type=type, title=title, message=message, data=data, priority=priority)


def notify_approval_needed(customer_id: str, action: str, approval_id: str):
    return notify(
        customer_id, "approval_needed", f"Action pending approval: {action[:100]}",
        message="An AI agent wants to execute an external action. Please approve or reject.",
        data={"approval_id": approval_id},
        priority="high",
    )


def notify_meeting_completed(customer_id: str, meeting_type: str, decision: str, meeting_id: str):
    return notify(
        customer_id, "meeting_completed", f"Meeting completed: {meeting_type}",
        message=f"Decision: {decision}",
        data={"meeting_id": meeting_id},
        priority="normal",
    )


def notify_cycle_summary(customer_id: str, cycle: int, narrative: str):
    return notify(
        customer_id, "cycle_summary", f"Cycle #{cycle} completed",
        message=narrative[:300],
        data={"cycle": cycle},
        priority="low",
    )


def notify_system_alert(customer_id: str, alert: str, severity: str = "warning"):
    return notify(
        customer_id, "system_alert", alert[:200],
        priority="urgent" if severity == "critical" else "high",
    )
