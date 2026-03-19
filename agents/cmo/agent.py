from agents.base_agent import BaseAgent
from agents.cmo.prompts import SYSTEM_PROMPT


class CMOAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="CMO", role="CMO", department="marketing")
