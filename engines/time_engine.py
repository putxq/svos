"""
Time Engine
محاكاة سيناريوهات 7/30/90 يوم
"""
from anthropic import AsyncAnthropic

from core.config import settings

client = AsyncAnthropic(api_key=settings.anthropic_api_key)
MODEL = "claude-haiku-4-5-20251001"


async def _call(system: str, user: str) -> str:
    msg = await client.messages.create(
        model=MODEL,
        max_tokens=700,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text.strip()


async def run_time_engine(strategy: str, constraints: list[str]) -> dict:
    base = f"الاستراتيجية: {strategy}\nالقيود: {', '.join(constraints)}"
    d7 = await _call("حلل سيناريو 7 أيام: ماذا يحدث إذا بدأنا الآن؟", base)
    d30 = await _call("حلل سيناريو 30 يوم: ماذا يحدث عند التنفيذ المنضبط؟", base)
    d90 = await _call("حلل سيناريو 90 يوم: ماذا يحدث عند الاستمرار أو التأخر؟", base)
    return {
        "engine": "Time Engine ✅",
        "day_7": d7,
        "day_30": d30,
        "day_90": d90,
    }
