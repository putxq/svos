from agents.base_agent import BaseAgent
from agents.guardian.prompts import SYSTEM_PROMPT
from agents.guardian.tools import compact


class GuardianAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_id="guardian", role="Guardian", system_prompt=SYSTEM_PROMPT)

    async def review(self, ceo_decision: str, cfo_decision: str, radar_decision: str) -> str:
        prompt = (
            "راجع المخرجات التالية واكتب ملاحظات حوكمة وجودة مختصرة:\n\n"
            f"[CEO]\n{compact(ceo_decision)}\n\n"
            f"[CFO]\n{compact(cfo_decision)}\n\n"
            f"[Radar]\n{compact(radar_decision)}"
        )
        out = await self.think(prompt, max_tokens=500)
        self.remember("last_review", out)
        return out
