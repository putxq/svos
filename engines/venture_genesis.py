"""
Venture Genesis
وصف نشاط واحد → شركة رقمية كاملة جاهزة
"""
from anthropic import AsyncAnthropic

from core.config import settings

client = AsyncAnthropic(api_key=settings.anthropic_api_key)
MODEL = "claude-haiku-4-5-20251001"


async def _call(system: str, user: str) -> str:
    msg = await client.messages.create(
        model=MODEL,
        max_tokens=900,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text.strip()


async def run_venture_genesis(activity_description: str) -> dict:
    blueprint = await _call(
        "حوّل الوصف إلى شركة رقمية كاملة: منتج، نموذج دخل، قنوات، عمليات، فريق وكلاء.",
        activity_description,
    )
    operating_model = await _call(
        "اعط نموذج تشغيل يومي/أسبوعي مع KPIs واضحة.",
        activity_description,
    )
    first_30_days = await _call(
        "ابنِ خطة تنفيذ لأول 30 يوم خطوة بخطوة.",
        activity_description,
    )
    return {
        "engine": "Venture Genesis ✅",
        "blueprint": blueprint,
        "operating_model": operating_model,
        "first_30_days": first_30_days,
    }
