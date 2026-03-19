from agents.base_agent import BaseAgent


class COOAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_id="coo", role="COO", system_prompt="أنت COO خبير في العمليات.")

    async def decide(self, business_context: str, current_operations: str, bottlenecks: list[str]) -> dict:
        ops_plan = await self.think(
            f"النشاط: {business_context}\nالعمليات الحالية: {current_operations}\nالاختناقات: {', '.join(bottlenecks)}\n"
            "ضع خطة تشغيلية تنفيذية فورية مع KPIs رقمية."
        )
        efficiency = await self.think(
            f"العمليات: {current_operations}\nالاختناقات: {', '.join(bottlenecks)}\n"
            "حدد 3 إجراءات فورية لرفع الكفاءة مع نسب التحسين."
        )
        kpis = await self.think(
            f"النشاط: {business_context}\nالخطة: {ops_plan[:300]}\n"
            "أعطِ 5 مؤشرات أداء مع baseline وهدف 30 يوم وطريقة القياس."
        )
        return {
            "role": "COO",
            "operations_plan": ops_plan,
            "efficiency_actions": efficiency,
            "kpis": kpis,
            "status": "active",
        }


async def coo_decide(business_context: str, current_operations: str, bottlenecks: list[str]) -> dict:
    return await COOAgent().decide(business_context, current_operations, bottlenecks)
