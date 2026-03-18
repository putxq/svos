"""
Content Assembly Line
خط إنتاج المحتوى الكامل
Research → Write → SEO → Publish → Analyze
"""
from anthropic import AsyncAnthropic

from core.config import settings

client = AsyncAnthropic(api_key=settings.anthropic_api_key)
MODEL = "claude-haiku-4-5-20251001"


async def _call(system: str, user: str) -> str:
    msg = await client.messages.create(
        model=MODEL,
        max_tokens=500,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text.strip()


async def run_content_line(topic: str, business: str, audience: str) -> dict:
    # ١ — Research Agent
    research = await _call(
        "أنت باحث متخصص. أعطِ أهم 3 نقاط عن الموضوع.",
        f"الموضوع: {topic}\nالنشاط: {business}",
    )

    # ٢ — Content Agent
    content = await _call(
        "أنت كاتب محتوى محترف. اكتب محتوى قصيراً جذاباً.",
        f"النقاط: {research}\nالجمهور: {audience}",
    )

    # ٣ — SEO Agent
    seo = await _call(
        "أنت خبير SEO. أعطِ 5 كلمات مفتاحية + عنوان محسّن.",
        f"المحتوى: {content[:200]}\nالموضوع: {topic}",
    )

    # ٤ — Quality Agent
    quality = await _call(
        "أنت مدقق جودة. قيّم هذا المحتوى من 10 وأعطِ ملاحظة.",
        f"المحتوى: {content[:300]}",
    )

    return {
        "topic": topic,
        "research": research,
        "content": content,
        "seo": seo,
        "quality_review": quality,
        "pipeline": [
            "Research ✅",
            "Content ✅",
            "SEO ✅",
            "Quality ✅",
        ],
    }
