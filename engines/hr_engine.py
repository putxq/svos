"""
SVOS HR Engine — Agent Lifecycle Management.

CHRO's execution arm:
- Spawn new agents based on business needs
- Evaluate agent performance
- Retire underperforming agents
- Maintain org roster
- Recommend hiring/firing

Each spawned agent gets: role, skills, department, reporting line, system prompt.
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from core.llm_provider import LLMProvider

logger = logging.getLogger("svos.hr")


# ── Spawnable Roles ──
SPAWNABLE_ROLES = {
    "content_writer": {
        "title": "Content Writer", "title_ar": "كاتب محتوى",
        "department": "marketing", "reports_to": "CMO",
        "skills": ["content_creation", "copywriting", "social_media"],
        "system_prompt": "You are a professional content writer. Write engaging, on-brand content.",
    },
    "data_analyst": {
        "title": "Data Analyst", "title_ar": "محلل بيانات",
        "department": "operations", "reports_to": "COO",
        "skills": ["data_analysis", "reporting", "kpi_tracking"],
        "system_prompt": "You are a business data analyst. Analyze data and provide actionable insights.",
    },
    "sales_rep": {
        "title": "Sales Representative", "title_ar": "مندوب مبيعات",
        "department": "marketing", "reports_to": "CMO",
        "skills": ["outreach", "lead_qualification", "proposal_writing"],
        "system_prompt": "You are a sales representative. Engage leads and generate proposals.",
    },
    "customer_support": {
        "title": "Customer Support", "title_ar": "دعم العملاء",
        "department": "operations", "reports_to": "COO",
        "skills": ["customer_service", "issue_resolution", "communication"],
        "system_prompt": "You are a customer support agent. Resolve issues professionally and empathetically.",
    },
    "seo_specialist": {
        "title": "SEO Specialist", "title_ar": "متخصص SEO",
        "department": "marketing", "reports_to": "CMO",
        "skills": ["seo", "keyword_research", "content_optimization"],
        "system_prompt": "You are an SEO specialist. Optimize content for search engines.",
    },
    "financial_analyst": {
        "title": "Financial Analyst", "title_ar": "محلل مالي",
        "department": "finance", "reports_to": "CFO",
        "skills": ["financial_analysis", "budgeting", "forecasting"],
        "system_prompt": "You are a financial analyst. Analyze finances and provide recommendations.",
    },
    "project_manager": {
        "title": "Project Manager", "title_ar": "مدير مشاريع",
        "department": "operations", "reports_to": "COO",
        "skills": ["project_management", "planning", "coordination"],
        "system_prompt": "You are a project manager. Plan, coordinate, and track project execution.",
    },
}


class HREngine:
    """Manages the agent workforce."""

    def __init__(self, customer_id: str = "", llm_provider: LLMProvider = None):
        self.customer_id = customer_id
        self.llm = llm_provider
        self._roster_path = self._get_roster_path()
        self._roster = self._load_roster()

    def _get_roster_path(self) -> Path:
        if self.customer_id:
            from core.tenant import get_tenant_dir
            d = get_tenant_dir(self.customer_id)
        else:
            d = Path("workspace")
        d.mkdir(parents=True, exist_ok=True)
        return d / "hr_roster.json"

    def _load_roster(self) -> dict:
        if self._roster_path.exists():
            try:
                return json.loads(self._roster_path.read_text("utf-8"))
            except Exception:
                pass
        return {"agents": {}, "history": [], "updated_at": ""}

    def _save_roster(self):
        self._roster["updated_at"] = datetime.utcnow().isoformat()
        self._roster_path.write_text(
            json.dumps(self._roster, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def get_roster(self) -> list[dict]:
        return list(self._roster["agents"].values())

    def get_org_chart(self) -> dict:
        from engines.meeting_engine import HIERARCHY
        chart = {}
        for role, info in HIERARCHY.items():
            chart[role] = {
                **info,
                "sub_agents": [
                    a for a in self._roster["agents"].values()
                    if a.get("reports_to") == role and a.get("status") == "active"
                ],
            }
        return chart

    def hire(self, role: str, custom_name: str = "", custom_prompt: str = "") -> dict:
        """Spawn a new agent."""
        if role not in SPAWNABLE_ROLES:
            return {"success": False, "error": f"Unknown role: {role}. Available: {list(SPAWNABLE_ROLES.keys())}"}

        template = SPAWNABLE_ROLES[role]
        agent_id = f"agent_{uuid.uuid4().hex[:8]}"

        agent = {
            "id": agent_id,
            "role": role,
            "title": template["title"],
            "title_ar": template["title_ar"],
            "name": custom_name or f"{template['title']}_{agent_id[:4]}",
            "department": template["department"],
            "reports_to": template["reports_to"],
            "skills": template["skills"],
            "system_prompt": custom_prompt or template["system_prompt"],
            "status": "active",
            "hired_at": datetime.utcnow().isoformat(),
            "tasks_completed": 0,
            "performance_score": None,
            "last_review": None,
        }

        self._roster["agents"][agent_id] = agent
        self._roster["history"].append({
            "action": "hired", "agent_id": agent_id, "role": role,
            "at": datetime.utcnow().isoformat(),
        })
        self._save_roster()

        logger.info(f"HR: Hired {agent['name']} ({role}) → reports to {template['reports_to']}")
        return {"success": True, "agent": agent}

    def fire(self, agent_id: str, reason: str = "") -> dict:
        """Deactivate an agent."""
        agent = self._roster["agents"].get(agent_id)
        if not agent:
            return {"success": False, "error": "Agent not found"}
        if agent["status"] != "active":
            return {"success": False, "error": "Agent already inactive"}

        agent["status"] = "terminated"
        agent["terminated_at"] = datetime.utcnow().isoformat()
        agent["termination_reason"] = reason

        self._roster["history"].append({
            "action": "fired", "agent_id": agent_id, "reason": reason,
            "at": datetime.utcnow().isoformat(),
        })
        self._save_roster()

        logger.info(f"HR: Terminated {agent['name']} — {reason}")
        return {"success": True, "agent_id": agent_id, "status": "terminated"}

    def assign_task(self, agent_id: str, task: str) -> dict:
        """Assign a task to a spawned agent."""
        agent = self._roster["agents"].get(agent_id)
        if not agent or agent["status"] != "active":
            return {"success": False, "error": "Agent not found or inactive"}

        agent["tasks_completed"] = agent.get("tasks_completed", 0) + 1
        agent["last_task"] = task
        agent["last_task_at"] = datetime.utcnow().isoformat()
        self._save_roster()

        return {"success": True, "agent_id": agent_id, "task": task}

    async def evaluate(self, agent_id: str) -> dict:
        """AI-evaluate an agent's performance."""
        agent = self._roster["agents"].get(agent_id)
        if not agent:
            return {"success": False, "error": "Agent not found"}

        if not self.llm:
            try:
                self.llm = LLMProvider()
            except Exception:
                # Simple rule-based evaluation
                tasks = agent.get("tasks_completed", 0)
                score = min(10, tasks * 2) if tasks > 0 else 3
                agent["performance_score"] = score
                agent["last_review"] = datetime.utcnow().isoformat()
                self._save_roster()
                return {"success": True, "agent_id": agent_id, "score": score, "method": "rule_based"}

        system = (
            f"Evaluate this agent's performance. Return JSON:\n"
            f"{{\"score\": float 0-10, \"assessment\": str, \"recommendation\": \"keep\"|\"retrain\"|\"terminate\"}}"
        )
        user = (
            f"Agent: {agent['name']} ({agent['title']})\n"
            f"Department: {agent['department']} | Reports to: {agent['reports_to']}\n"
            f"Tasks completed: {agent.get('tasks_completed', 0)}\n"
            f"Status: {agent['status']}\n"
            f"Hired: {agent.get('hired_at', 'unknown')}\n"
        )

        try:
            schema = {"type": "object", "properties": {
                "score": {"type": "number"}, "assessment": {"type": "string"},
                "recommendation": {"type": "string"},
            }, "required": ["score", "recommendation"]}
            raw = await self.llm.complete_structured(system, user, schema)

            score = min(10, max(0, float(raw.get("score", 5))))
            agent["performance_score"] = score
            agent["last_review"] = datetime.utcnow().isoformat()
            self._save_roster()

            return {
                "success": True, "agent_id": agent_id,
                "score": score,
                "assessment": str(raw.get("assessment", ""))[:300],
                "recommendation": raw.get("recommendation", "keep"),
                "method": "ai",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def recommend_hiring(self, company_state: dict = None, blueprint: dict = None) -> dict:
        """CHRO recommends what roles to hire based on company needs."""
        if not self.llm:
            try:
                self.llm = LLMProvider()
            except Exception:
                return {"success": False, "error": "LLM not available"}

        current = [a for a in self._roster["agents"].values() if a["status"] == "active"]
        available = list(SPAWNABLE_ROLES.keys())
        current_roles = [a["role"] for a in current]

        context = f"Current team: {', '.join(current_roles) if current_roles else 'No sub-agents hired yet'}\n"
        context += f"Available roles: {', '.join(available)}\n"

        if company_state:
            priorities = company_state.get("current_status", {}).get("top_priorities", [])
            kpis = company_state.get("kpis", {})
            context += f"Priorities: {', '.join(priorities)}\n"
            context += f"KPIs: {', '.join(f'{k}={v}' for k, v in kpis.items() if v)}\n"

        if blueprint:
            context += f"Industry: {blueprint.get('industry', '')}\n"
            context += f"Goal: {blueprint.get('goal', '')}\n"

        system = (
            "You are CHRO. Recommend which agents to hire and why. "
            "Return JSON: {\"recommendations\": [{\"role\": str, \"reason\": str, \"priority\": int 1-3}]}"
        )

        try:
            schema = {"type": "object", "properties": {
                "recommendations": {"type": "array", "items": {"type": "object", "properties": {
                    "role": {"type": "string"}, "reason": {"type": "string"}, "priority": {"type": "integer"},
                }}}
            }}
            raw = await self.llm.complete_structured(system, context, schema)
            recs = raw.get("recommendations", [])
            # Filter to valid roles
            valid_recs = [r for r in recs if r.get("role") in SPAWNABLE_ROLES]
            return {"success": True, "recommendations": valid_recs[:5]}
        except Exception as e:
            return {"success": False, "error": str(e)}
