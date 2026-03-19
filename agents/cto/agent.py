from agents.base_agent import BaseAgent
from agents.cto.prompts import SYSTEM_PROMPT


class CTOAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="CTO", role="CTO", department="technology")
