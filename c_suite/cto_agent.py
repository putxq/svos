from anthropic import AsyncAnthropic
from core.config import settings

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

async def cto_decide(
 business_context: str,
 current_tech: str,
 tech_goals: list[str]
) -> dict:

 tech_strategy = await _call(
 """أنت CTO استراتيجي.
ضع استراتيجية تقنية واضحة:
- الأدوات المطلوبة
- الأولويات التقنية
- المخاطر وكيفية تجنبها""",
 f"النشاط: {business_context}\n"
 f"التقنية الحالية: {current_tech}\n"
 f"الأهداف: {', '.join(tech_goals)}"
 )

 ai_roadmap = await _call(
 """أنت خبير تحول رقمي بالذكاء الاصطناعي.
أعطِ خارطة طريق AI لهذا النشاط:
- ما يمكن أتمتته فوراً
- ما يحتاج 30 يوم
- ما يحتاج 90 يوم
مع تكلفة تقريبية لكل مرحلة.""",
 f"النشاط: {business_context}\n"
 f"الأهداف: {', '.join(tech_goals)}"
 )

 security = await _call(
 """أنت خبير أمن معلومات.
حدد أهم 3 مخاطر أمنية لهذا النشاط
مع خطوة واحدة فورية لكل مخاطرة.""",
 f"النشاط: {business_context}\n"
 f"التقنية: {current_tech}"
 )

 return {
 "role": "CTO",
 "tech_strategy": tech_strategy,
 "ai_roadmap": ai_roadmap,
 "security_assessment": security,
 "status": "active"
 }
