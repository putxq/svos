from agents.base_agent import BaseAgent
from agents.coo.prompts import SYSTEM_PROMPT


class COOAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_id='coo', role='COO', system_prompt=SYSTEM_PROMPT)
