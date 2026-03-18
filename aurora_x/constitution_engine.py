"""
AURORA-X — محرك الدستور الذكي
يتكيف مع كل قطاع ويتعلم من كل قرار
"""
from datetime import datetime


class ConstitutionEngine:
    def __init__(self, sphere_id: str):
        self.sphere_id = sphere_id
        self.constitution = {
            "mission": "",
            "values": [],
            "constraints": [],
            "goals": [],
            "risk_tolerance": "medium",
            "created_at": datetime.utcnow().isoformat(),
        }
        self.decision_history = []
        self.trust_scores = {}

    def build_from_input(
        self,
        mission: str,
        values: list[str],
        constraints: list[str],
        goals: list[str],
        risk_tolerance: str = "medium",
    ):
        self.constitution.update(
            {
                "mission": mission,
                "values": values,
                "constraints": constraints,
                "goals": goals,
                "risk_tolerance": risk_tolerance,
            }
        )
        return self.constitution

    def validate_decision(self, decision: str, agent: str) -> dict:
        violations = []

        for constraint in self.constitution["constraints"]:
            if constraint.lower() in decision.lower():
                violations.append(constraint)

        trust = self.trust_scores.get(agent, 1.0)
        approved = len(violations) == 0 and trust > 0.5

        self.decision_history.append(
            {
                "decision": decision[:100],
                "agent": agent,
                "approved": approved,
                "violations": violations,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        return {
            "approved": approved,
            "violations": violations,
            "trust_score": trust,
            "agent": agent,
        }

    def update_trust(self, agent: str, success: bool):
        current = self.trust_scores.get(agent, 1.0)
        if success:
            self.trust_scores[agent] = min(1.0, current + 0.05)
        else:
            self.trust_scores[agent] = max(0.0, current - 0.1)

    def get_summary(self) -> dict:
        return {
            "sphere_id": self.sphere_id,
            "constitution": self.constitution,
            "decisions_made": len(self.decision_history),
            "trust_scores": self.trust_scores,
            "approved_rate": (
                sum(1 for d in self.decision_history if d["approved"])
                / max(len(self.decision_history), 1)
            ),
        }
