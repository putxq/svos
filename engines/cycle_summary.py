"""
SVOS Cycle Summary Generator — Dual Layer Output.

Layer 1: Operational Log (no AI needed, pure data aggregation)
Layer 2: Executive Narrative (AI-generated, CEO-level summary)

The operational log always works even if LLM is down.
The executive narrative adds human-readable insight on top.
"""

import json
import logging
from datetime import datetime

logger = logging.getLogger("svos.cycle_summary")


def generate_operational_summary(cycle_result: dict, company_state: dict = None) -> dict:
    """
    Layer 1: Pure data aggregation. No AI. Always works.
    Counts phases, actions, errors from the cycle result.
    """
    phases = cycle_result.get("phases", {})

    phases_done = sum(1 for p in phases.values() if p.get("status") == "done")
    phases_error = sum(1 for p in phases.values() if p.get("status") == "error")
    phases_total = len(phases)

    # Count actions from execution phase
    execution = phases.get("execution", {})
    actions_taken = execution.get("total_actions", len(execution.get("actions_taken", [])))
    actions_detail = execution.get("actions_taken", [])
    actions_succeeded = sum(1 for a in actions_detail if a.get("status") == "done")
    actions_failed = sum(1 for a in actions_detail if a.get("status") == "error")

    # Extract key info from each phase
    briefing_summary = phases.get("briefing", {}).get("summary", "")[:200]
    market_summary = phases.get("market_scan", {}).get("opportunities", "")[:200]
    decision_summary = phases.get("decision", {}).get("decision", "")[:200]

    duration = cycle_result.get("duration_seconds", 0)

    return {
        "cycle": cycle_result.get("cycle", 0),
        "timestamp": datetime.utcnow().isoformat(),
        "duration_seconds": round(duration, 1),
        "phases": {
            "total": phases_total,
            "completed": phases_done,
            "errors": phases_error,
        },
        "actions": {
            "total": actions_taken,
            "succeeded": actions_succeeded,
            "failed": actions_failed,
            "detail": [
                {"action": a.get("action", ""), "status": a.get("status", "")}
                for a in actions_detail
            ],
        },
        "highlights": {
            "briefing": briefing_summary,
            "market": market_summary,
            "decision": decision_summary,
        },
        "health": "healthy" if phases_error == 0 else ("degraded" if phases_error < phases_total else "critical"),
    }


async def generate_executive_narrative(
    operational_summary: dict,
    company_state: dict = None,
    llm_provider=None,
) -> str:
    """
    Layer 2: AI-generated executive narrative.
    CEO-level summary in natural language.
    Falls back to a formatted string if LLM fails.
    """
    # Build context for the AI
    cycle = operational_summary.get("cycle", "?")
    phases = operational_summary.get("phases", {})
    actions = operational_summary.get("actions", {})
    highlights = operational_summary.get("highlights", {})
    health = operational_summary.get("health", "unknown")
    duration = operational_summary.get("duration_seconds", 0)

    # Company context if available
    company_context = ""
    if company_state:
        identity = company_state.get("identity", {})
        if identity.get("company_name"):
            company_context = f"Company: {identity['company_name']} ({identity.get('industry', '')}). "
        priorities = company_state.get("current_status", {}).get("top_priorities", [])
        if priorities:
            company_context += f"Current priorities: {', '.join(priorities[:3])}. "

    data_block = (
        f"Cycle #{cycle} completed in {duration:.0f}s. "
        f"Phases: {phases.get('completed', 0)}/{phases.get('total', 0)} succeeded. "
        f"Actions: {actions.get('succeeded', 0)} succeeded, {actions.get('failed', 0)} failed. "
        f"System health: {health}. "
        f"Briefing: {highlights.get('briefing', 'N/A')[:150]}. "
        f"Market: {highlights.get('market', 'N/A')[:150]}. "
        f"Decision: {highlights.get('decision', 'N/A')[:150]}."
    )

    if llm_provider is None:
        try:
            from core.llm_provider import LLMProvider
            llm_provider = LLMProvider()
        except Exception as e:
            logger.warning(f"Cannot create LLM for narrative: {e}")
            return _fallback_narrative(operational_summary)

    system = (
        "You are the CEO of a digital company. Write a brief executive summary of today's cycle. "
        "Be concise (3-5 sentences max), strategic, and actionable. "
        "Mention what was accomplished, what needs attention, and recommended next focus. "
        "Reply in the same language as the company context (Arabic if Arabic, English if English)."
    )

    user = f"{company_context}\n\nToday's cycle data:\n{data_block}"

    try:
        narrative = await llm_provider.complete(
            system_prompt=system,
            user_message=user,
            temperature=0.4,
            max_tokens=300,
        )
        return narrative.strip()
    except Exception as e:
        logger.warning(f"Executive narrative generation failed: {e}")
        return _fallback_narrative(operational_summary)


def _fallback_narrative(op_summary: dict) -> str:
    """Plain text fallback when AI is unavailable."""
    cycle = op_summary.get("cycle", "?")
    phases = op_summary.get("phases", {})
    actions = op_summary.get("actions", {})
    health = op_summary.get("health", "unknown")

    return (
        f"Cycle #{cycle} completed. "
        f"{phases.get('completed', 0)}/{phases.get('total', 0)} phases succeeded. "
        f"{actions.get('total', 0)} actions executed ({actions.get('succeeded', 0)} succeeded). "
        f"System health: {health}."
    )


async def generate_full_summary(
    cycle_result: dict,
    company_state: dict = None,
    llm_provider=None,
) -> dict:
    """Generate both layers in one call."""
    operational = generate_operational_summary(cycle_result, company_state)

    narrative = await generate_executive_narrative(
        operational, company_state, llm_provider
    )

    return {
        "operational": operational,
        "narrative": narrative,
        "generated_at": datetime.utcnow().isoformat(),
    }
