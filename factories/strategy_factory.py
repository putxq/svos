"""
Strategy Factory — مصنع الاستراتيجية
ينتج استراتيجيات جاهزة للتنفيذ
"""
from anthropic import AsyncAnthropic
from core.config import settings
import asyncio

client = AsyncAnthropic(
 api_key=settings.anthropic_api_key
)
MODEL = "claude-haiku-4-5-20251001"

async def _call(system: str, user: str) -> str:
 msg = await client.messages.create(
 model=MODEL, max_tokens=600,
 system=system,
 messages=[{"role":"user","content":user}]
 )
 return msg.content[0].text.strip()

async def build_strategy(
 business: str,
 goals: list[str],
 timeframe: str = "90 يوم"
) -> dict:

 market = await _call(
 """أنت محلل سوق استراتيجي.
حلّل الوضع التنافسي وأعطِ:
- الفرص الرئيسية 3
- التهديدات الرئيسية 3
- نقاط القوة للاستثمار فيها""",
 f"النشاط: {business}\nالأهداف: {', '.join(goals)}"
 )

 roadmap = await _call(
 f"""أنت خبير تخطيط استراتيجي.
ابنِ خارطة طريق لـ {timeframe}:
- الشهر الأول: إجراءات فورية
- الشهر الثاني: بناء وتطوير
- الشهر الثالث: توسع وقياس
كل مرحلة مع مسؤول ومؤشر نجاح""",
 f"النشاط: {business}\nالأهداف: {', '.join(goals)}"
 )

 budget = await _call(
 """أنت مخطط مالي استراتيجي.
وزّع الميزانية المثالية:
- التسويق والمبيعات: %
- التقنية والأدوات: %
- العمليات: %
- الاحتياطي: %
مع تبرير كل قرار.""",
 f"النشاط: {business}\nالأهداف: {', '.join(goals)}"
 )

 return {
 "business": business,
 "goals": goals,
 "timeframe": timeframe,
 "market_analysis": market,
 "roadmap": roadmap,
 "budget_allocation": budget,
 "factory": "Strategy Factory ✅"
 }
