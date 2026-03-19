from agents.base_agent import BaseAgent
from engine.performance import PerformanceMonitor


class CHROAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_id="chro", role="CHRO", system_prompt="أنت CHRO متخصص في إدارة الوكلاء الرقميين.")

    async def evaluate(self, monitor: PerformanceMonitor) -> dict:
        scores = monitor.scores
        top = monitor.top_performers()
        candidates = [aid for aid in scores if monitor.should_terminate(aid)]

        evaluation = await self.think(
            f"درجات الأداء: {scores}\nالأفضل أداءً: {top}\nمرشحون للإيقاف: {candidates}\n"
            "قدّم تقرير أداء مع توصيات: clone/train/retain/terminate."
        )

        actions = []
        for agent_id, data in scores.items():
            if data["score"] >= 90:
                actions.append({"agent": agent_id, "action": "clone", "reason": "أداء ممتاز"})
            elif data["score"] >= 70:
                actions.append({"agent": agent_id, "action": "retain", "reason": "أداء جيد"})
            elif data["score"] < 40:
                actions.append({"agent": agent_id, "action": "terminate", "reason": "أداء ضعيف"})
            else:
                actions.append({"agent": agent_id, "action": "train", "reason": "يحتاج تحسين"})

        return {
            "role": "CHRO",
            "performance_report": evaluation,
            "workforce_actions": actions,
            "clone_candidates": [a["agent"] for a in actions if a["action"] == "clone"],
            "terminate_candidates": [a["agent"] for a in actions if a["action"] == "terminate"],
            "status": "active",
        }


async def chro_evaluate(monitor: PerformanceMonitor) -> dict:
    return await CHROAgent().evaluate(monitor)
