from anthropic import AsyncAnthropic
from core.config import settings

client = AsyncAnthropic(
 api_key=settings.anthropic_api_key
)
MODEL = "claude-haiku-4-5-20251001"

async def _call(system: str, user: str) -> str:
 msg = await client.messages.create(
 model=MODEL, max_tokens=500,
 system=system,
 messages=[{"role":"user","content":user}]
 )
 return msg.content[0].text.strip()

async def run_logistics(
 business: str,
 origin: str,
 destination: str,
 cargo_type: str
) -> dict:

 route = await _call(
 """أنت خبير لوجستيات.
صمّم خطة شحن مثالية:
- أفضل مسار
- وسيلة النقل الموصى بها
- الوقت المتوقع
- التكلفة التقريبية""",
 f"النشاط: {business}\n"
 f"من: {origin} إلى: {destination}\n"
 f"البضاعة: {cargo_type}"
 )

 risks = await _call(
 """أنت محلل مخاطر لوجستية.
حدد المخاطر المحتملة وحلولها:
- مخاطر التأخير
- مخاطر التلف
- مخاطر التكلفة
مع خطة طوارئ لكل خطر.""",
 f"المسار: {origin} إلى {destination}\n"
 f"البضاعة: {cargo_type}"
 )

 return {
 "business": business,
 "route": f"{origin} → {destination}",
 "cargo": cargo_type,
 "logistics_plan": route,
 "risk_mitigation": risks,
 "agent": "Logistics Agent ✅"
 }
