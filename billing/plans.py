"""
SVOS Subscription Plans and Limits.
"""

PLANS = {
    "starter": {
        "id": "starter",
        "name": "Starter",
        "name_ar": "المبتدئ",
        "price_usd": 299,
        "price_sar": 1122,
        "billing_cycle": "monthly",
        "stripe_price_id": "",
        "moyasar_amount": 112200,
        "limits": {
            "agents": 3,
            "cycles_per_day": 2,
            "tools_enabled": ["email", "landing_page"],
            "companies": 1,
            "storage_mb": 500,
            "api_calls_per_day": 100,
        },
        "features": [
            "3 AI Agents (CEO, CMO, CTO)",
            "2 autonomous cycles/day",
            "Email + Landing Page tools",
            "Basic dashboard",
        ],
    },
    "professional": {
        "id": "professional",
        "name": "Professional",
        "name_ar": "الاحترافي",
        "price_usd": 799,
        "price_sar": 2996,
        "billing_cycle": "monthly",
        "stripe_price_id": "",
        "moyasar_amount": 299600,
        "limits": {
            "agents": 7,
            "cycles_per_day": 6,
            "tools_enabled": ["email", "landing_page", "whatsapp", "social_post"],
            "companies": 3,
            "storage_mb": 2000,
            "api_calls_per_day": 500,
        },
        "features": [
            "7 AI Agents (Full C-Suite)",
            "6 autonomous cycles/day",
            "All execution tools",
            "Advanced dashboard + analytics",
            "WhatsApp + Social Media",
        ],
    },
    "enterprise": {
        "id": "enterprise",
        "name": "Enterprise",
        "name_ar": "المؤسسي",
        "price_usd": 1999,
        "price_sar": 7496,
        "billing_cycle": "monthly",
        "stripe_price_id": "",
        "moyasar_amount": 749600,
        "limits": {
            "agents": 9,
            "cycles_per_day": 24,
            "tools_enabled": ["email", "landing_page", "whatsapp", "social_post", "custom"],
            "companies": 10,
            "storage_mb": 10000,
            "api_calls_per_day": 2000,
        },
        "features": [
            "9 AI Agents + Custom Agents",
            "24/7 autonomous operation",
            "All tools + custom integrations",
            "Full dashboard + API access",
            "Priority support",
            "Self-building capabilities",
        ],
    },
    "custom": {
        "id": "custom",
        "name": "Custom",
        "name_ar": "مخصص",
        "price_usd": 0,
        "price_sar": 0,
        "billing_cycle": "custom",
        "stripe_price_id": "",
        "moyasar_amount": 0,
        "limits": {
            "agents": 99,
            "cycles_per_day": 999,
            "tools_enabled": ["all"],
            "companies": 999,
            "storage_mb": 99999,
            "api_calls_per_day": 99999,
        },
        "features": ["Everything in Enterprise", "Custom agent development", "Dedicated infrastructure", "SLA guarantee"],
    },
}


def get_plan(plan_id: str) -> dict:
    return PLANS.get(plan_id, PLANS["starter"])


def get_limits(plan_id: str) -> dict:
    return get_plan(plan_id).get("limits", {})


def list_plans() -> list:
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "name_ar": p["name_ar"],
            "price_usd": p["price_usd"],
            "price_sar": p["price_sar"],
            "features": p["features"],
        }
        for p in PLANS.values()
        if p["id"] != "custom"
    ]
