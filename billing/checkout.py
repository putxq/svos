"""
Payment provider abstraction: Stripe (international) + Moyasar (Saudi).
"""

import logging
import os
import time

logger = logging.getLogger("svos.billing.checkout")


class StripeProvider:
    """Stripe payment provider for international customers."""

    def __init__(self):
        self.secret_key = os.getenv("STRIPE_SECRET_KEY", "")
        self.publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
        self.configured = bool(self.secret_key)

        if self.configured:
            import stripe

            stripe.api_key = self.secret_key
            logger.info("StripeProvider initialized")
        else:
            logger.warning("StripeProvider: No secret key - dry-run mode")

    def create_checkout_session(self, plan_id: str, customer_email: str, success_url: str, cancel_url: str) -> dict:
        from billing.plans import get_plan

        plan = get_plan(plan_id)

        if not self.configured:
            session_id = f"dry_run_{plan_id}_{int(time.time())}"
            return {
                "status": "dry-run",
                "session_id": session_id,
                "checkout_url": f"{success_url}?session_id={session_id}",
                "plan": plan_id,
                "amount_usd": plan["price_usd"],
                "message": "Set STRIPE_SECRET_KEY to enable real payments",
            }

        try:
            import stripe

            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                mode="subscription",
                customer_email=customer_email,
                line_items=[
                    {
                        "price": plan.get("stripe_price_id") or self._create_price(plan),
                        "quantity": 1,
                    }
                ],
                success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=cancel_url,
                metadata={"plan_id": plan_id, "svos": "true"},
            )
            return {
                "status": "created",
                "session_id": session.id,
                "checkout_url": session.url,
                "plan": plan_id,
            }
        except Exception as e:
            logger.error(f"Stripe checkout failed: {e}")
            return {"status": "error", "error": str(e)}

    def _create_price(self, plan: dict) -> str:
        import stripe

        product = stripe.Product.create(name=f"SVOS {plan['name']}")
        price = stripe.Price.create(
            product=product.id,
            unit_amount=plan["price_usd"] * 100,
            currency="usd",
            recurring={"interval": "month"},
        )
        return price.id

    def verify_webhook(self, payload: bytes, sig_header: str) -> dict:
        if not self.configured or not self.webhook_secret:
            return {"verified": False, "reason": "not configured"}
        try:
            import stripe

            event = stripe.Webhook.construct_event(payload, sig_header, self.webhook_secret)
            return {"verified": True, "event": event}
        except Exception as e:
            return {"verified": False, "reason": str(e)}


class MoyasarProvider:
    """Moyasar payment provider for Saudi customers (SAR)."""

    def __init__(self):
        self.api_key = os.getenv("MOYASAR_API_KEY", "")
        self.publishable_key = os.getenv("MOYASAR_PUBLISHABLE_KEY", "")
        self.configured = bool(self.api_key)

        if self.configured:
            logger.info("MoyasarProvider initialized")
        else:
            logger.warning("MoyasarProvider: No API key - dry-run mode")

    def create_payment(self, plan_id: str, customer_email: str, callback_url: str) -> dict:
        from billing.plans import get_plan

        plan = get_plan(plan_id)

        if not self.configured:
            payment_id = f"moy_dry_{plan_id}_{int(time.time())}"
            return {
                "status": "dry-run",
                "payment_id": payment_id,
                "plan": plan_id,
                "amount_sar": plan["price_sar"],
                "message": "Set MOYASAR_API_KEY to enable real payments",
            }

        try:
            import requests

            resp = requests.post(
                "https://api.moyasar.com/v1/payments",
                auth=(self.api_key, ""),
                json={
                    "amount": plan["moyasar_amount"],
                    "currency": "SAR",
                    "description": f"SVOS {plan['name']} Subscription",
                    "callback_url": callback_url,
                    "source": {"type": "creditcard"},
                    "metadata": {"plan_id": plan_id, "email": customer_email},
                },
            )
            data = resp.json()
            return {
                "status": "created",
                "payment_id": data.get("id"),
                "payment_url": data.get("source", {}).get("transaction_url"),
                "plan": plan_id,
            }
        except Exception as e:
            logger.error(f"Moyasar payment failed: {e}")
            return {"status": "error", "error": str(e)}


def get_provider(region: str = "international"):
    if region in ("sa", "saudi", "sar", "local"):
        return MoyasarProvider()
    return StripeProvider()
