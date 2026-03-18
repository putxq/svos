"""
Trust Engine — نظام الثقة والصلاحيات
"""
from datetime import datetime


class TrustEngine:
    def __init__(self):
        self.agents = {}

    def register_agent(self, agent_id: str, role: str, initial_trust: float = 1.0):
        self.agents[agent_id] = {
            "role": role,
            "trust_score": initial_trust,
            "actions": 0,
            "successes": 0,
            "registered_at": datetime.utcnow().isoformat(),
        }

    def can_act(self, agent_id: str, action_level: str = "standard") -> bool:
        agent = self.agents.get(agent_id)
        if not agent:
            return False
        thresholds = {
            "read": 0.1,
            "standard": 0.5,
            "critical": 0.8,
            "sovereign": 0.95,
        }
        threshold = thresholds.get(action_level, 0.5)
        return agent["trust_score"] >= threshold

    def record_action(self, agent_id: str, success: bool):
        if agent_id not in self.agents:
            return
        self.agents[agent_id]["actions"] += 1
        if success:
            self.agents[agent_id]["successes"] += 1
            self.agents[agent_id]["trust_score"] = min(
                1.0, self.agents[agent_id]["trust_score"] + 0.02
            )
        else:
            self.agents[agent_id]["trust_score"] = max(
                0.0, self.agents[agent_id]["trust_score"] - 0.05
            )

    def get_all_scores(self) -> dict:
        return {
            aid: {
                "trust": a["trust_score"],
                "role": a["role"],
                "success_rate": (a["successes"] / max(a["actions"], 1)),
            }
            for aid, a in self.agents.items()
        }
