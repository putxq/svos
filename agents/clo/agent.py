from agents.base_agent import BaseAgent
from agents.clo.prompts import SYSTEM_PROMPT


class CLOAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_id='clo', role='CLO', system_prompt=SYSTEM_PROMPT)
