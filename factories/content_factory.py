"""
Content Factory — مصنع المحتوى الرقمي
ينتج محتوى بكميات كبيرة لمنصات متعددة
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
 model=MODEL, max_tokens=500,
 system=system,
 messages=[{"role":"user","content":user}]
 )
 return msg.content[0].text.strip()

async def produce_content_batch(
 topic: str,
 business: str,
 platforms: list[str]
) -> dict:

 async def make_post(platform: str) -> dict:
  style = {
  "linkedin": "احترافي وتحليلي، 150-200 كلمة",
  "twitter": "مختصر وجذاب، أقل من 280 حرف",
  "instagram": "بصري وعاطفي مع hashtags",
  "blog": "تفصيلي وشامل، 300-400 كلمة",
  "email": "شخصي ومقنع مع CTA واضح"
  }.get(platform, "احترافي ومناسب")

  content = await _call(
  f"""أنت كاتب محتوى متخصص في {platform}.
الأسلوب: {style}
قواعد إلزامية:
- محتوى حقيقي وقيّم
- لا حشو ولا تكرار
- ينتهي بدعوة للعمل""",
  f"الموضوع: {topic}\nالنشاط: {business}"
  )
  return {"platform": platform, "content": content}

 results = []
 for p in platforms:
  r = await make_post(p)
  results.append(r)

 return {
 "topic": topic,
 "business": business,
 "produced": len(results),
 "content_batch": results,
 "factory": "Content Factory ✅"
 }
