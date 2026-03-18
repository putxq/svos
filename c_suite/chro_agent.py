from anthropic import AsyncAnthropic
from core.config import settings
from engine.performance import PerformanceMonitor

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

async def chro_evaluate(
 monitor: PerformanceMonitor
) -> dict:

 scores = monitor.scores
 top = monitor.top_performers()
 candidates = [
 aid for aid in scores
 if monitor.should_terminate(aid)
 ]

 evaluation = await _call(
 """أنت CHRO متخصص في إدارة الوكلاء الرقميين.
قدّم تقرير أداء شامل مع توصيات:
- من يستحق الترقية والاستنساخ
- من يحتاج تدريب وتحسين
- من يجب إيقافه
كن حاسماً ومبنياً على البيانات.""",
 f"درجات الأداء: {scores}\n"
 f"الأفضل أداءً: {top}\n"
 f"مرشحون للإيقاف: {candidates}"
 )

 actions = []
 for agent_id, data in scores.items():
  if data['score'] >= 90:
   actions.append({
   "agent": agent_id,
   "action": "clone",
   "reason": "أداء ممتاز"
   })
  elif data['score'] >= 70:
   actions.append({
   "agent": agent_id,
   "action": "retain",
   "reason": "أداء جيد"
   })
  elif data['score'] < 40:
   actions.append({
   "agent": agent_id,
   "action": "terminate",
   "reason": "أداء ضعيف"
   })
  else:
   actions.append({
   "agent": agent_id,
   "action": "train",
   "reason": "يحتاج تحسين"
   })

 return {
 "role": "CHRO",
 "performance_report": evaluation,
 "workforce_actions": actions,
 "clone_candidates": [
 a["agent"] for a in actions
 if a["action"] == "clone"
 ],
 "terminate_candidates": [
 a["agent"] for a in actions
 if a["action"] == "terminate"
 ],
 "status": "active"
 }
