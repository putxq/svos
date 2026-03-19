from agents.base_agent import BaseAgent
from agents.coo.prompts import SYSTEM_PROMPT


class COOAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="COO", role="COO", department="operations")
