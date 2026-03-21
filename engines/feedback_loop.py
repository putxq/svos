"""
SVOS Decision Feedback Loop — The Company Learns.

Runs during weekly review:
1. Finds decisions from past 7 days with no outcome yet
2. Evaluates them based on current KPIs and state
3. Records lessons learned
4. Updates Company State

This is what makes SVOS smarter over time.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger("svos.feedback")


async def run_weekly_feedback(customer_id: str, llm_provider=None) -> dict:
    """
    Run the weekly decision feedback loop.
    Reviews unresolved decisions and generates lessons.
    """
    from engines.company_state import get_company_state

    state = get_company_state(customer_id)
    decisions = state.state.get("decisions", [])

    if not decisions:
        return {"reviewed": 0, "lessons": [], "message": "No decisions to review"}

    # Find decisions from last 7 days without outcomes
    cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
    unresolved = []
    for i, d in enumerate(decisions):
        if d.get("actual_outcome") is None and d.get("taken_at", "") >= cutoff:
            unresolved.append((i, d))

    if not unresolved:
        return {"reviewed": 0, "lessons": [], "message": "No unresolved recent decisions"}

    # Get current KPIs for evaluation context
    kpis = state.state.get("kpis", {})
    recent_cycles = state.state.get("recent_cycles", [])

    lessons = []
    evaluated = 0

    if llm_provider:
        try:
            result = await _ai_evaluate_decisions(unresolved, kpis, recent_cycles, llm_provider)
            for eval_item in result:
                idx = eval_item.get("index", -1)
                if 0 <= idx < len(decisions):
                    state.evaluate_decision(
                        index=idx,
                        actual_outcome=eval_item.get("outcome", "evaluated by AI"),
                        success=eval_item.get("success", True),
                    )
                    evaluated += 1

                if eval_item.get("lesson"):
                    state.record_lesson(
                        lesson=eval_item["lesson"],
                        category=eval_item.get("category", "weekly_review"),
                    )
                    lessons.append(eval_item["lesson"])
        except Exception as e:
            logger.warning(f"AI evaluation failed, using simple evaluation: {e}")
            evaluated, lessons = _simple_evaluate(state, unresolved, kpis)
    else:
        evaluated, lessons = _simple_evaluate(state, unresolved, kpis)

    return {
        "reviewed": evaluated,
        "total_unresolved": len(unresolved),
        "lessons": lessons,
        "kpis_snapshot": kpis,
    }


async def _ai_evaluate_decisions(
    unresolved: list[tuple[int, dict]],
    kpis: dict,
    recent_cycles: list,
    llm_provider,
) -> list[dict]:
    """AI evaluates unresolved decisions."""
    decisions_text = "\n".join(
        f"[{i}] Decision: {d['decision'][:150]} | Expected: {d.get('expected_outcome', 'N/A')[:100]} | Date: {d.get('taken_at', '')[:10]}"
        for i, d in unresolved
    )

    kpis_text = ", ".join(f"{k}: {v}" for k, v in kpis.items() if v)
    cycles_text = ""
    if recent_cycles:
        cycles_text = " | ".join(
            f"Cycle {c.get('cycle', '?')}: {c.get('summary', '')[:100]}"
            for c in recent_cycles[-3:]
        )

    system = (
        "You are a business performance reviewer. "
        "Evaluate these past decisions based on current KPIs and recent activity. "
        "For each decision, determine: was it successful? what was the actual outcome? what lesson to learn?\n\n"
        "Return ONLY a JSON array. Each item:\n"
        "- index: int (the decision index)\n"
        "- success: bool\n"
        "- outcome: string (what actually happened, 1 sentence)\n"
        "- lesson: string (what to learn for future, 1 sentence)\n"
        "- category: string (strategy|execution|market|customer)\n"
    )

    user = (
        f"Decisions to evaluate:\n{decisions_text}\n\n"
        f"Current KPIs: {kpis_text}\n\n"
        f"Recent cycles: {cycles_text}\n"
    )

    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "index": {"type": "integer"},
                "success": {"type": "boolean"},
                "outcome": {"type": "string"},
                "lesson": {"type": "string"},
                "category": {"type": "string"},
            },
            "required": ["index", "success", "outcome"],
        },
    }

    raw = await llm_provider.complete_structured(system, user, schema)

    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict) and not raw.get("_parse_error"):
        return [raw]
    return []


def _simple_evaluate(state, unresolved: list, kpis: dict) -> tuple[int, list]:
    """Simple rule-based evaluation when AI is unavailable."""
    evaluated = 0
    lessons = []

    # Simple heuristic: if KPIs improved since decision, mark as success
    total_activity = sum(v for v in kpis.values() if isinstance(v, (int, float)))
    has_activity = total_activity > 0

    for idx, decision in unresolved:
        success = has_activity  # Simple: if there's any activity, consider positive
        state.evaluate_decision(
            index=idx,
            actual_outcome="Evaluated during weekly review (rule-based)",
            success=success,
        )
        evaluated += 1

    if evaluated > 0:
        lesson = (
            f"Reviewed {evaluated} decisions. "
            f"Current activity level: {'active' if has_activity else 'low'}. "
            f"Focus on increasing measurable outcomes."
        )
        state.record_lesson(lesson=lesson, category="weekly_review")
        lessons.append(lesson)

    return evaluated, lessons


async def generate_weekly_report(customer_id: str, llm_provider=None) -> dict:
    """
    Generate a weekly performance report.
    Combines: KPIs, decisions made, lessons learned, recommendations.
    """
    from engines.company_state import get_company_state

    state = get_company_state(customer_id)
    s = state.state

    kpis = s.get("kpis", {})
    decisions = s.get("decisions", [])[-7:]  # last 7
    lessons = s.get("lessons", [])[-5:]
    cycles = s.get("recent_cycles", [])[-7:]
    priorities = s.get("current_status", {}).get("top_priorities", [])

    # Stats
    total_cycles = len(cycles)
    total_decisions = len(decisions)
    successful = sum(1 for d in decisions if d.get("success") is True)
    failed = sum(1 for d in decisions if d.get("success") is False)

    report = {
        "period": "weekly",
        "generated_at": datetime.utcnow().isoformat(),
        "stats": {
            "cycles_completed": total_cycles,
            "decisions_made": total_decisions,
            "successful_decisions": successful,
            "failed_decisions": failed,
            "success_rate": round(successful / max(total_decisions, 1) * 100, 1),
        },
        "kpis": kpis,
        "recent_lessons": [l.get("lesson", "") for l in lessons],
        "current_priorities": priorities,
    }

    # AI narrative if available
    if llm_provider:
        try:
            system = (
                "You are a CEO writing a weekly performance report. "
                "Be concise (3-5 sentences), highlight wins, flag concerns, suggest next week's focus. "
                "Reply in the same language as the company context."
            )
            user = (
                f"Weekly stats: {total_cycles} cycles, {successful}/{total_decisions} decisions successful.\n"
                f"KPIs: {', '.join(f'{k}: {v}' for k, v in kpis.items() if v)}\n"
                f"Lessons: {'; '.join(l.get('lesson', '')[:80] for l in lessons)}\n"
                f"Priorities: {', '.join(priorities)}"
            )
            narrative = await llm_provider.complete(system, user, temperature=0.4, max_tokens=300)
            report["narrative"] = narrative.strip()
        except Exception as e:
            report["narrative"] = (
                f"Weekly report: {total_cycles} cycles completed, "
                f"{successful}/{total_decisions} decisions successful. "
                f"{'Focus on improving outcomes.' if failed > successful else 'Good progress this week.'}"
            )
    else:
        report["narrative"] = f"{total_cycles} cycles, {successful}/{total_decisions} decisions successful."

    return report
