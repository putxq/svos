import json
import re

from core.llm_provider import LLMProvider


def parse_llm_json(text):
    text = text.strip()
    text = re.sub(r'^```json\s*', '', text)
    text = re.sub(r'^```\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        try:
            return json.loads(text[start:end+1])
        except:
            pass
    return {}


class TimeEngine:
    """محرك الزمن — يحاكي المستقبل ويتنبأ بالسيناريوهات"""

    def __init__(self):
        self.llm = LLMProvider()

    async def simulate(self, decision: str, context: dict, timeframes: list = None) -> dict:
        """
        يحاكي ماذا يحدث إذا نفذنا قرار معين.
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
            "decision": parsed.get("decision", decision),
            "scenarios": parsed.get("scenarios", {}),
            "best_case": parsed.get("best_case", ""),
            "worst_case": parsed.get("worst_case", ""),
            "most_likely": parsed.get("most_likely", ""),
            "kill_signals": parsed.get("kill_signals", []),
            "acceleration_signals": parsed.get("acceleration_signals", []),
        }

    async def should_proceed(self, decision: str, context: dict) -> dict:
        """
        سؤال بسيط: هل نمشي أو نتوقف؟
        """
        sim = await self.simulate(decision, context)

        total_confidence = 0
        count = 0
        for key, scenario in sim.get("scenarios", {}).items():
            if isinstance(scenario, dict):
                total_confidence += scenario.get("confidence", 0.5)
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
