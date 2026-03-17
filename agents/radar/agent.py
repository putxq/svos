from anthropic import AsyncAnthropic

from core.config import settings
from agents.radar.prompts import SYSTEM_PROMPT
from agents.radar.tools import format_goals


class RadarAgent:
    def __init__(self):
        if not settings.anthropic_api_key:
            raise RuntimeError('ANTHROPIC_API_KEY is not configured')
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def decide(self, business_context: str, goals: list[str], task: str) -> str:
        prompt = (
            f"سياق النشاط:\n{business_context}\n\n"
            f"الأهداف:\n{format_goals(goals)}\n\n"
            f"المهمة:\n{task}\n\n"
            "قدّم رصدًا للسوق: منافسين، فرص، مخاطر، وخطوات الأسبوع القادم."
        )

        msg = await self.client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=700,
            temperature=0.25,
            system=SYSTEM_PROMPT,
            messages=[{'role': 'user', 'content': prompt}],
        )

        parts: list[str] = []
        for block in msg.content:
            text = getattr(block, 'text', None)
            if text:
                parts.append(text)
        return "\n".join(parts).strip()
