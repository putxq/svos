"""
SVOS Reaction Hooks — Event-Triggered Automations.

Not a workflow engine. Just smart if-statements that fire after key events.
Each hook reads the Blueprint to know what's active, then reacts.

Usage:
    from engines.reaction_hooks import trigger_hook
    await trigger_hook("lead_added", {"lead_id": "...", "customer_id": "..."})
"""

import logging
from typing import Any

logger = logging.getLogger("svos.hooks")


async def trigger_hook(event: str, data: dict) -> dict:
    """Trigger a reaction hook. Returns what happened."""
    handler = HOOKS.get(event)
    if not handler:
        return {"event": event, "handled": False, "reason": "no_hook_registered"}

    try:
        result = await handler(data)
        logger.info(f"Hook '{event}' fired: {result.get('actions', [])}")
        return {"event": event, "handled": True, "result": result}
    except Exception as e:
        logger.warning(f"Hook '{event}' failed: {e}")
        return {"event": event, "handled": False, "error": str(e)}


def _is_workflow_active(customer_id: str, workflow_name: str) -> bool:
    """Check if a workflow is active in the customer's Blueprint."""
    try:
        from engines.blueprint_engine import load_blueprint
        bp = load_blueprint(customer_id)
        if not bp:
            return False
        workflows = bp.get("workflows", {})
        wf = workflows.get(workflow_name, {})
        return isinstance(wf, dict) and wf.get("active", False)
    except Exception:
        return False


# =====================================================================
# HOOK: lead_added — New lead enters CRM
# =====================================================================
async def _hook_lead_added(data: dict) -> dict:
    """When a new lead is added to CRM, auto-score and optionally outreach."""
    customer_id = data.get("customer_id", "")
    lead_id = data.get("lead_id", "")
    actions = []

    if not customer_id or not lead_id:
        return {"actions": [], "reason": "missing customer_id or lead_id"}

    # Auto-score if lead_nurturing workflow is active
    if _is_workflow_active(customer_id, "lead_nurturing"):
        try:
            from engines.crm_engine import CRMEngine
            from core.tenant import get_tenant_crm_dir

            crm = CRMEngine(data_dir=str(get_tenant_crm_dir(customer_id)))
            score_result = await crm.score_lead(lead_id)
            actions.append({"action": "auto_scored", "result": str(score_result)[:200]})

            # If qualified, queue outreach for approval
            score = score_result.get("score", 0) if isinstance(score_result, dict) else 0
            if score and score > 70:
                try:
                    from engines.company_state import get_company_state
                    state = get_company_state(customer_id)
                    state.add_pending_approval(
                        action=f"Send outreach email to lead {lead_id} (score: {score})",
                        tool="email",
                        params={"lead_id": lead_id, "type": "outreach"},
                    )
                    actions.append({"action": "outreach_queued_for_approval", "score": score})
                except Exception as e:
                    actions.append({"action": "outreach_queue_failed", "error": str(e)})
        except Exception as e:
            actions.append({"action": "auto_score_failed", "error": str(e)})

    # Update KPI
    try:
        from engines.company_state import get_company_state
        state = get_company_state(customer_id)
        state.increment_kpi("leads_total")
        actions.append({"action": "kpi_updated", "kpi": "leads_total"})
    except Exception:
        pass

    return {"actions": actions}


# =====================================================================
# HOOK: cycle_completed — After each autonomous cycle
# =====================================================================
async def _hook_cycle_completed(data: dict) -> dict:
    """After cycle completes, update KPIs and check weekly review."""
    customer_id = data.get("customer_id", "")
    cycle = data.get("cycle", 0)
    actions_count = data.get("actions_taken", 0)
    actions = []

    if not customer_id:
        return {"actions": [], "reason": "no customer_id"}

    # Check if weekly review is due (Sunday)
    from datetime import datetime
    today = datetime.utcnow()
    if today.weekday() == 6:  # Sunday
        if _is_workflow_active(customer_id, "monthly_review") or \
           _is_workflow_active(customer_id, "weekly_content"):
            actions.append({
                "action": "weekly_review_due",
                "note": "System should run weekly review in next cycle",
            })

    # Check if monthly review is due (1st of month)
    if today.day == 1:
        if _is_workflow_active(customer_id, "monthly_review"):
            actions.append({
                "action": "monthly_review_due",
                "note": "System should run strategic review",
            })

    return {"actions": actions}


# =====================================================================
# HOOK: content_produced — After content generation
# =====================================================================
async def _hook_content_produced(data: dict) -> dict:
    """Track content production in KPIs."""
    customer_id = data.get("customer_id", "")
    actions = []

    if customer_id:
        try:
            from engines.company_state import get_company_state
            state = get_company_state(customer_id)
            count = data.get("count", 1)
            state.increment_kpi("content_produced", count)
            actions.append({"action": "kpi_updated", "kpi": "content_produced", "added": count})
        except Exception:
            pass

    return {"actions": actions}


# =====================================================================
# HOOK: inbound_received — Message received via inbox
# =====================================================================
async def _hook_inbound_received(data: dict) -> dict:
    """Classify and route an inbound message."""
    customer_id = data.get("customer_id", "")
    msg_type = data.get("type", "unknown")
    body = data.get("body", "")
    from_addr = data.get("from", "")
    actions = []

    if not customer_id or not body:
        return {"actions": [], "reason": "missing data"}

    # Simple classification (AI-enhanced later)
    classification = _classify_inbound(body, msg_type)
    actions.append({"action": "classified", "classification": classification})

    # Route based on classification
    if classification == "new_lead":
        try:
            from engines.crm_engine import CRMEngine
            from core.tenant import get_tenant_crm_dir

            crm = CRMEngine(data_dir=str(get_tenant_crm_dir(customer_id)))
            lead = crm.add_lead(
                name=from_addr.split("@")[0] if "@" in from_addr else from_addr,
                email=from_addr if "@" in from_addr else "",
                source=f"inbound_{msg_type}",
                notes=body[:200],
            )
            actions.append({"action": "lead_created", "lead_id": lead.get("lead_id", "")})

            # Trigger lead_added hook
            await trigger_hook("lead_added", {
                "customer_id": customer_id,
                "lead_id": lead.get("lead_id", ""),
            })
        except Exception as e:
            actions.append({"action": "lead_creation_failed", "error": str(e)})

    elif classification == "support_request":
        # Queue for human review
        try:
            from engines.company_state import get_company_state
            state = get_company_state(customer_id)
            state.add_pending_approval(
                action=f"Support request from {from_addr}: {body[:100]}",
                tool="email",
                params={"type": "support_reply", "from": from_addr, "body": body[:500]},
            )
            actions.append({"action": "queued_for_support_review"})
        except Exception as e:
            actions.append({"action": "support_queue_failed", "error": str(e)})

    elif classification == "reply_to_outreach":
        actions.append({"action": "flagged_as_outreach_reply", "from": from_addr})

    return {"actions": actions}


def _classify_inbound(body: str, msg_type: str) -> str:
    """Simple rule-based classification. AI-enhanced in future."""
    text = body.lower()

    # Support signals
    if any(kw in text for kw in ["help", "problem", "issue", "مشكلة", "مساعدة", "support", "complaint"]):
        return "support_request"

    # Reply signals
    if any(kw in text for kw in ["thank", "interested", "yes", "شكر", "مهتم", "نعم", "أبغى"]):
        return "reply_to_outreach"

    # Default: treat as new lead
    return "new_lead"


# =====================================================================
# HOOK REGISTRY
# =====================================================================
HOOKS = {
    "lead_added": _hook_lead_added,
    "cycle_completed": _hook_cycle_completed,
    "content_produced": _hook_content_produced,
    "inbound_received": _hook_inbound_received,
}
