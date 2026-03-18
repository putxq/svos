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

async def run_inventory(
 business: str,
 products: list[str],
 current_stock: str
) -> dict:

 optimization = await _call(
 """أنت خبير إدارة مخزون.
حسّن مستويات المخزون:
- الحد الأدنى لكل منتج
- نقطة إعادة الطلب
- الكمية المثالية للطلب
- تكلفة الاحتفاظ بالمخزون""",
 f"النشاط: {business}\n"
 f"المنتجات: {', '.join(products)}\n"
 f"المخزون الحالي: {current_stock}"
 )

 forecast = await _call(
 """أنت محلل طلب.
توقع الطلب للشهر القادم:
- المنتجات الأكثر طلباً
- المواسم والذروات
- توصية الطلب المسبق""",
 f"المنتجات: {', '.join(products)}\n"
 f"المخزون: {current_stock}"
 )

 return {
 "business": business,
 "products": products,
 "current_stock": current_stock,
 "inventory_optimization": optimization,
 "demand_forecast": forecast,
 "agent": "Inventory Agent ✅"
 }
