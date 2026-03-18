from datetime import datetime

from anthropic import AsyncAnthropic

from core.config import settings
from agents.guardian.prompts import SYSTEM_PROMPT
from agents.guardian.tools import compact


class GuardianAgent:
    def __init__(self):
        if not settings.anthropic_api_key:
            raise RuntimeError('ANTHROPIC_API_KEY is not configured')
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.memory = []  # قصيرة المدى

    def remember(self, key, value):
        self.memory.append(
            {
                "key": key,
                "value": value,
                "ts": datetime.utcnow().isoformat(),
            }
        )

    def recall(self, key):
        for m in reversed(self.memory):
            if m["key"] == key:
                return m["value"]
        return None

    async def review(self, ceo_decision: str, cfo_decision: str, radar_decision: str) -> str:
        prompt = (
            "راجع المخرجات التالية واكتب ملاحظات حوكمة وجودة مختصرة:\n\n"
            f"[CEO]\n{compact(ceo_decision)}\n\n"
            f"[CFO]\n{compact(cfo_decision)}\n\n"
            f"[Radar]\n{compact(radar_decision)}"
        )

        msg = await self.client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=500,
            temperature=0.1,
            system=SYSTEM_PROMPT,
            messages=[{'role': 'user', 'content': prompt}],
        )

        parts: list[str] = []
        for block in msg.content:
            text = getattr(block, 'text', None)
            if text:
                parts.append(text)
        return "\n".join(parts).strip()
