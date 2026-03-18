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

async def coo_decide(
 business_context: str,
 current_operations: str,
 bottlenecks: list[str]
) -> dict:

 ops_plan = await _call(
 """أنت COO خبير في العمليات.
قواعد إلزامية:
- خطوات تنفيذية فورية فقط
- أرقام وأهداف قابلة للقياس
- لا كلام نظري""",
 f"النشاط: {business_context}\n"
 f"العمليات الحالية: {current_operations}\n"
 f"الاختناقات: {', '.join(bottlenecks)}"
 )

 efficiency = await _call(
 """أنت خبير كفاءة تشغيلية.
حدد 3 إجراءات فورية لرفع الكفاءة
مع نسبة التحسين المتوقعة لكل إجراء.""",
 f"العمليات: {current_operations}\n"
 f"الاختناقات: {', '.join(bottlenecks)}"
 )

 kpis = await _call(
 """أنت محلل KPIs.
أعطِ 5 مؤشرات أداء رئيسية مع:
- القيمة الحالية المتوقعة
- الهدف خلال 30 يوم
- طريقة القياس""",
 f"النشاط: {business_context}\n"
 f"الخطة: {ops_plan[:300]}"
 )

 return {
 "role": "COO",
 "operations_plan": ops_plan,
 "efficiency_actions": efficiency,
 "kpis": kpis,
 "status": "active"
 }
