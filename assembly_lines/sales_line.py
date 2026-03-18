"""
Sales Assembly Line
خط المبيعات الكامل — من Lead إلى Close
"""
from anthropic import AsyncAnthropic

from core.config import settings

client = AsyncAnthropic(api_key=settings.anthropic_api_key)
MODEL = "claude-haiku-4-5-20251001"


async def _call(system: str, user: str) -> str:
    msg = await client.messages.create(
        model=MODEL,
        max_tokens=600,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text.strip()


async def run_sales_line(lead_name: str, business_type: str, pain_points: list[str]) -> dict:
    pains = "\n".join(pain_points)

    # ١ — Research Agent
    research = await _call(
        "أنت باحث مبيعات. حلّل هذا العميل المحتمل.",
        f"العميل: {lead_name}\nنشاطه: {business_type}\nمشاكله: {pains}",
    )

    # ٢ — Qualification Agent
    qualify = await _call(
        """أنت خبير تأهيل عملاء.
قيّم هذا العميل وأجب بـ JSON:
{
 "qualified": true/false,
 "score": 0-100,
 "reason": "السبب",
 "priority": "high/medium/low"
}""",
        f"البحث: {research}\nالمشاكل: {pains}",
    )

    # ٣ — Pitch Agent
    pitch = await _call(
        "أنت خبير مبيعات. اكتب عرضاً مخصصاً قصيراً وجذاباً.",
        f"العميل: {lead_name}\nالبحث: {research[:300]}\nالمشاكل: {pains}",
    )

    # ٤ — Objection Handler
    objections = await _call(
        "أنت خبير التعامل مع الاعتراضات. أعطِ 3 اعتراضات متوقعة مع ردود احترافية.",
        f"العميل: {lead_name}\nالعرض: {pitch[:300]}",
    )

    # ٥ — Close Agent
    close = await _call(
        "أنت متخصص إغلاق الصفقات. أعطِ خطة إغلاق واضحة مع خطوات follow-up.",
        f"العميل: {lead_name}\nالعرض: {pitch[:200]}\nالاعتراضات: {objections[:200]}",
    )

    return {
        "lead": lead_name,
        "business_type": business_type,
        "research": research,
        "qualification": qualify,
        "pitch": pitch,
        "objection_handling": objections,
        "closing_plan": close,
        "pipeline": [
            "Research ✅",
            "Qualification ✅",
            "Pitch ✅",
            "Objections ✅",
            "Close ✅",
        ],
    }
