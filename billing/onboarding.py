"""
SVOS Onboarding — single flow to activate a new customer.
register → provision subscription → issue API key → init workspace → init company DNA → done.
"""

import logging
import time
from typing import Any

from billing.auth import issue_api_key
from billing.subscriptions import get_subscription_manager
from core.tenant import init_tenant_workspace

logger = logging.getLogger("svos.onboarding")


def onboard_customer(
    customer_id: str,
    email: str,
    plan_id: str = "starter",
    company_name: str = "",
    company_description: str = "",
    mission: str = "",
    vision: str = "",
    values: list[str] | None = None,
    industry: str = "general",
    country: str = "Saudi Arabia",
    risk_appetite: str = "moderate",
    payment_ref: str = "",
    llm_provider: str = "",
    llm_api_key: str = "",
    llm_model: str = "",
    ollama_base_url: str = "http://localhost:11434",
) -> dict:
    """
    Complete onboarding in one call.
    Returns everything the customer needs to start using SVOS.
    """
    errors: list[str] = []

    # ── Step 1: Provision subscription ──
    mgr = get_subscription_manager()
    sub_result = mgr.provision(
        customer_id=customer_id,
        plan_id=plan_id,
        email=email,
        payment_ref=payment_ref,
    )
    logger.info(f"[onboard] Subscription provisioned: {customer_id} on {plan_id}")

    # ── Step 2: Issue API key ──
    key_result = issue_api_key(customer_id=customer_id, label="onboarding_key")
    api_key = key_result.get("api_key", "")
    logger.info(f"[onboard] API key issued for {customer_id}")

    # ── Step 3: Init tenant workspace ──
    workspace = init_tenant_workspace(customer_id)
    logger.info(f"[onboard] Workspace created: {workspace['workspace']}")

    # ── Step 4: Save LLM config (BYOK) ──
    llm_result = {}
    if llm_provider:
        try:
            from core.tenant_llm_config import save_llm_config
            llm_result = save_llm_config(
                customer_id=customer_id,
                provider=llm_provider,
                api_key=llm_api_key,
                model=llm_model,
                ollama_base_url=ollama_base_url,
            )
            if llm_result.get("success"):
                logger.info(f"[onboard] LLM config saved: {llm_provider} for {customer_id}")
            else:
                errors.append(f"LLM config: {llm_result.get('error', 'unknown')}")
        except Exception as e:
            errors.append(f"LLM config failed: {str(e)}")
            logger.warning(f"[onboard] LLM config error: {e}")

    # ── Step 5: Init Company DNA ──
    dna_result = {}
    try:
        from engines.company_dna import CompanyDNA
        from core.tenant import get_tenant_dna_dir

        dna_dir = get_tenant_dna_dir(customer_id)
        dna = CompanyDNA(company_id=customer_id, data_dir=str(dna_dir))
        dna_result = dna.initialize(
            name=company_name or f"Company-{customer_id[:8]}",
            mission=mission or f"Build a successful {industry} business",
            vision=vision or "Become a market leader",
            values=values or ["quality", "innovation", "trust"],
            personality={
                "tone": "professional",
                "risk_appetite": risk_appetite,
                "decision_speed": "balanced",
                "innovation_level": "high",
            },
        )
        logger.info(f"[onboard] Company DNA initialized for {customer_id}")
    except Exception as e:
        errors.append(f"DNA init failed: {str(e)}")
        logger.warning(f"[onboard] DNA init error: {e}")

    # ── Step 6: Build onboarding summary ──
    plan_details = sub_result.get("subscription", {})

    return {
        "success": True,
        "customer_id": customer_id,
        "email": email,
        "plan": {
            "id": plan_id,
            "name": plan_details.get("plan_name", plan_id),
            "limits": plan_details.get("limits", {}),
        },
        "api_key": api_key,
        "llm": llm_result if llm_result else {"status": "not_configured", "message": "Add your LLM key later in settings"},
        "workspace": workspace,
        "company_dna": dna_result if dna_result else {"status": "skipped"},
        "company_name": company_name,
        "dashboard_url": f"/dashboard?key={api_key}",
        "next_steps": [
            "Save your API key securely — it won't be shown again",
            "Open the dashboard to configure your AI company",
            "Chat with your CEO agent to set strategic direction",
            "Run your first autonomous cycle from the scheduler panel",
        ] if llm_provider else [
            "Save your API key securely — it won't be shown again",
            "Add your LLM API key (Claude, GPT, Gemini, or Ollama)",
            "Open the dashboard to configure your AI company",
            "Chat with your CEO agent to set strategic direction",
        ],
        "errors": errors,
        "onboarded_at": time.time(),
    }


def get_onboarding_status(customer_id: str) -> dict:
    """Check what's been set up for a customer."""
    from billing.subscriptions import get_subscription_manager
    from core.tenant import get_tenant_dir
    from core.tenant_llm_config import get_llm_status
    from pathlib import Path

    mgr = get_subscription_manager()
    sub = mgr.get_subscription(customer_id)
    has_subscription = sub.get("status") == "found"

    tenant_dir = get_tenant_dir(customer_id)
    has_workspace = tenant_dir.exists() and (tenant_dir / "crm").exists()

    dna_file = tenant_dir / "dna" / f"{customer_id}_dna.json"
    has_dna = dna_file.exists()

    llm_status = get_llm_status(customer_id)
    has_llm = llm_status.get("configured", False)

    return {
        "customer_id": customer_id,
        "subscription": has_subscription,
        "workspace": has_workspace,
        "company_dna": has_dna,
        "llm_configured": has_llm,
        "llm_details": llm_status,
        "fully_onboarded": all([has_subscription, has_workspace, has_dna, has_llm]),
    }
