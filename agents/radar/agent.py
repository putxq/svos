from agents.base_agent import BaseAgent
from agents.radar.prompts import SYSTEM_PROMPT
from agents.radar.tools import format_goals


class RadarAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_id="radar", role="Radar", system_prompt=SYSTEM_PROMPT)

    async def decide(self, business_context: str, goals: list[str], task: str) -> str:
        prompt = (
            f"سياق النشاط:\n{business_context}\n\n"
            f"الأهداف:\n{format_goals(goals)}\n\n"
            f"المهمة:\n{task}\n\n"
            "قدّم رصدًا للسوق: منافسين، فرص، مخاطر، وخطوات الأسبوع القادم."
        )
        out = await self.think(prompt)
        self.remember("last_decision", out)
        return out
