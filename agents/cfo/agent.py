from agents.base_agent import BaseAgent
from agents.cfo.prompts import SYSTEM_PROMPT
from agents.cfo.tools import format_goals


class CFOAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_id="cfo", role="CFO", system_prompt=SYSTEM_PROMPT)

    async def decide(self, business_context: str, goals: list[str], task: str) -> str:
        prompt = (
            f"سياق النشاط:\n{business_context}\n\n"
            f"الأهداف:\n{format_goals(goals)}\n\n"
            f"المهمة:\n{task}\n\n"
            "قدّم قرارًا ماليًا: التدفق النقدي، التسعير، ضبط التكاليف، ومؤشرات قياس أسبوعية."
        )
        out = await self.think(prompt)
        self.remember("last_decision", out)
        return out
