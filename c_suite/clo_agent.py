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

async def clo_decide(
 business_context: str,
 country: str,
 business_type: str
) -> dict:

 compliance = await _call(
 """أنت مستشار قانوني ومتخصص امتثال.
قدّم تقييم امتثال شامل:
- المتطلبات القانونية الأساسية
- المخاطر القانونية المحتملة
- الإجراءات الفورية للامتثال""",
 f"النشاط: {business_context}\n"
 f"الدولة: {country}\n"
 f"نوع النشاط: {business_type}"
 )

 contracts = await _call(
 """أنت خبير عقود تجارية.
حدد أهم 3 عقود يحتاجها هذا النشاط
مع البنود الجوهرية لكل عقد.""",
 f"النشاط: {business_context}\n"
 f"النوع: {business_type}"
 )

 risks = await _call(
 """أنت محلل مخاطر قانونية.
حدد أكبر 3 مخاطر قانونية
مع استراتيجية تخفيف لكل خطر.""",
 f"النشاط: {business_context}\n"
 f"الدولة: {country}"
 )

 return {
 "role": "CLO",
 "compliance_assessment": compliance,
 "key_contracts": contracts,
 "legal_risks": risks,
 "status": "active"
 }
