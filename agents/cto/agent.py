from agents.base_agent import BaseAgent
from agents.cto.prompts import SYSTEM_PROMPT


class CTOAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_id='cto', role='CTO', system_prompt=SYSTEM_PROMPT)
