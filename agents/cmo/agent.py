from agents.base_agent import BaseAgent
from agents.cmo.prompts import SYSTEM_PROMPT


class CMOAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_id='cmo', role='CMO', system_prompt=SYSTEM_PROMPT)
