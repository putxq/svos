from agents.base_agent import BaseAgent
from agents.chro.prompts import SYSTEM_PROMPT


class CHROAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="CHRO", role="CHRO", department="hr")
