"""
Evolution Engine
تحسين مستمر — البرومبتات + العروض + أداء الوكلاء
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


async def run_evolution_engine(current_prompt: str, current_offer: str, performance_snapshot: str) -> dict:
    optimized_prompt = await _call(
        "حسّن البرومبت لرفع الجودة وتقليل الهلوسة.",
        f"البرومبت الحالي:\n{current_prompt}",
    )
    optimized_offer = await _call(
        "حسّن العرض التجاري لرفع التحويل.",
        f"العرض الحالي:\n{current_offer}",
    )
    agent_tuning = await _call(
        "حلل أداء الوكلاء وقدّم توصيات تحسين دقيقة.",
        f"لقطة الأداء:\n{performance_snapshot}",
    )
    return {
        "engine": "Evolution Engine ✅",
        "optimized_prompt": optimized_prompt,
        "optimized_offer": optimized_offer,
        "agent_tuning": agent_tuning,
    }
