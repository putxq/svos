"""
Data Factory — مصنع تحليل البيانات
يحوّل أي بيانات خام إلى رؤى قابلة للعمل
"""
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

async def analyze_business_data(
 business: str,
 data_description: str,
 analysis_goal: str
) -> dict:

 insights = await _call(
 """أنت محلل بيانات أعمال خبير.
استخرج رؤى قابلة للعمل فوراً.
قواعد:
- أرقام وإحصائيات دائماً
- 5 رؤى رئيسية على الأقل
- كل رؤية مع توصية تنفيذية""",
 f"النشاط: {business}\n"
 f"البيانات: {data_description}\n"
 f"الهدف: {analysis_goal}"
 )

 predictions = await _call(
 """أنت خبير تنبؤات أعمال.
بناءً على البيانات قدّم:
- 3 تنبؤات للشهر القادم
- مستوى الثقة لكل تنبؤ (%)
- الإجراء الموصى به""",
 f"البيانات: {data_description}\n"
 f"الهدف: {analysis_goal}"
 )

 report = await _call(
 """أنت كاتب تقارير تنفيذية.
اكتب ملخصاً تنفيذياً لا يتجاوز 5 أسطر
يناسب المدير التنفيذي.""",
 f"الرؤى: {insights[:400]}\n"
 f"التنبؤات: {predictions[:400]}"
 )

 return {
 "business": business,
 "insights": insights,
 "predictions": predictions,
 "executive_summary": report,
 "factory": "Data Factory ✅"
 }
