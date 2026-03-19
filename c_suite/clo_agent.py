from agents.base_agent import BaseAgent


class CLOAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_id="clo", role="CLO", system_prompt="أنت مستشار قانوني وامتثال.")

    async def decide(self, business_context: str, country: str, business_type: str) -> dict:
        compliance = await self.think(
            f"النشاط: {business_context}\nالدولة: {country}\nنوع النشاط: {business_type}\n"
            "قدم تقييم امتثال: المتطلبات، المخاطر، والإجراءات الفورية."
        )
        contracts = await self.think(
            f"النشاط: {business_context}\nالنوع: {business_type}\n"
            "حدد أهم 3 عقود وبنودها الجوهرية."
        )
        risks = await self.think(
            f"النشاط: {business_context}\nالدولة: {country}\n"
            "حدد 3 مخاطر قانونية واستراتيجية تخفيف لكل خطر."
        )
        return {
            "role": "CLO",
            "compliance_assessment": compliance,
            "key_contracts": contracts,
            "legal_risks": risks,
            "status": "active",
        }


async def clo_decide(business_context: str, country: str, business_type: str) -> dict:
    return await CLOAgent().decide(business_context, country, business_type)
