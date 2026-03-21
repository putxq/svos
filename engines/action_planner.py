"""
SVOS Action Planner — Translates decisions into structured action plans.

Replaces keyword-based execution with AI-planned actions.
Decision → Action Plan → Execution (with approval checks).

Each action has: tool, params, priority, requires_approval.
"""

import json
import logging
from typing import Any

logger = logging.getLogger("svos.action_planner")

# Tools that SVOS can execute
AVAILABLE_TOOLS = {
    "content": {
        "description": "Generate content (blog, social, article)",
        "safe": True,  # no external side effects
    },
    "market_scan": {
        "description": "Scan market for opportunities",
        "safe": True,
    },
    "landing_page": {
        "description": "Generate a landing page",
        "safe": True,
    },
    "email": {
        "description": "Send an email",
        "safe": False,  # external side effect
    },
    "whatsapp": {
        "description": "Send WhatsApp message",
        "safe": False,
    },
    "social_post": {
        "description": "Post to social media",
        "safe": False,
    },
    "crm_outreach": {
        "description": "Generate and queue outreach for CRM leads",
        "safe": False,
    },
    "report": {
        "description": "Generate internal report",
        "safe": True,
    },
    "analysis": {
        "description": "Run business analysis",
        "safe": True,
    },
}


async def generate_action_plan(
    decision_text: str,
    company_state: dict = None,
    blueprint: dict = None,
    llm_provider=None,
) -> list[dict]:
    """
    AI generates a structured action plan from a decision.
    Falls back to rule-based planning if AI is unavailable.
    """
    if llm_provider:
        try:
            return await _ai_plan(decision_text, company_state, blueprint, llm_provider)
        except Exception as e:
            logger.warning(f"AI action planning failed, using rule-based: {e}")

    return _rule_based_plan(decision_text, company_state, blueprint)


async def _ai_plan(
    decision_text: str,
    company_state: dict,
    blueprint: dict,
    llm_provider,
) -> list[dict]:
    """AI-generated action plan."""
    tools_desc = "\n".join(f"- {k}: {v['description']}" for k, v in AVAILABLE_TOOLS.items())

    # Build context
    context_parts = [f"Decision: {decision_text}"]
    if company_state:
        identity = company_state.get("identity", {})
        if identity.get("company_name"):
            context_parts.append(f"Company: {identity['company_name']} ({identity.get('industry', '')})")
        priorities = company_state.get("current_status", {}).get("top_priorities", [])
        if priorities:
            context_parts.append(f"Priorities: {', '.join(priorities)}")
    if blueprint:
        content_strategy = blueprint.get("content_strategy", {})
        if content_strategy.get("platforms"):
            context_parts.append(f"Preferred platforms: {', '.join(content_strategy['platforms'])}")

    system = (
        "You are an execution planner for a digital company. "
        "Given a strategic decision, create 2-4 concrete actions to execute it.\n\n"
        f"Available tools:\n{tools_desc}\n\n"
        "Return ONLY a JSON array of actions. Each action must have:\n"
        "- tool: one of the available tools above\n"
        "- description: what this action does (1 sentence)\n"
        "- params: dict of parameters for the tool\n"
        "- priority: 1 (highest) to 4 (lowest)\n\n"
        "Be specific. Use company context for params (real names, real topics).\n"
        "Return JSON array only, no other text."
    )

    user = "\n".join(context_parts)

    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "description": {"type": "string"},
                "params": {"type": "object"},
                "priority": {"type": "integer"},
            },
            "required": ["tool", "description", "priority"],
        },
    }

    raw = await llm_provider.complete_structured(system, user, schema)

    # Handle both list and dict responses
    if isinstance(raw, list):
        actions = raw
    elif isinstance(raw, dict) and raw.get("_parse_error"):
        return _rule_based_plan(decision_text, company_state, blueprint)
    elif isinstance(raw, dict):
        # Might be wrapped
        actions = raw.get("actions", [raw])
    else:
        return _rule_based_plan(decision_text, company_state, blueprint)

    # Validate and enrich
    result = []
    for a in actions[:4]:
        if not isinstance(a, dict):
            continue
        tool = a.get("tool", "")
        if tool not in AVAILABLE_TOOLS:
            continue
        result.append({
            "tool": tool,
            "description": a.get("description", "")[:200],
            "params": a.get("params", {}),
            "priority": min(max(a.get("priority", 2), 1), 4),
            "requires_approval": not AVAILABLE_TOOLS[tool]["safe"],
        })

    return result if result else _rule_based_plan(decision_text, company_state, blueprint)


def _rule_based_plan(
    decision_text: str,
    company_state: dict = None,
    blueprint: dict = None,
) -> list[dict]:
    """Fallback: rule-based action planning when AI is unavailable."""
    actions = []
    text = decision_text.lower()

    # Get company context
    company_name = "SVOS Company"
    industry = "general"
    platforms = ["linkedin", "twitter"]
    if company_state:
        identity = company_state.get("identity", {})
        company_name = identity.get("company_name", company_name)
        industry = identity.get("industry", industry)
    if blueprint:
        cs = blueprint.get("content_strategy", {})
        platforms = cs.get("platforms", platforms)[:2]

    # Content-related decisions
    if any(kw in text for kw in ["content", "marketing", "blog", "social", "محتوى", "تسويق", "thought", "awareness"]):
        actions.append({
            "tool": "content",
            "description": f"Generate content for {company_name} on {', '.join(platforms)}",
            "params": {
                "topic": f"{industry} trends and insights",
                "business": company_name,
                "platforms": platforms,
                "tone": "professional",
                "language": "ar",
            },
            "priority": 1,
            "requires_approval": False,
        })

    # Market/opportunity decisions
    if any(kw in text for kw in ["market", "opportunity", "scan", "research", "سوق", "فرص", "تحليل"]):
        actions.append({
            "tool": "market_scan",
            "description": f"Deep market scan for {industry} opportunities",
            "params": {"query": f"{industry} market trends Saudi Arabia 2026"},
            "priority": 1,
            "requires_approval": False,
        })

    # Landing page decisions
    if any(kw in text for kw in ["landing", "page", "website", "صفحة", "موقع", "launch"]):
        actions.append({
            "tool": "landing_page",
            "description": f"Generate landing page for {company_name}",
            "params": {
                "company_name": company_name,
                "headline": f"Welcome to {company_name}",
                "subheadline": f"Leading {industry} solutions",
                "benefits": ["Expert team", "Proven results", "Local focus"],
                "cta_text": "Get Started",
            },
            "priority": 2,
            "requires_approval": False,
        })

    # Outreach decisions
    if any(kw in text for kw in ["outreach", "email", "lead", "customer", "عملاء", "تواصل"]):
        actions.append({
            "tool": "crm_outreach",
            "description": "Generate outreach for qualified leads",
            "params": {"type": "email", "segment": "qualified"},
            "priority": 2,
            "requires_approval": True,
        })

    # Always add a report
    actions.append({
        "tool": "report",
        "description": "Generate daily execution report",
        "params": {},
        "priority": 4,
        "requires_approval": False,
    })

    return actions
