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

    @staticmethod
    def _extract_confidence(obj: dict, scale_hint: str = "auto") -> float:
        """
        يستخرج قيمة الثقة من أي مفتاح ممكن Claude يستخدمه.
        يدعم: confidence, confidence_score, score, confidence_level
        يتعامل مع: أرقام 0-1، أرقام 0-100، نصوص مثل "78%"، نصوص مثل "high"
        """
        CONFIDENCE_KEYS = [
            "confidence",
            "confidence_score",
            "score",
            "confidence_level",
            "confidence_rating",
            "certainty",
        ]

        raw = None
        for key in CONFIDENCE_KEYS:
            val = obj.get(key)
            if val is not None and val != "" and val != 0:
                raw = val
                break

        if raw is None:
            raw = obj.get("confidence", 0)

        # Handle string values
        if isinstance(raw, str):
            raw = raw.strip().lower()

            # Handle percentage strings like "78%"
            pct_match = re.match(r"(\d+(?:\.\d+)?)\s*%", raw)
            if pct_match:
                return min(1.0, float(pct_match.group(1)) / 100.0)

            # Handle word-based confidence
            word_map = {
                "very high": 0.92,
                "high": 0.82,
                "medium-high": 0.72,
                "medium": 0.55,
                "moderate": 0.55,
                "medium-low": 0.38,
                "low": 0.25,
                "very low": 0.12,
                "none": 0.05,
            }
            if raw in word_map:
                return word_map[raw]

            # Try to parse as number
            try:
                raw = float(raw)
            except ValueError:
                return 0.5  # safe default for unparseable

        try:
            conf = float(raw)
        except (TypeError, ValueError):
            return 0.5

        # Normalize: if > 1, assume 0-100 scale
        if conf > 1.0:
            conf = conf / 100.0

        return max(0.0, min(1.0, conf))

    async def scan_market(self, industry: str, region: str, service: str) -> dict:
        """يمسح السوق ويكتشف الفرص الحقيقية."""
        queries = [
            f"{industry} {region} market demand 2025 2026",
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
        if total_results == 0:
            fallback_result = await self.search.execute(
                f"{industry} market opportunity", max_results=5
            )
            for item in fallback_result.get("results", []):
                item = dict(item)
                item["query"] = f"{industry} market opportunity"
                gathered.append(item)

        compact = []
        for i, r in enumerate(gathered[:18], 1):
            compact.append({
                "n": i,
                "query": r.get("query", ""),
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("snippet", ""),
            })

        system_prompt = (
            "You are a market intelligence analyst. "
            "Based on these search results, identify:\n"
            "1. Top 3 real opportunities\n"
            "2. Top 3 pain points customers have\n"
            "3. Competition level (low/medium/high)\n"
            "4. Recommended entry strategy\n"
            "5. Estimated time to first revenue\n\n"
            "IMPORTANT: Return ONLY valid JSON. No markdown.\n"
            "Each opportunity MUST have a 'confidence' field as a number from 0 to 100.\n"
            "Use this exact structure:\n"
            '{"opportunities": [{"title": "...", "description": "...", "confidence": 78, "evidence": "..."}], '
            '"pain_points": ["..."], "competition_level": "medium", '
            '"entry_strategy": "...", "time_to_revenue": "..."}\n'
            "Respond in the same language as the industry/region description."
        )

        user_prompt = (
            f"Industry: {industry}\n"
            f"Region: {region}\n"
            f"Service: {service}\n"
            f"Search results ({len(compact)} items): {json.dumps(compact, ensure_ascii=False)}\n\n"
            "Return JSON with keys: opportunities, pain_points, competition_level, "
            "entry_strategy, time_to_revenue."
        )

        raw = await self.llm.complete(system_prompt=system_prompt, user_message=user_prompt)
        parsed = parse_llm_json(raw)

        opportunities = extract_field(
            parsed,
            "opportunities",
            "analysis.opportunities",
            "market_opportunities",
            "top_opportunities",
            default=[],
        )

        clean_opportunities = []
        for opp in opportunities:
            if not isinstance(opp, dict):
                continue

            conf = self._extract_confidence(opp)

            clean_opportunities.append({
                "title": opp.get("title") or opp.get("opportunity") or opp.get("name", "Unknown"),
                "description": opp.get("description") or opp.get("rationale") or opp.get("details", ""),
                "confidence_scan": conf,
                "confidence": conf,
                "evidence": opp.get("evidence") or opp.get("rationale") or opp.get("reasoning", ""),
            })

        competition = extract_field(
            parsed,
            "competition_level",
            "analysis.competition_level",
            "competition.level",
            "competition",
            default="unknown",
        )
        entry_strategy = extract_field(
            parsed,
            "entry_strategy",
            "recommended_entry_strategy",
            "analysis.entry_strategy",
            "strategy",
            default="",
        )
        time_to_revenue = extract_field(
            parsed,
            "time_to_revenue",
            "time_to_first_revenue",
            "analysis.time_to_revenue",
            "revenue_timeline",
            default="",
        )
        pain_points = extract_field(
            parsed,
            "pain_points",
            "analysis.pain_points",
            "customer_pain_points",
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
        """يقيّم فرصة واحدة بعمق."""
        system = (
            "Evaluate this business opportunity strictly.\n"
            "Return ONLY valid JSON with these exact keys:\n"
            '{"is_real": true, "confidence": 78, "evidence_for": ["..."], '
            '"evidence_against": ["..."], "recommended_action": "...", '
            '"risk_level": "low", "potential_revenue": "..."}\n'
            "IMPORTANT: confidence must be a NUMBER from 0 to 100. Not a string. Not a decimal.\n"
            "No markdown. No explanation. JSON only."
        )

        user = (
            f"Evaluate this business opportunity: {opportunity}\n"
            f"Context: {json.dumps(context, ensure_ascii=False, default=str)}\n"
            "Return JSON with: is_real (bool), confidence (number 0-100), "
            "evidence_for (list), evidence_against (list), "
            "recommended_action (string), risk_level (low/medium/high), "
            "potential_revenue (string estimate)"
        )

        raw = await self.llm.complete(system_prompt=system, user_message=user)
        parsed = self._safe_json(
            raw,
            fallback={
                "is_real": False,
                "confidence": 40,
                "evidence_for": [],
                "evidence_against": ["insufficient structured evidence"],
                "recommended_action": "collect more market evidence",
                "risk_level": "medium",
                "potential_revenue": "unknown",
            },
        )

        conf = self._extract_confidence(parsed)

        return {
            "is_real": bool(parsed.get("is_real", False)),
            "confidence_eval": conf,
            "evidence_for": [str(x) for x in (parsed.get("evidence_for") or [])],
            "evidence_against": [str(x) for x in (parsed.get("evidence_against") or [])],
            "recommended_action": str(parsed.get("recommended_action", "")),
            "risk_level": str(parsed.get("risk_level", "medium")),
            "potential_revenue": str(parsed.get("potential_revenue", "unknown")),
        }

    async def find_demand_gravity(self, business_description: str) -> dict:
        """الدالة الرئيسية — تستقبل وصف نشاط وترجع خريطة الطلب."""
        parse_system = (
            "Extract business parameters from this description.\n"
            "Return ONLY a JSON object with these exact keys:\n"
            '{"industry": "...", "region": "...", "service": "..."}\n'
            "Always return English values for better search results.\n"
            "No markdown. No explanation. JSON only."
        )

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
                    "market_scan": {
                        "pain_points": market.get("pain_points", []),
                        "competition_level": market.get("competition_level", ""),
                    },
                },
            )

            # Smart merge: keep both scores + calculate weighted final
            scan_conf = float(opp.get("confidence_scan", 0.5))
            eval_conf = float(ev.get("confidence_eval", 0.5))

            # Scan has broader context (market data), eval has deeper analysis
            # Weighted: 40% scan + 60% eval
            final_conf = (scan_conf * 0.4) + (eval_conf * 0.6)

            merged = {**opp, **ev}
            merged["confidence_scan"] = round(scan_conf, 3)
            merged["confidence_eval"] = round(eval_conf, 3)
            merged["confidence"] = round(final_conf, 3)
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
