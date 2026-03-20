from __future__ import annotations

import json
import re
from typing import Any

from core.json_parser import parse_llm_json, extract_field


class GravityEngine:
    """محرك الجاذبية — يكتشف أين الطلب الحقيقي في السوق"""

    def __init__(self):
        from core.llm_provider import LLMProvider
        from tools.web_search import WebSearchTool

        self.llm = LLMProvider()
        self.search = WebSearchTool()

    @staticmethod
    def _clean_json(text: str) -> str:
        text = (text or "").strip()
        text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return text.strip()

    @staticmethod
    def _safe_json(text: str, fallback: dict[str, Any]) -> dict[str, Any]:
        parsed = parse_llm_json(text)
        return parsed if isinstance(parsed, dict) and parsed else fallback

    async def scan_market(self, industry: str, region: str, service: str) -> dict:
        """
        يمسح السوق ويكتشف الفرص الحقيقية.
        """
        queries = [
            f"{industry} {region} market demand 2026",
            f"{industry} {region} pain points problems",
            f"{service} {industry} {region} competition",
        ]

        gathered: list[dict[str, Any]] = []
        for q in queries:
            res = await self.search.execute(q, max_results=6)
            for item in res.get("results", []):
                item = dict(item)
                item["query"] = q
                gathered.append(item)

        total_results = len(gathered)
        # ??? ?? ????? ? ???? ??? ????
        if total_results == 0:
            fallback_result = await self.search.execute(f"{industry} market opportunity", max_results=5)
            for item in fallback_result.get("results", []):
                item = dict(item)
                item["query"] = f"{industry} market opportunity"
                gathered.append(item)

        compact = []
        for i, r in enumerate(gathered[:18], 1):
            compact.append(
                {
                    "n": i,
                    "query": r.get("query", ""),
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("snippet", ""),
                }
            )

        system_prompt = (
            "You are a market intelligence analyst. "
            "Based on these search results, identify: "
            "1. Top 3 real opportunities (with confidence score 0-100) "
            "2. Top 3 pain points customers have "
            "3. Competition level (low/medium/high) "
            "4. Recommended entry strategy "
            "5. Estimated time to first revenue "
            "Respond in JSON format. "
            "Respond in the same language as the industry/region description."
        )

        user_prompt = (
            f"Industry: {industry}\n"
            f"Region: {region}\n"
            f"Service: {service}\n"
            f"Search results: {json.dumps(compact, ensure_ascii=False)}\n\n"
            "Return JSON with keys: opportunities, pain_points, competition_level, entry_strategy, time_to_revenue."
        )

        raw = await self.llm.complete(system_prompt=system_prompt, user_message=user_prompt)
        raw_response = raw
        parsed = parse_llm_json(raw_response)

        # ?????? ????? ? ?? ???? ?? ????? ??????
        opportunities = extract_field(
            parsed,
            "opportunities",
            "analysis.opportunities",
            "market_opportunities",
            default=[],
        )

        # ???? ??? ?? ????
        clean_opportunities = []
        for opp in opportunities:
            if not isinstance(opp, dict):
                continue
            conf_raw = opp.get("confidence", 0) or 0
            try:
                conf = float(conf_raw)
            except Exception:
                conf = 0.0
            clean_opportunities.append(
                {
                    "title": opp.get("title") or opp.get("opportunity", "Unknown"),
                    "description": opp.get("description") or opp.get("rationale", ""),
                    "confidence": (conf / 100.0) if conf > 1 else conf,
                    "evidence": opp.get("evidence") or opp.get("rationale", ""),
                }
            )

        # ??? ????? ????? ??????
        competition = extract_field(
            parsed,
            "competition_level",
            "analysis.competition_level",
            "competition.level",
            default="unknown",
        )
        entry_strategy = extract_field(
            parsed,
            "entry_strategy",
            "recommended_entry_strategy",
            "analysis.entry_strategy",
            default="",
        )
        time_to_revenue = extract_field(
            parsed,
            "time_to_revenue",
            "time_to_first_revenue",
            "analysis.time_to_revenue",
            default="",
        )
        pain_points = extract_field(
            parsed,
            "pain_points",
            "analysis.pain_points",
            default=[],
        )

        return {
            "industry": industry,
            "region": region,
            "opportunities": clean_opportunities[:3],
            "pain_points": [str(x) for x in pain_points[:3]],
            "competition_level": str(competition),
            "entry_strategy": str(entry_strategy),
            "time_to_revenue": str(time_to_revenue),
            "search_sources": len(queries),
            "raw_search_results": len(gathered),
        }

    async def evaluate_opportunity(self, opportunity: str, context: dict) -> dict:
        """
        يقيّم فرصة واحدة بعمق: ظل أم حفرة؟ سراب أم ماء؟
        """
        system = (
            "Evaluate this business opportunity strictly and return JSON only. "
            "Return keys: is_real, confidence, evidence_for, evidence_against, "
            "recommended_action, risk_level, potential_revenue."
        )
        user = (
            f"Evaluate this business opportunity: {opportunity}\n"
            f"Context: {json.dumps(context, ensure_ascii=False)}\n"
            "Return JSON with: "
            "- is_real: bool "
            "- confidence: float 0-1 "
            "- evidence_for: list "
            "- evidence_against: list "
            "- recommended_action: str "
            "- risk_level: low/medium/high "
            "- potential_revenue: str estimate"
        )

        raw = await self.llm.complete(system_prompt=system, user_message=user)
        parsed = self._safe_json(
            raw,
            fallback={
                "is_real": False,
                "confidence": 0.4,
                "evidence_for": [],
                "evidence_against": ["insufficient structured evidence"],
                "recommended_action": "collect more market evidence",
                "risk_level": "medium",
                "potential_revenue": "unknown",
            },
        )

        conf = float(parsed.get("confidence", 0.0) or 0.0)
        if conf > 1:
            conf = conf / 100.0

        return {
            "is_real": bool(parsed.get("is_real", False)),
            "confidence": max(0.0, min(1.0, conf)),
            "evidence_for": [str(x) for x in (parsed.get("evidence_for") or [])],
            "evidence_against": [str(x) for x in (parsed.get("evidence_against") or [])],
            "recommended_action": str(parsed.get("recommended_action", "")),
            "risk_level": str(parsed.get("risk_level", "medium")),
            "potential_revenue": str(parsed.get("potential_revenue", "unknown")),
        }

    async def find_demand_gravity(self, business_description: str) -> dict:
        """
        الدالة الرئيسية — تستقبل وصف نشاط وترجع خريطة الطلب.
        """
        parse_system = """Extract business parameters from this description.
Return ONLY a JSON object with these exact keys:
{"industry": "...", "region": "...", "service": "..."}
Examples:
- "???? ????? ???? ??????? ?? ????????" -> {"industry": "restaurants", "region": "Saudi Arabia", "service": "digital marketing"}
- "Digital marketing for restaurants in Dubai" -> {"industry": "restaurants", "region": "Dubai", "service": "digital marketing"}
- "E-commerce platform for fashion in Egypt" -> {"industry": "fashion", "region": "Egypt", "service": "e-commerce"}
Always return English values for better search results.
Return ONLY the JSON. No markdown. No explanation."""
        parse_user = (
            f"Business description: {business_description}\n"
            "Return JSON with industry, region, service."
        )
        parsed = self._safe_json(
            await self.llm.complete(system_prompt=parse_system, user_message=parse_user),
            fallback={
                "industry": business_description,
                "region": "global",
                "service": "digital services",
            },
        )

        industry = str(parsed.get("industry", "")).strip()
        region = str(parsed.get("region", "")).strip()
        service = str(parsed.get("service", "")).strip()

        if not industry or not region or not service:
            # fallback: ?????? ????? ?????? ?? search query
            industry = business_description
            region = "global"
            service = "business"

        market = await self.scan_market(industry=industry, region=region, service=service)

        deep_evals = []
        for opp in market.get("opportunities", [])[:3]:
            title = opp.get("title", "")
            ev = await self.evaluate_opportunity(
                opportunity=title,
                context={
                    "industry": industry,
                    "region": region,
                    "service": service,
                    "market_scan": market,
                },
            )
            merged = {**opp, **ev}
            deep_evals.append(merged)

        deep_evals.sort(key=lambda x: float(x.get("confidence", 0.0)), reverse=True)

        return {
            "business_description": business_description,
            "industry": industry,
            "region": region,
            "service": service,
            "opportunities": deep_evals,
            "pain_points": market.get("pain_points", []),
            "competition_level": market.get("competition_level", "medium"),
            "entry_strategy": market.get("entry_strategy", ""),
            "time_to_revenue": market.get("time_to_revenue", ""),
            "search_sources": market.get("search_sources", 0),
            "raw_search_results": market.get("raw_search_results", 0),
        }
