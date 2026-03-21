"""
SVOS Meeting Engine — Corporate Governance Meetings.

Types: Board Meeting, Executive Standup, Department Review, Strategy Session, Crisis Meeting
Each meeting has: agenda, participants, discussion rounds, voting, minutes, action items.
Secretary agent records everything. Accountability flows down the hierarchy.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any

from core.llm_provider import LLMProvider
from core.json_parser import parse_llm_json

logger = logging.getLogger("svos.meetings")


# ── Corporate Hierarchy ──
HIERARCHY = {
    "board": {
        "level": 0,
        "members": ["BOARD_CHAIR"],
        "reports_to": None,
        "oversees": ["CEO"],
    },
    "CEO": {
        "level": 1,
        "department": "executive",
        "reports_to": "board",
        "oversees": ["CMO", "CFO", "CTO", "COO", "CLO", "CHRO"],
    },
    "CMO": {"level": 2, "department": "marketing", "reports_to": "CEO", "oversees": []},
    "CFO": {"level": 2, "department": "finance", "reports_to": "CEO", "oversees": []},
    "CTO": {"level": 2, "department": "technology", "reports_to": "CEO", "oversees": []},
    "COO": {"level": 2, "department": "operations", "reports_to": "CEO", "oversees": []},
    "CLO": {"level": 2, "department": "legal", "reports_to": "CEO", "oversees": []},
    "CHRO": {"level": 2, "department": "hr", "reports_to": "CEO", "oversees": []},
    "GUARDIAN": {"level": 1, "department": "governance", "reports_to": "board", "oversees": []},
    "RADAR": {"level": 2, "department": "intelligence", "reports_to": "CEO", "oversees": []},
}


# ── Meeting Types ──
MEETING_TYPES = {
    "board_meeting": {
        "name": "Board Meeting",
        "name_ar": "اجتماع مجلس الإدارة",
        "chair": "BOARD_CHAIR",
        "participants": ["CEO", "GUARDIAN"],
        "frequency": "monthly",
        "purpose": "Strategic oversight, CEO accountability, major decisions",
        "max_rounds": 3,
    },
    "executive_standup": {
        "name": "Executive Standup",
        "name_ar": "اجتماع تنفيذي",
        "chair": "CEO",
        "participants": ["CMO", "CFO", "CTO", "COO"],
        "frequency": "weekly",
        "purpose": "Coordinate priorities, resolve blockers, align departments",
        "max_rounds": 2,
    },
    "department_review": {
        "name": "Department Review",
        "name_ar": "مراجعة القسم",
        "chair": "CEO",
        "participants": [],
        "frequency": "weekly",
        "purpose": "Review department performance, set targets",
        "max_rounds": 2,
    },
    "strategy_session": {
        "name": "Strategy Session",
        "name_ar": "جلسة استراتيجية",
        "chair": "CEO",
        "participants": ["CFO", "CTO", "CMO"],
        "frequency": "on_demand",
        "purpose": "Major strategic decisions requiring multi-perspective analysis",
        "max_rounds": 3,
    },
    "crisis_meeting": {
        "name": "Crisis Meeting",
        "name_ar": "اجتماع طوارئ",
        "chair": "CEO",
        "participants": ["CFO", "CTO", "COO", "CLO", "GUARDIAN"],
        "frequency": "emergency",
        "purpose": "Address critical system or business failures",
        "max_rounds": 2,
    },
}


class MeetingEngine:
    """Runs corporate meetings with real multi-agent discussion."""

    def __init__(self, llm_provider: LLMProvider | None = None):
        self.llm = llm_provider or LLMProvider()

    async def run_meeting(
        self,
        meeting_type: str,
        agenda: list[str],
        context: dict = None,
        company_state: dict = None,
        department: str = "",
    ) -> dict:
        meeting_id = f"mtg_{uuid.uuid4().hex[:8]}"
        config = MEETING_TYPES.get(meeting_type, MEETING_TYPES["executive_standup"])
        context = context or {}

        participants = list(config["participants"])
        if meeting_type == "department_review" and department:
            dept_head = self._get_department_head(department)
            if dept_head:
                participants = [dept_head]

        chair = config["chair"]
        all_attendees = [chair] + [p for p in participants if p != chair]

        state_context = ""
        if company_state:
            identity = company_state.get("identity", {})
            status = company_state.get("current_status", {})
            kpis = company_state.get("kpis", {})
            state_context = (
                f"Company: {identity.get('company_name', 'SVOS')} | "
                f"Phase: {status.get('phase', 'startup')} | "
                f"Priorities: {', '.join(status.get('top_priorities', [])[:3])} | "
                f"KPIs: {', '.join(f'{k}={v}' for k, v in kpis.items() if v)}"
            )

        meeting_start = datetime.utcnow()
        logger.info(f"Meeting {meeting_id} started: {config['name']} | Chair: {chair} | Attendees: {all_attendees}")

        # ── Discussion Rounds ──
        all_opinions = []
        rounds = []

        for round_num in range(1, config["max_rounds"] + 1):
            round_opinions = []
            for agent_role in all_attendees:
                opinion = await self._get_agent_opinion(
                    agent_role=agent_role,
                    meeting_type=meeting_type,
                    agenda=agenda,
                    round_num=round_num,
                    prior_opinions=all_opinions,
                    state_context=state_context,
                    context=context,
                )
                round_opinions.append(opinion)
                all_opinions.append(opinion)

            rounds.append({"round": round_num, "opinions": round_opinions})

            avg_confidence = sum(o.get("confidence", 0.5) for o in round_opinions) / max(len(round_opinions), 1)
            if round_num >= 2 and avg_confidence >= 0.85:
                logger.info(f"Early consensus at round {round_num} (confidence: {avg_confidence:.2f})")
                break

        # ── Voting ──
        votes = await self._conduct_vote(all_attendees, agenda, all_opinions)

        # ── Minutes ──
        minutes = await self._generate_minutes(
            meeting_id, meeting_type, config, chair, all_attendees,
            agenda, rounds, votes, state_context, meeting_start,
        )

        # ── Action Items ──
        action_items = await self._extract_action_items(agenda, rounds, votes, all_attendees)

        return {
            "meeting_id": meeting_id,
            "type": meeting_type,
            "type_name": config["name"],
            "type_name_ar": config["name_ar"],
            "chair": chair,
            "attendees": all_attendees,
            "agenda": agenda,
            "started_at": meeting_start.isoformat(),
            "ended_at": datetime.utcnow().isoformat(),
            "duration_seconds": (datetime.utcnow() - meeting_start).total_seconds(),
            "rounds": rounds,
            "votes": votes,
            "minutes": minutes,
            "action_items": action_items,
            "consensus": votes.get("consensus", 0),
            "decision": votes.get("final_decision", "no_decision"),
        }

    async def _get_agent_opinion(
        self, agent_role, meeting_type, agenda, round_num,
        prior_opinions, state_context, context,
    ) -> dict:
        role_context = HIERARCHY.get(agent_role, {})
        department = role_context.get("department", "general")

        prior_summary = ""
        if prior_opinions:
            prior_summary = "\n".join(
                f"- {o['agent']} (R{o['round']}): {o['stance'][:100]} [confidence: {o['confidence']}]"
                for o in prior_opinions[-8:]
            )

        system = (
            f"You are {agent_role}, head of {department} department.\n"
            f"Meeting: {MEETING_TYPES.get(meeting_type, {}).get('name', 'meeting')}. Round {round_num}.\n"
            f"{state_context}\n\n"
            f"{'Previous opinions:\n' + prior_summary if prior_summary else 'Opening round.'}\n\n"
            "Give your professional opinion. Return JSON:\n"
            "{\"stance\": str, \"confidence\": float 0-1, \"rationale\": str, "
            "\"concerns\": [str], \"recommendations\": [str]}"
        )
        user = "Agenda:\n" + "\n".join(f"{i+1}. {a}" for i, a in enumerate(agenda))
        if context:
            user += f"\n\nContext: {json.dumps(context, ensure_ascii=False)[:500]}"

        try:
            schema = {
                "type": "object",
                "properties": {
                    "stance": {"type": "string"},
                    "confidence": {"type": "number"},
                    "rationale": {"type": "string"},
                    "concerns": {"type": "array", "items": {"type": "string"}},
                    "recommendations": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["stance", "confidence", "rationale"],
            }
            raw = await self.llm.complete_structured(system, user, schema)
            conf = float(raw.get("confidence", 0.5) or 0.5)
            if conf > 1:
                conf = conf / 100.0
            return {
                "agent": agent_role, "round": round_num, "department": department,
                "stance": str(raw.get("stance", "neutral"))[:300],
                "confidence": max(0.0, min(1.0, conf)),
                "rationale": str(raw.get("rationale", ""))[:300],
                "concerns": (raw.get("concerns") or [])[:3],
                "recommendations": (raw.get("recommendations") or [])[:3],
            }
        except Exception as e:
            return {
                "agent": agent_role, "round": round_num, "department": department,
                "stance": "unable to participate", "confidence": 0.0,
                "rationale": str(e)[:200], "concerns": [], "recommendations": [],
            }

    async def _conduct_vote(self, attendees, agenda, opinions) -> dict:
        final_opinions = {}
        for o in opinions:
            final_opinions[o["agent"]] = o

        votes_for, votes_against, abstained = [], [], []
        for agent, opinion in final_opinions.items():
            conf = opinion.get("confidence", 0.5)
            if conf >= 0.6:
                votes_for.append({"agent": agent, "confidence": conf})
            elif conf <= 0.35:
                votes_against.append({"agent": agent, "confidence": conf})
            else:
                abstained.append({"agent": agent, "confidence": conf})

        total = len(final_opinions)
        approval_rate = len(votes_for) / max(total, 1)
        avg_confidence = sum(o.get("confidence", 0.5) for o in final_opinions.values()) / max(total, 1)

        if approval_rate >= 0.66:
            decision = "approved"
        elif approval_rate <= 0.33:
            decision = "rejected"
        else:
            decision = "escalated"

        return {
            "total_voters": total,
            "votes_for": votes_for, "votes_against": votes_against, "abstained": abstained,
            "approval_rate": round(approval_rate, 2),
            "consensus": round(avg_confidence, 2),
            "final_decision": decision,
        }

    async def _generate_minutes(
        self, meeting_id, meeting_type, config, chair, attendees,
        agenda, rounds, votes, state_context, started_at,
    ) -> str:
        try:
            system = (
                "You are the meeting secretary. Write formal meeting minutes. "
                "Include: type, date, attendees, agenda, key opinions, votes, decision, action items. "
                "Be concise and professional. Reply in same language as context."
            )
            opinions_text = ""
            for r in rounds:
                opinions_text += f"\n--- Round {r['round']} ---\n"
                for o in r["opinions"]:
                    opinions_text += (
                        f"{o['agent']}: {o['stance'][:100]} (confidence: {o['confidence']:.0%})"
                        f"{'| Concerns: ' + ', '.join(o.get('concerns', [])[:2]) if o.get('concerns') else ''}\n"
                    )
            user = (
                f"Meeting: {config['name']} ({config['name_ar']})\n"
                f"Date: {started_at.strftime('%Y-%m-%d %H:%M')}\nChair: {chair}\n"
                f"Attendees: {', '.join(attendees)}\n{state_context}\n\n"
                f"Agenda:\n" + "\n".join(f"- {a}" for a in agenda) +
                f"\n\nDiscussion:\n{opinions_text}\n\n"
                f"Vote: {votes['final_decision']} (For: {len(votes['votes_for'])}, "
                f"Against: {len(votes['votes_against'])}, Abstained: {len(votes['abstained'])})\n"
                f"Consensus: {votes['consensus']:.0%}"
            )
            return (await self.llm.complete(system, user, temperature=0.3, max_tokens=800)).strip()
        except Exception as e:
            return (
                f"Minutes: {config['name']} | {started_at.isoformat()}\n"
                f"Attendees: {', '.join(attendees)}\nAgenda: {'; '.join(agenda)}\n"
                f"Decision: {votes.get('final_decision', 'N/A')} | Consensus: {votes.get('consensus', 0):.0%}\n"
            )

    async def _extract_action_items(self, agenda, rounds, votes, attendees) -> list[dict]:
        try:
            all_recs = []
            for r in rounds:
                for o in r["opinions"]:
                    all_recs.extend(o.get("recommendations", []))
            system = (
                "Extract 3-5 action items from these recommendations. "
                "Each: {\"description\": str, \"assigned_to\": str, \"deadline_days\": int}. "
                "Return JSON array."
            )
            user = f"Attendees: {', '.join(attendees)}\nRecommendations:\n" + "\n".join(f"- {r}" for r in all_recs[:15])
            schema = {"type": "array", "items": {"type": "object", "properties": {
                "description": {"type": "string"}, "assigned_to": {"type": "string"}, "deadline_days": {"type": "integer"},
            }, "required": ["description", "assigned_to"]}}
            raw = await self.llm.complete_structured(system, user, schema)
            if isinstance(raw, list):
                return [{"description": a.get("description", "")[:200], "assigned_to": a.get("assigned_to", "CEO"),
                         "deadline_days": a.get("deadline_days", 7), "status": "pending"} for a in raw[:5]]
        except Exception as e:
            logger.warning(f"Action item extraction failed: {e}")
        return [{"description": a, "assigned_to": "CEO", "deadline_days": 7, "status": "pending"} for a in agenda[:3]]

    def _get_department_head(self, department: str) -> str | None:
        for role, info in HIERARCHY.items():
            if info.get("department") == department.lower():
                return role
        return None

    # ── Accountability: Performance Review ──
    async def performance_review(self, reviewer: str, reviewee: str, kpis: dict, company_state: dict = None) -> dict:
        reviewer_info = HIERARCHY.get(reviewer, {})
        if reviewee not in reviewer_info.get("oversees", []):
            return {"error": f"{reviewer} does not oversee {reviewee}"}
        state_context = f"Company KPIs: {json.dumps(kpis, ensure_ascii=False)}" if kpis else ""
        system = (
            f"You are {reviewer}, reviewing {reviewee}'s performance.\n{state_context}\n\n"
            "Return JSON: {\"rating\": float 0-10, \"strengths\": [str], \"weaknesses\": [str], "
            "\"recommendations\": [str], \"overall_assessment\": str}"
        )
        try:
            schema = {"type": "object", "properties": {
                "rating": {"type": "number"}, "strengths": {"type": "array", "items": {"type": "string"}},
                "weaknesses": {"type": "array", "items": {"type": "string"}},
                "recommendations": {"type": "array", "items": {"type": "string"}},
                "overall_assessment": {"type": "string"},
            }, "required": ["rating", "overall_assessment"]}
            result = await self.llm.complete_structured(system, f"KPIs for {reviewee}: {json.dumps(kpis)}", schema)
            return {
                "reviewer": reviewer, "reviewee": reviewee,
                "rating": min(10, max(0, float(result.get("rating", 5)))),
                "strengths": result.get("strengths", [])[:3],
                "weaknesses": result.get("weaknesses", [])[:3],
                "recommendations": result.get("recommendations", [])[:3],
                "overall_assessment": str(result.get("overall_assessment", ""))[:300],
                "reviewed_at": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {"reviewer": reviewer, "reviewee": reviewee, "error": str(e)}


# ── Storage ──
def save_meeting(customer_id: str, meeting: dict):
    from core.tenant import get_tenant_dir
    meetings_dir = get_tenant_dir(customer_id) / "meetings"
    meetings_dir.mkdir(parents=True, exist_ok=True)
    path = meetings_dir / f"{meeting['meeting_id']}.json"
    path.write_text(json.dumps(meeting, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def list_meetings(customer_id: str, limit: int = 20) -> list[dict]:
    from core.tenant import get_tenant_dir
    meetings_dir = get_tenant_dir(customer_id) / "meetings"
    if not meetings_dir.exists():
        return []
    meetings = []
    for f in sorted(meetings_dir.glob("*.json"), reverse=True)[:limit]:
        try:
            data = json.loads(f.read_text("utf-8"))
            meetings.append({
                "meeting_id": data.get("meeting_id"), "type": data.get("type"),
                "type_name": data.get("type_name"), "chair": data.get("chair"),
                "attendees": data.get("attendees"), "decision": data.get("decision"),
                "consensus": data.get("consensus"), "started_at": data.get("started_at"),
                "action_items_count": len(data.get("action_items", [])),
            })
        except Exception:
            pass
    return meetings
