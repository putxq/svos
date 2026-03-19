"""
Gravity Engine
اكتشاف الطلب → تأهيل الفرصة → تحويل لـ lead → تحويل لإيراد
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


async def run_gravity_engine(market_signal: str, segment: str, offer: str) -> dict:
    demand = await _call(
        "أنت خبير اكتشاف طلب. استخرج أين الطلب الحقيقي الآن.",
        f"الإشارة: {market_signal}\nالقطاع: {segment}",
    )
    qualification = await _call(
        "أنت خبير تأهيل فرص. صنّف الفرصة (high/medium/low) مع السبب.",
        f"الإشارة: {market_signal}\nالعرض: {offer}",
    )
    lead_strategy = await _call(
        "أنت خبير تحويل. أعطِ خطة تحويل إلى lead ثم revenue خلال 30 يوم.",
        f"القطاع: {segment}\nالعرض: {offer}",
    )
    return {
        "engine": "Gravity Engine ✅",
        "demand_discovery": demand,
        "opportunity_qualification": qualification,
        "lead_to_revenue_plan": lead_strategy,
    }
