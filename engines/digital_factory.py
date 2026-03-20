import json
import logging
from datetime import datetime
from pathlib import Path

from core.llm_provider import LLMProvider
from core.json_parser import parse_llm_json

logger = logging.getLogger("svos.digital_factory")


class DigitalFactory:
    """المصنع الرقمي — خطوط إنتاج كاملة."""

    def __init__(self, output_dir: str = "workspace/factory_output"):
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.llm = LLMProvider()
        self.production_log: list[dict] = []

    def _save_output(self, factory_name: str, product_name: str, content: str, ext: str = "md") -> str:
        factory_dir = self.output_dir / factory_name
        factory_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        safe_name = "".join(c if c.isalnum() or c in "_ -" else "_" for c in product_name)[:40]
        filepath = factory_dir / f"{timestamp}_{safe_name}.{ext}"
        filepath.write_text(content, encoding="utf-8")
        return str(filepath)

    def _log_production(self, factory: str, product: str, filepath: str, quality: str):
        entry = {
            "factory": factory,
            "product": product,
            "filepath": filepath,
            "quality": quality,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.production_log.append(entry)
        logger.info(f"Factory [{factory}]: produced {product}")

    async def produce_content(
        self,
        topic: str,
        business: str,
        platforms: list[str] = None,
        tone: str = "professional",
        language: str = "ar",
    ) -> dict:
        platforms = platforms or ["linkedin", "twitter", "blog"]
        system = (
            "You are an expert content factory. Produce high-quality content for each platform. "
            "Each piece must be tailored to the platform's style and audience. "
            f"Tone: {tone}. Language: {'Arabic' if language == 'ar' else 'English'}. "
            "Return ONLY valid JSON."
        )
        user = (
            f"Business: {business}\nTopic: {topic}\n"
            f"Produce content for: {', '.join(platforms)}\n\n"
            "Return JSON:\n"
            "{\"products\": [{\"platform\": str, \"title\": str, \"content\": str, "
            "\"hashtags\": [str], \"best_time\": str, \"estimated_reach\": str}]}"
        )
        raw = await self.llm.complete(system, user, max_tokens=3000)
        parsed = parse_llm_json(raw)
        products = parsed.get("products", [])

        saved_files = []
        for p in products:
            platform = p.get("platform", "general")
            content_text = f"# {p.get('title', topic)}\n\n{p.get('content', '')}"
            if p.get("hashtags"):
                content_text += f"\n\n---\nHashtags: {' '.join(p['hashtags'])}"
            filepath = self._save_output("content", f"{platform}_{topic[:20]}", content_text)
            saved_files.append(filepath)
            self._log_production("content", f"{platform}: {topic[:30]}", filepath, "standard")

        return {
            "factory": "content",
            "topic": topic,
            "platforms": len(products),
            "products": products,
            "saved_files": saved_files,
        }

    async def produce_strategy(
        self,
        business: str,
        goals: list[str],
        timeframe: str = "90 days",
        constraints: list[str] = None,
    ) -> dict:
        constraints = constraints or []
        system = (
            "You are a McKinsey-level strategy consultant. "
            "Produce a comprehensive, actionable strategic plan. "
            "Include: SWOT, competitive positioning, milestones, KPIs, risk mitigation. "
            "Be extremely specific — no generic advice. "
            "Return ONLY valid JSON."
        )
        user = (
            f"Business: {business}\n"
            f"Goals: {json.dumps(goals, ensure_ascii=False)}\n"
            f"Timeframe: {timeframe}\n"
            f"Constraints: {json.dumps(constraints, ensure_ascii=False)}\n\n"
            "Return JSON:\n"
            "{\"executive_summary\": str, \"swot\": {\"strengths\": [], \"weaknesses\": [], "
            "\"opportunities\": [], \"threats\": []}, \"strategic_pillars\": [{\"name\": str, "
            "\"objective\": str, \"actions\": [str], \"kpi\": str, \"owner\": str}], "
            "\"milestones\": [{\"week\": int, \"milestone\": str, \"deliverable\": str}], "
            "\"budget_allocation\": {}, \"risks\": [{\"risk\": str, \"mitigation\": str}], "
            "\"success_criteria\": str}"
        )
        raw = await self.llm.complete(system, user, max_tokens=4000)
        parsed = parse_llm_json(raw)

        doc = f"# Strategic Plan: {business}\n\n"
        doc += f"## Executive Summary\n{parsed.get('executive_summary', '')}\n\n"
        swot = parsed.get("swot", {})
        doc += "## SWOT Analysis\n"
        for key in ["strengths", "weaknesses", "opportunities", "threats"]:
            doc += f"\n### {key.title()}\n"
            for item in swot.get(key, []):
                doc += f"- {item}\n"
        doc += "\n## Strategic Pillars\n"
        for pillar in parsed.get("strategic_pillars", []):
            doc += f"\n### {pillar.get('name', '')}\n"
            doc += f"**Objective:** {pillar.get('objective', '')}\n"
            doc += f"**KPI:** {pillar.get('kpi', '')}\n"
            doc += f"**Owner:** {pillar.get('owner', '')}\n"
            for action in pillar.get("actions", []):
                doc += f"- {action}\n"
        doc += "\n## Milestones\n"
        for ms in parsed.get("milestones", []):
            doc += f"- Week {ms.get('week', '?')}: {ms.get('milestone', '')} -> {ms.get('deliverable', '')}\n"

        filepath = self._save_output("strategy", f"plan_{business[:20]}", doc)
        self._log_production("strategy", f"Strategic Plan: {business[:30]}", filepath, "premium")
        return {"factory": "strategy", "business": business, "plan": parsed, "saved_to": filepath}

    async def produce_analysis(self, business: str, data_description: str, analysis_goal: str) -> dict:
        system = (
            "You are a senior business analyst. Produce a comprehensive data analysis report. "
            "Include: key findings, trends, anomalies, recommendations, visualizations suggestions. "
            "Return ONLY valid JSON."
        )
        user = (
            f"Business: {business}\n"
            f"Data: {data_description}\n"
            f"Analysis goal: {analysis_goal}\n\n"
            "Return JSON:\n"
            "{\"title\": str, \"key_findings\": [str], \"trends\": [str], "
            "\"anomalies\": [str], \"recommendations\": [{\"action\": str, \"impact\": str, \"effort\": str}], "
            "\"data_gaps\": [str], \"next_steps\": [str]}"
        )
        raw = await self.llm.complete(system, user, max_tokens=3000)
        parsed = parse_llm_json(raw)

        doc = f"# Analysis Report: {parsed.get('title', analysis_goal)}\n\n"
        doc += f"**Business:** {business}\n**Goal:** {analysis_goal}\n\n"
        doc += "## Key Findings\n"
        for f in parsed.get("key_findings", []):
            doc += f"- {f}\n"
        doc += "\n## Trends\n"
        for t in parsed.get("trends", []):
            doc += f"- {t}\n"
        doc += "\n## Recommendations\n"
        for r in parsed.get("recommendations", []):
            doc += f"- {r.get('action', '')} (Impact: {r.get('impact', '?')}, Effort: {r.get('effort', '?')})\n"

        filepath = self._save_output("analysis", f"report_{business[:20]}", doc)
        self._log_production("analysis", f"Analysis: {analysis_goal[:30]}", filepath, "standard")
        return {"factory": "analysis", "report": parsed, "saved_to": filepath}

    async def produce_digital_product(
        self,
        product_type: str,
        topic: str,
        target_audience: str,
        business: str = "",
    ) -> dict:
        product_prompts = {
            "ebook": {
                "desc": "a complete ebook outline with chapter summaries",
                "schema": "{\"title\": str, \"subtitle\": str, \"chapters\": [{\"number\": int, \"title\": str, \"summary\": str, \"key_points\": [str]}], \"total_pages_estimate\": int, \"target_price\": str}",
            },
            "course_outline": {
                "desc": "a complete online course curriculum",
                "schema": "{\"course_title\": str, \"modules\": [{\"number\": int, \"title\": str, \"lessons\": [{\"title\": str, \"duration_min\": int, \"type\": str}], \"assignment\": str}], \"total_hours\": int, \"target_price\": str, \"platform\": str}",
            },
            "saas_spec": {
                "desc": "a complete SaaS product specification",
                "schema": "{\"product_name\": str, \"tagline\": str, \"problem\": str, \"solution\": str, \"features\": [{\"name\": str, \"description\": str, \"priority\": str}], \"tech_stack\": [str], \"pricing_tiers\": [{\"name\": str, \"price\": str, \"features\": [str]}], \"mvp_timeline\": str}",
            },
            "template_pack": {
                "desc": "a professional template pack",
                "schema": "{\"pack_name\": str, \"templates\": [{\"name\": str, \"purpose\": str, \"sections\": [str], \"content\": str}], \"total_templates\": int, \"target_price\": str}",
            },
            "checklist": {
                "desc": "a comprehensive professional checklist",
                "schema": "{\"title\": str, \"categories\": [{\"name\": str, \"items\": [{\"task\": str, \"details\": str, \"critical\": bool}]}], \"total_items\": int}",
            },
        }
        if product_type not in product_prompts:
            return {"error": f"Unknown product type: {product_type}. Available: {list(product_prompts.keys())}"}
        prompt_info = product_prompts[product_type]
        system = (
            f"You are a digital product creator. Create {prompt_info['desc']}. "
            "Make it comprehensive, professional, and ready to sell. "
            "Return ONLY valid JSON."
        )
        user = (
            f"Topic: {topic}\nTarget audience: {target_audience}\n"
            f"Business context: {business}\n\n"
            f"Return JSON matching this schema:\n{prompt_info['schema']}"
        )
        raw = await self.llm.complete(system, user, max_tokens=4000)
        parsed = parse_llm_json(raw)

        title = parsed.get("title", parsed.get("product_name", parsed.get("course_title", parsed.get("pack_name", topic))))
        doc = f"# {title}\n\n" + json.dumps(parsed, ensure_ascii=False, indent=2)
        filepath = self._save_output("products", f"{product_type}_{topic[:20]}", doc)
        self._log_production("products", f"{product_type}: {topic[:30]}", filepath, "premium")
        return {"factory": "products", "product_type": product_type, "product": parsed, "saved_to": filepath}

    async def fleet_insight(self, companies: list[dict]) -> dict:
        system = (
            "You are a fleet intelligence analyst. Analyze multiple companies and extract "
            "common success patterns, shared risks, and cross-company opportunities."
            "Return ONLY valid JSON."
        )
        user = (
            f"Companies in fleet: {json.dumps(companies, ensure_ascii=False)}\n\n"
            "Return JSON:\n"
            "{\"success_patterns\": [str], \"shared_risks\": [str], "
            "\"cross_opportunities\": [str], \"recommended_knowledge_transfer\": [str], "
            "\"fleet_health_score\": int}"
        )
        raw = await self.llm.complete(system, user, max_tokens=2000)
        parsed = parse_llm_json(raw)
        filepath = self._save_output("fleet", "fleet_insight", json.dumps(parsed, ensure_ascii=False, indent=2))
        self._log_production("fleet", "Fleet Analysis", filepath, "premium")
        return {"factory": "fleet_learning", "insight": parsed, "saved_to": filepath}

    def get_production_log(self) -> list[dict]:
        return self.production_log

    def get_stats(self) -> dict:
        factories = {}
        for entry in self.production_log:
            f = entry["factory"]
            factories[f] = factories.get(f, 0) + 1
        return {
            "total_produced": len(self.production_log),
            "by_factory": factories,
            "last_production": self.production_log[-1] if self.production_log else None,
        }
