import json
import logging
from datetime import datetime
from pathlib import Path

from core.json_parser import parse_llm_json
from core.llm_provider import LLMProvider

logger = logging.getLogger("svos.company_dna")


class CompanyDNA:
    """بصمة الشركة الرقمية — هوية فريدة تتطور مع الوقت."""

    def __init__(self, company_id: str = "default", data_dir: str = "workspace/dna"):
        self.company_id = company_id
        self.data_dir = Path(data_dir).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.llm = LLMProvider()
        self.dna: dict = {}
        self._load()

    def _file(self) -> Path:
        return self.data_dir / f"{self.company_id}_dna.json"

    def _default_dna(self) -> dict:
        return {
            "company_id": self.company_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
            "identity": {"name": "", "mission": "", "vision": "", "values": []},
            "personality": {
                "tone": "professional",
                "risk_appetite": "moderate",
                "decision_speed": "balanced",
                "innovation_level": "high",
            },
            "strengths": [],
            "weaknesses": [],
            "learned_lessons": [],
            "decision_patterns": [],
            "market_position": {"segment": "", "differentiation": "", "competitors": []},
            "evolution_log": [],
            "metrics": {
                "decisions_made": 0,
                "successful_decisions": 0,
                "total_revenue_generated": "0",
                "customers_acquired": 0,
            },
        }

    def _load(self):
        f = self._file()
        if f.exists():
            try:
                self.dna = json.loads(f.read_text("utf-8"))
            except Exception:
                self.dna = self._default_dna()
        else:
            self.dna = self._default_dna()

    def _save(self):
        self.dna["last_updated"] = datetime.utcnow().isoformat()
        self._file().write_text(json.dumps(self.dna, ensure_ascii=False, indent=2), encoding="utf-8")

    def _log_evolution(self, event_type: str, description: str):
        self.dna["evolution_log"].append(
            {"type": event_type, "description": description, "timestamp": datetime.utcnow().isoformat()}
        )
        if len(self.dna["evolution_log"]) > 100:
            self.dna["evolution_log"] = self.dna["evolution_log"][-100:]

    def initialize(self, name: str, mission: str, vision: str, values: list[str], personality: dict | None = None) -> dict:
        self.dna["identity"] = {"name": name, "mission": mission, "vision": vision, "values": values}
        if personality:
            self.dna["personality"].update(personality)
        self._log_evolution("initialized", f"Company DNA created: {name}")
        self._save()
        return self.dna

    def record_decision(self, decision: str, outcome: str, success: bool):
        self.dna["metrics"]["decisions_made"] += 1
        if success:
            self.dna["metrics"]["successful_decisions"] += 1

        pattern = {
            "decision": decision,
            "outcome": outcome,
            "success": success,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.dna["decision_patterns"].append(pattern)
        if len(self.dna["decision_patterns"]) > 50:
            self.dna["decision_patterns"] = self.dna["decision_patterns"][-50:]

        self._log_evolution("decision", f"{'Success' if success else 'Fail'}: {decision[:80]}")
        self._save()

    def record_lesson(self, lesson: str, category: str = "general"):
        self.dna["learned_lessons"].append(
            {"lesson": lesson, "category": category, "timestamp": datetime.utcnow().isoformat()}
        )
        self._log_evolution("lesson", lesson[:80])
        self._save()

    async def evolve(self) -> dict:
        system = (
            "You are an organizational development expert. Analyze this company DNA "
            "and suggest evolution steps. Return ONLY valid JSON."
        )
        user = (
            f"Company DNA: {json.dumps(self.dna, ensure_ascii=False)}\n\n"
            "Return JSON:\n"
            '{"health_score": int, "strengths_identified": [str], '
            '"areas_to_improve": [str], "personality_adjustments": {}, '
            '"strategic_recommendations": [str], "next_evolution_steps": [str]}'
        )

        raw = await self.llm.complete(system, user, max_tokens=2000)
        parsed = parse_llm_json(raw)

        self._log_evolution("evolution_analysis", f"Health: {parsed.get('health_score', '?')}")
        if parsed.get("strengths_identified"):
            self.dna["strengths"] = parsed["strengths_identified"]
        if parsed.get("areas_to_improve"):
            self.dna["weaknesses"] = parsed["areas_to_improve"]
        self._save()

        return {"company_id": self.company_id, "evolution": parsed}

    async def generate_brand_voice(self) -> dict:
        system = "Based on this company DNA, create a unique brand voice guide. Return ONLY valid JSON."
        user = (
            f"DNA: {json.dumps(self.dna['identity'], ensure_ascii=False)}\n"
            f"Personality: {json.dumps(self.dna['personality'], ensure_ascii=False)}\n\n"
            "Return JSON:\n"
            '{"brand_voice": str, "tone_words": [str], "avoid_words": [str], '
            '"sample_tagline": str, "social_media_style": str, '
            '"email_style": str, "elevator_pitch": str}'
        )
        raw = await self.llm.complete(system, user, max_tokens=1500)
        return {"company_id": self.company_id, "brand": parse_llm_json(raw)}

    def get_dna(self) -> dict:
        return self.dna

    def get_success_rate(self) -> float:
        total = self.dna["metrics"]["decisions_made"]
        if total == 0:
            return 0.0
        return round(self.dna["metrics"]["successful_decisions"] / total * 100, 1)
