"""
Subscription management: provisioning, metering, and enforcement.
"""

import json
import logging
import time
from pathlib import Path

from billing.plans import get_limits, get_plan

logger = logging.getLogger("svos.billing.subscriptions")

SUBS_DIR = Path("workspace/subscriptions")
SUBS_DIR.mkdir(parents=True, exist_ok=True)


class SubscriptionManager:
    """Manages customer subscriptions, usage metering, and limit enforcement."""

    def __init__(self):
        self._cache = {}
        self._load_all()

    def _load_all(self):
        for f in SUBS_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text("utf-8"))
                self._cache[data["customer_id"]] = data
            except Exception as e:
                logger.warning(f"Failed to load subscription {f}: {e}")

    def _save(self, sub: dict):
        path = SUBS_DIR / f"{sub['customer_id']}.json"
        path.write_text(json.dumps(sub, indent=2, ensure_ascii=False), encoding="utf-8")
        self._cache[sub["customer_id"]] = sub

    def provision(self, customer_id: str, plan_id: str, email: str, payment_ref: str = "") -> dict:
        plan = get_plan(plan_id)
        now = time.time()

        sub = {
            "customer_id": customer_id,
            "email": email,
            "plan_id": plan_id,
            "plan_name": plan["name"],
            "status": "active",
            "payment_ref": payment_ref,
            "provisioned_at": now,
            "expires_at": now + (30 * 86400),
            "limits": get_limits(plan_id),
            "usage_today": {
                "cycles": 0,
                "api_calls": 0,
                "tools_used": 0,
                "date": time.strftime("%Y-%m-%d"),
            },
            "total_usage": {
                "cycles": 0,
                "api_calls": 0,
                "tools_used": 0,
            },
        }

        self._save(sub)
        logger.info(f"Provisioned {customer_id} on plan '{plan_id}'")
        return {"status": "provisioned", "subscription": sub}

    def get_subscription(self, customer_id: str) -> dict:
        sub = self._cache.get(customer_id)
        if not sub:
            return {"status": "not_found", "customer_id": customer_id}

        if sub.get("usage_today", {}).get("date") != time.strftime("%Y-%m-%d"):
            sub["usage_today"] = {
                "cycles": 0,
                "api_calls": 0,
                "tools_used": 0,
                "date": time.strftime("%Y-%m-%d"),
            }
            self._save(sub)

        expired = time.time() > sub.get("expires_at", 0)
        sub["is_expired"] = expired
        if expired:
            sub["status"] = "expired"

        return {"status": "found", "subscription": sub}

    def check_limit(self, customer_id: str, resource: str) -> dict:
        result = self.get_subscription(customer_id)
        if result["status"] != "found":
            return {"allowed": False, "reason": "no_subscription"}

        sub = result["subscription"]
        if sub["status"] != "active":
            return {"allowed": False, "reason": f"subscription_{sub['status']}"}

        limits = sub.get("limits", {})
        usage = sub.get("usage_today", {})

        if resource == "cycle":
            allowed = usage.get("cycles", 0) < limits.get("cycles_per_day", 0)
            return {
                "allowed": allowed,
                "current": usage.get("cycles", 0),
                "limit": limits.get("cycles_per_day", 0),
                "resource": resource,
                "reason": "" if allowed else "daily_cycle_limit_reached",
            }
        elif resource == "api_call":
            allowed = usage.get("api_calls", 0) < limits.get("api_calls_per_day", 0)
            return {
                "allowed": allowed,
                "current": usage.get("api_calls", 0),
                "limit": limits.get("api_calls_per_day", 0),
                "resource": resource,
                "reason": "" if allowed else "daily_api_limit_reached",
            }
        elif resource.startswith("tool:"):
            tool_name = resource.split(":", 1)[1]
            enabled = limits.get("tools_enabled", [])
            allowed = tool_name in enabled or "all" in enabled
            return {
                "allowed": allowed,
                "tool": tool_name,
                "enabled_tools": enabled,
                "reason": "" if allowed else f"tool_{tool_name}_not_in_plan",
            }

        return {"allowed": True, "resource": resource}

    def record_usage(self, customer_id: str, resource: str, amount: int = 1) -> dict:
        result = self.get_subscription(customer_id)
        if result["status"] != "found":
            return {"recorded": False, "reason": "no_subscription"}

        sub = result["subscription"]

        if resource == "cycle":
            sub["usage_today"]["cycles"] = sub["usage_today"].get("cycles", 0) + amount
            sub["total_usage"]["cycles"] = sub["total_usage"].get("cycles", 0) + amount
        elif resource == "api_call":
            sub["usage_today"]["api_calls"] = sub["usage_today"].get("api_calls", 0) + amount
            sub["total_usage"]["api_calls"] = sub["total_usage"].get("api_calls", 0) + amount
        elif resource == "tool":
            sub["usage_today"]["tools_used"] = sub["usage_today"].get("tools_used", 0) + amount
            sub["total_usage"]["tools_used"] = sub["total_usage"].get("tools_used", 0) + amount

        self._save(sub)
        return {"recorded": True, "usage_today": sub["usage_today"]}

    def cancel(self, customer_id: str) -> dict:
        result = self.get_subscription(customer_id)
        if result["status"] != "found":
            return {"cancelled": False, "reason": "not_found"}

        sub = result["subscription"]
        sub["status"] = "cancelled"
        sub["cancelled_at"] = time.time()
        self._save(sub)
        return {"cancelled": True, "customer_id": customer_id}

    def list_all(self) -> list:
        return list(self._cache.values())


_manager = None


def get_subscription_manager() -> SubscriptionManager:
    global _manager
    if _manager is None:
        _manager = SubscriptionManager()
    return _manager
