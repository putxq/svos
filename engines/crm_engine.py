import json
import uuid
import logging
from datetime import datetime
from pathlib import Path

from core.llm_provider import LLMProvider
from core.json_parser import parse_llm_json

logger = logging.getLogger("svos.crm")


class CRMEngine:
    STAGES = ["lead", "qualified", "proposal", "negotiation", "won", "lost", "churned"]

    def __init__(self, data_dir: str = "workspace/crm"):
        self.data_dir = Path(data_dir).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.llm = LLMProvider()
        self.contacts: dict[str, dict] = {}
        self.interactions: dict[str, list] = {}
        self._load_data()

    def _data_file(self) -> Path:
        return self.data_dir / "crm_data.json"

    def _load_data(self):
        f = self._data_file()
        if f.exists():
            try:
                data = json.loads(f.read_text("utf-8"))
                self.contacts = data.get("contacts", {})
                self.interactions = data.get("interactions", {})
            except Exception:
                self.contacts, self.interactions = {}, {}

    def _save_data(self):
        data = {
            "contacts": self.contacts,
            "interactions": self.interactions,
            "updated_at": datetime.utcnow().isoformat(),
        }
        self._data_file().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _add_interaction(self, lead_id: str, action: str, details: str):
        if lead_id not in self.interactions:
            self.interactions[lead_id] = []
        self.interactions[lead_id].append(
            {"action": action, "details": details, "timestamp": datetime.utcnow().isoformat()}
        )

    def add_lead(
        self,
        name: str,
        email: str = "",
        phone: str = "",
        company: str = "",
        source: str = "manual",
        notes: str = "",
        value_estimate: str = "",
    ) -> dict:
        lead_id = uuid.uuid4().hex[:10]
        contact = {
            "id": lead_id,
            "name": name,
            "email": email,
            "phone": phone,
            "company": company,
            "source": source,
            "notes": notes,
            "value_estimate": value_estimate,
            "stage": "lead",
            "score": 0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "next_action": "Initial outreach",
            "assigned_to": "CMO",
            "tags": [],
        }
        self.contacts[lead_id] = contact
        self.interactions[lead_id] = []
        self._add_interaction(lead_id, "created", f"Lead added from {source}: {name}")
        self._save_data()
        logger.info(f"CRM: Lead added — {name} ({lead_id})")
        return contact

    def update_stage(self, lead_id: str, new_stage: str, reason: str = "") -> dict:
        if lead_id not in self.contacts:
            return {"error": f"Lead {lead_id} not found"}
        if new_stage not in self.STAGES:
            return {"error": f"Invalid stage: {new_stage}. Valid: {self.STAGES}"}
        old_stage = self.contacts[lead_id]["stage"]
        self.contacts[lead_id]["stage"] = new_stage
        self.contacts[lead_id]["updated_at"] = datetime.utcnow().isoformat()
        self._add_interaction(lead_id, "stage_change", f"Moved from {old_stage} to {new_stage}. Reason: {reason}")
        self._save_data()
        logger.info(f"CRM: {lead_id} moved {old_stage} -> {new_stage}")
        return self.contacts[lead_id]

    def log_interaction(self, lead_id: str, action: str, details: str) -> dict:
        if lead_id not in self.contacts:
            return {"error": f"Lead {lead_id} not found"}
        self._add_interaction(lead_id, action, details)
        self.contacts[lead_id]["updated_at"] = datetime.utcnow().isoformat()
        self._save_data()
        return {"logged": True, "lead_id": lead_id, "action": action}

    async def score_lead(self, lead_id: str) -> dict:
        if lead_id not in self.contacts:
            return {"error": f"Lead {lead_id} not found"}
        contact = self.contacts[lead_id]
        history = self.interactions.get(lead_id, [])
        system = (
            "You are a sales intelligence AI. Score this lead 0-100 based on likelihood to convert. "
            "Consider: company size, engagement level, budget indicators, interaction history. "
            "Return ONLY JSON: {\"score\": int, \"reasoning\": str, \"next_action\": str, \"priority\": str}"
        )
        user = (
            f"Lead: {json.dumps(contact, ensure_ascii=False)}\n"
            f"Interactions ({len(history)}): {json.dumps(history[-5:], ensure_ascii=False)}\n"
            "Score this lead and suggest next action."
        )
        raw = await self.llm.complete(system, user, max_tokens=500)
        parsed = parse_llm_json(raw)
        score = min(100, max(0, int(parsed.get("score", 50))))
        next_action = parsed.get("next_action", "Follow up")
        priority = parsed.get("priority", "medium")
        self.contacts[lead_id]["score"] = score
        self.contacts[lead_id]["next_action"] = next_action
        self.contacts[lead_id]["priority"] = priority
        self._add_interaction(lead_id, "ai_scored", f"Score: {score}. Next: {next_action}")
        self._save_data()
        return {
            "lead_id": lead_id,
            "score": score,
            "reasoning": parsed.get("reasoning", ""),
            "next_action": next_action,
            "priority": priority,
        }

    async def suggest_next_actions(self, lead_id: str) -> dict:
        if lead_id not in self.contacts:
            return {"error": f"Lead {lead_id} not found"}
        contact = self.contacts[lead_id]
        history = self.interactions.get(lead_id, [])
        system = (
            "You are an expert sales strategist. Based on this lead's stage and history, "
            "suggest 3 specific next actions. Be very actionable and specific. "
            "Return ONLY JSON: {\"actions\": [{\"action\": str, \"tool\": str, \"urgency\": str, \"reason\": str}]}"
        )
        user = (
            f"Lead: {json.dumps(contact, ensure_ascii=False)}\n"
            f"History: {json.dumps(history[-5:], ensure_ascii=False)}\n"
            "What should we do next with this lead?"
        )
        raw = await self.llm.complete(system, user, max_tokens=800)
        parsed = parse_llm_json(raw)
        return {
            "lead_id": lead_id,
            "lead_name": contact["name"],
            "stage": contact["stage"],
            "actions": parsed.get("actions", []),
        }

    async def generate_outreach(self, lead_id: str, outreach_type: str = "email") -> dict:
        if lead_id not in self.contacts:
            return {"error": f"Lead {lead_id} not found"}
        contact = self.contacts[lead_id]
        system = (
            f"You are a sales copywriter. Write a personalized {outreach_type} for this lead. "
            "Be concise, professional, and persuasive. "
            "Return ONLY JSON: {\"subject\": str, \"body\": str, \"cta\": str}"
        )
        user = (
            f"Lead: {contact['name']} at {contact['company']}\n"
            f"Stage: {contact['stage']}\n"
            f"Notes: {contact['notes']}\n"
            f"Value: {contact['value_estimate']}\n"
            f"Write a {outreach_type} to move them to the next stage."
        )
        raw = await self.llm.complete(system, user, max_tokens=1000)
        parsed = parse_llm_json(raw)
        self._add_interaction(lead_id, "outreach_generated", f"Type: {outreach_type}")
        self._save_data()
        return {
            "lead_id": lead_id,
            "type": outreach_type,
            "subject": parsed.get("subject", ""),
            "body": parsed.get("body", ""),
            "cta": parsed.get("cta", ""),
        }

    def get_pipeline(self) -> dict:
        pipeline = {stage: [] for stage in self.STAGES}
        for contact in self.contacts.values():
            stage = contact.get("stage", "lead")
            if stage in pipeline:
                pipeline[stage].append(
                    {
                        "id": contact["id"],
                        "name": contact["name"],
                        "company": contact.get("company", ""),
                        "score": contact.get("score", 0),
                        "value": contact.get("value_estimate", ""),
                        "next_action": contact.get("next_action", ""),
                        "updated": contact.get("updated_at", ""),
                    }
                )
        total = len(self.contacts)
        won = len(pipeline.get("won", []))
        conversion = round((won / total * 100), 1) if total > 0 else 0
        return {
            "pipeline": pipeline,
            "total_leads": total,
            "won": won,
            "conversion_rate": conversion,
            "stages_count": {s: len(pipeline[s]) for s in self.STAGES},
        }

    def get_contact(self, lead_id: str) -> dict | None:
        return self.contacts.get(lead_id)

    def get_interactions(self, lead_id: str) -> list:
        return self.interactions.get(lead_id, [])

    def search(self, query: str) -> list:
        query_lower = query.lower()
        results = []
        for c in self.contacts.values():
            if (
                query_lower in c.get("name", "").lower()
                or query_lower in c.get("company", "").lower()
                or query_lower in c.get("notes", "").lower()
                or query_lower in c.get("email", "").lower()
            ):
                results.append(c)
        return results
