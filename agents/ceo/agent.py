from agents.base_agent import BaseAgent
from agents.ceo.prompts import SYSTEM_PROMPT
from agents.ceo.tools import format_goals, search_market


class CEOAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="ceo",
            role="CEO",
            system_prompt=SYSTEM_PROMPT,
            tools={"search_market": search_market},
        )

    async def decide(self, business_context: str, goals: list[str], task: str) -> str:
        self.remember("last_context", business_context)
        market_hint = await self.use_tools("search_market", query=f"{business_context} {task}")
        prompt = (
            f"سياق النشاط:\n{business_context}\n\n"
            f"الأهداف:\n{format_goals(goals)}\n\n"
            f"المهمة:\n{task}\n\n"
            f"إشارة سوقية:\n{market_hint[:400]}\n\n"
            "قدّم قرار تنفيذي وخطة أسبوعية مختصرة مع نقاط عملية ومؤشرات قياس."
        )
        out = await self.think(prompt)
        self.remember("last_decision", out)
        return out
