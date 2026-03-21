import json
import logging
from datetime import datetime
from pathlib import Path

from core.json_parser import parse_llm_json
from core.llm_provider import LLMProvider

logger = logging.getLogger("svos.revenue")


class RevenueEngine:
    """محرك الإيرادات — يكتشف فرص الدخل ويفعّلها."""

    def __init__(self, data_dir: str = "workspace/revenue"):
        self.data_dir = Path(data_dir).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.llm = LLMProvider()
        self.streams: list[dict] = []
        self._load()

    def _file(self) -> Path:
        return self.data_dir / "revenue_data.json"

    def _load(self):
        f = self._file()
        if f.exists():
            try:
                self.streams = json.loads(f.read_text("utf-8")).get("streams", [])
            except Exception:
                self.streams = []

    def _save(self):
        self._file().write_text(
            json.dumps(
                {"streams": self.streams, "updated": datetime.utcnow().isoformat()},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    async def discover_streams(self, business: str, current_revenue: str = "", goals: list[str] | None = None) -> dict:
        goals = goals or ["increase revenue"]
        system = (
            "You are a revenue strategist. Analyze this business and discover ALL possible revenue streams. "
            "Think beyond obvious ones. Include: direct sales, subscriptions, licensing, partnerships, "
            "white-label, affiliate, data monetization, premium tiers, add-ons, consulting, training. "
            "Return ONLY valid JSON."
        )
        user = (
            f"Business: {business}\n"
            f"Current revenue: {current_revenue}\n"
            f"Goals: {json.dumps(goals)}\n\n"
            "Return JSON:\n"
            '{"streams": [{"name": str, "type": str, "description": str, '
            '"revenue_potential": str, "effort_to_launch": str, "time_to_first_revenue": str, '
            '"confidence": int, "action_steps": [str]}], '
            '"total_potential": str, "recommended_priority": [str]}'
        )
        raw = await self.llm.complete(system, user, max_tokens=3000)
        parsed = parse_llm_json(raw)

        streams = parsed.get("streams", [])
        for s in streams:
            s["discovered_at"] = datetime.utcnow().isoformat()
            s["status"] = "discovered"
            s["business"] = business

        self.streams.extend(streams)
        self._save()
        logger.info(f"Revenue: discovered {len(streams)} streams for {business}")

        return {
            "business": business,
            "streams": streams,
            "total_potential": parsed.get("total_potential", ""),
            "recommended_priority": parsed.get("recommended_priority", []),
        }

    async def evaluate_stream(self, stream_name: str, business_context: str) -> dict:
        system = "You are a revenue analyst. Evaluate this revenue stream deeply. Return ONLY valid JSON."
        user = (
            f"Revenue stream: {stream_name}\n"
            f"Business: {business_context}\n\n"
            "Return JSON:\n"
            '{"viability_score": int, "market_size": str, "competitors": [str], '
            '"pricing_strategy": str, "customer_acquisition_cost": str, '
            '"lifetime_value": str, "break_even": str, "risks": [str], '
            '"quick_wins": [str], "long_term_plays": [str]}'
        )
        raw = await self.llm.complete(system, user, max_tokens=2000)
        return {"stream": stream_name, "evaluation": parse_llm_json(raw)}

    async def generate_pricing(self, product: str, target_market: str, competitors: str = "") -> dict:
        system = "You are a pricing strategist. Create a complete pricing strategy. Return ONLY valid JSON."
        user = (
            f"Product: {product}\n"
            f"Target market: {target_market}\n"
            f"Competitors: {competitors}\n\n"
            "Return JSON:\n"
            '{"pricing_model": str, "tiers": [{"name": str, "price": str, '
            '"features": [str], "target": str}], "free_tier": bool, '
            '"annual_discount": str, "enterprise_custom": bool, '
            '"psychological_tactics": [str], "launch_offer": str}'
        )
        raw = await self.llm.complete(system, user, max_tokens=2000)
        return {"product": product, "pricing": parse_llm_json(raw)}

    async def forecast(self, business: str, streams: list[str], months: int = 12) -> dict:
        system = (
            "You are a financial forecaster. Create a realistic revenue forecast. "
            "Be conservative with early months and show growth curve. Return ONLY valid JSON."
        )
        user = (
            f"Business: {business}\n"
            f"Revenue streams: {json.dumps(streams)}\n"
            f"Forecast: {months} months\n\n"
            "Return JSON:\n"
            '{"monthly_forecast": [{"month": int, "revenue": str, "streams_breakdown": {}}], '
            '"total_year": str, "growth_rate": str, "assumptions": [str], '
            '"best_case": str, "worst_case": str}'
        )
        raw = await self.llm.complete(system, user, max_tokens=3000)
        return {"business": business, "forecast": parse_llm_json(raw)}

    def get_all_streams(self) -> list[dict]:
        return self.streams

    def get_summary(self) -> dict:
        by_status: dict[str, int] = {}
        for s in self.streams:
            st = s.get("status", "discovered")
            by_status[st] = by_status.get(st, 0) + 1
        return {"total_streams": len(self.streams), "by_status": by_status}
