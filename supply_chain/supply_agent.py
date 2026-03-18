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

async def analyze_supply_chain(
 business: str,
 products: list[str],
 current_suppliers: list[str]
) -> dict:

 procurement = await _call(
 """أنت خبير مشتريات.
حلّل وضع المشتريات وأعطِ:
- أفضل 3 استراتيجيات للمشتريات
- كيف تقلل التكاليف 15-20%
- مؤشرات قياس الموردين""",
 f"النشاط: {business}\n"
 f"المنتجات: {', '.join(products)}\n"
 f"الموردون: {', '.join(current_suppliers)}"
 )

 inventory = await _call(
 """أنت خبير إدارة مخزون.
أعطِ توصيات عملية:
- مستويات المخزون المثالية
- نقاط إعادة الطلب
- كيف تتجنب النفاد أو الفائض""",
 f"النشاط: {business}\n"
 f"المنتجات: {', '.join(products)}"
 )

 logistics = await _call(
 """أنت خبير لوجستيات.
صمّم خطة توصيل مثالية:
- أسرع طرق التوصيل
- تقليل تكاليف الشحن
- التعامل مع التأخيرات""",
 f"النشاط: {business}\n"
 f"المنتجات: {', '.join(products)}"
 )

 return {
 "business": business,
 "products": products,
 "procurement_strategy": procurement,
 "inventory_management": inventory,
 "logistics_plan": logistics,
 "supply_chain": "Supply Chain Agent ✅"
 }
