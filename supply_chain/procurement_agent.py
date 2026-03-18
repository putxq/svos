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

async def run_procurement(
 business: str,
 needed_items: list[str],
 budget: str
) -> dict:

 suppliers = await _call(
 """أنت خبير مشتريات.
حدد أفضل استراتيجية توريد:
- مصادر التوريد الموصى بها
- معايير اختيار المورد
- شروط التفاوض المثالية""",
 f"النشاط: {business}\n"
 f"المشتريات: {', '.join(needed_items)}\n"
 f"الميزانية: {budget}"
 )

 cost_plan = await _call(
 """أنت محلل تكاليف.
ضع خطة تكلفة مفصلة:
- تكلفة كل بند
- فرص التوفير
- البدائل الأرخص""",
 f"المشتريات: {', '.join(needed_items)}\n"
 f"الميزانية: {budget}"
 )

 return {
 "business": business,
 "items": needed_items,
 "budget": budget,
 "supplier_strategy": suppliers,
 "cost_plan": cost_plan,
 "agent": "Procurement Agent ✅"
 }
