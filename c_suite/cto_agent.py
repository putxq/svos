from agents.base_agent import BaseAgent


class CTOAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_id="cto", role="CTO", system_prompt="أنت CTO استراتيجي.")

    async def decide(self, business_context: str, current_tech: str, tech_goals: list[str]) -> dict:
        tech_strategy = await self.think(
            f"النشاط: {business_context}\nالتقنية الحالية: {current_tech}\nالأهداف: {', '.join(tech_goals)}\n"
            "ضع استراتيجية تقنية واضحة: أدوات، أولويات، مخاطر وتخفيف."
        )
        ai_roadmap = await self.think(
            f"النشاط: {business_context}\nالأهداف: {', '.join(tech_goals)}\n"
            "أعط خارطة طريق AI: الآن/30 يوم/90 يوم + تكلفة تقريبية."
        )
        security = await self.think(
            f"النشاط: {business_context}\nالتقنية: {current_tech}\n"
            "حدد 3 مخاطر أمنية مع خطوة فورية لكل مخاطرة."
        )
        return {
            "role": "CTO",
            "tech_strategy": tech_strategy,
            "ai_roadmap": ai_roadmap,
            "security_assessment": security,
            "status": "active",
        }


async def cto_decide(business_context: str, current_tech: str, tech_goals: list[str]) -> dict:
    return await CTOAgent().decide(business_context, current_tech, tech_goals)
