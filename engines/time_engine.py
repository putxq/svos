import json
from core.llm_provider import LLMProvider
from core.json_parser import parse_llm_json, extract_field
from engines.confidence_engine import ConfidenceEngine
from core.response_schemas import validate_response, ScenarioSchema, TimeResult


class TimeEngine:
    """محرك الزمن — يحاكي المستقبل ويتنبأ بالسيناريوهات"""

    def __init__(self):
        self.llm = LLMProvider()

    async def simulate(self, decision: str, context: dict, timeframes: list = None) -> dict:
        """
        يحاكي ماذا يحدث إذا نفذنا قرار معين
        يسأل Claude:
        system_prompt:
        "You are a strategic scenario planner with deep business experience.
        Given a business decision and context, simulate what happens at each timeframe.
        Be realistic and specific - include both opportunities and risks.
        Respond in the same language as the decision.
        Return ONLY JSON, no markdown."

        user_message:
        "Decision: {decision}
        Context: {json.dumps(context)}
        Simulate outcomes for these timeframes: {timeframes}

        Return JSON:
        {
          'decision': str,
          'scenarios': {
            '7_days': {
              'status': str,
              'achievements': [str],
              'challenges': [str],
              'confidence': float 0-1,
              'critical_action': str
            },
            '30_days': { same structure },
            '90_days': { same structure }
          },
          'best_case': str,
          'worst_case': str,
          'most_likely': str,
          'kill_signals': [str],  // signs we should stop
          'acceleration_signals': [str] // signs we should go faster
        }"
        """
        if timeframes is None:
            timeframes = ["7 days", "30 days", "90 days"]

        system_prompt = (
            "You are a strategic scenario planner with deep business experience. "
            "Given a business decision and context, simulate realistic outcomes. "
            "Be specific with numbers and actions. Include both opportunities and risks. "
            "Respond in the same language as the decision. "
            "Return ONLY valid JSON, no markdown fences."
        )

        user_message = (
            f"Decision: {decision}\n"
            f"Context: {json.dumps(context, ensure_ascii=False)}\n\n"
            f"Simulate outcomes for: {', '.join(timeframes)}\n\n"
            "Return JSON with keys: decision, scenarios (with keys like 7_days/30_days/90_days each having "
            "status, achievements list, challenges list, confidence 0-1, critical_action), "
            "best_case, worst_case, most_likely, kill_signals list, acceleration_signals list."
        )

        raw = await self.llm.complete(system_prompt, user_message)
        parsed = parse_llm_json(raw)

        return {
            "decision": extract_field(parsed, "decision", default=decision),
            "scenarios": extract_field(parsed, "scenarios", default={}),
            "best_case": extract_field(parsed, "best_case", default=""),
            "worst_case": extract_field(parsed, "worst_case", default=""),
            "most_likely": extract_field(parsed, "most_likely", default=""),
            "kill_signals": extract_field(parsed, "kill_signals", default=[]),
            "acceleration_signals": extract_field(parsed, "acceleration_signals", default=[]),
        }

    async def should_proceed(self, decision: str, context: dict) -> dict:
        """
        سؤال بسيط: هل نمشي أو نتوقف؟
        يستخدم simulate ثم يحسب:
        - إذا أغلب السيناريوهات إيجابية → proceed
        - إذا أغلبها سلبية → pause
        - إذا فيه kill signals → stop
        """
        sim = await self.simulate(decision, context)

        total_confidence = 0
        count = 0
        for key, scenario in sim.get("scenarios", {}).items():
            if isinstance(scenario, dict):
                total_confidence += ConfidenceEngine.normalize(scenario.get("confidence", 0.5))
                count += 1

        avg_confidence = total_confidence / count if count > 0 else 0.5
        kill_signals = sim.get("kill_signals", [])

        if kill_signals and len(kill_signals) >= 3:
            recommendation = "stop"
        elif avg_confidence >= 0.6:
            recommendation = "proceed"
        elif avg_confidence >= 0.4:
            recommendation = "proceed_with_caution"
        else:
            recommendation = "pause"

        return {
            "recommendation": recommendation,
            "avg_confidence": avg_confidence,
            "kill_signals_count": len(kill_signals),
            "simulation": sim,
        }

