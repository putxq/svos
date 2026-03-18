"""
Planetary Layer — القيود الكونية العالمية
"""


class PlanetaryLayer:
    GLOBAL_CONSTRAINTS = [
        "no illegal activities",
        "no harm to humans",
        "respect privacy",
        "environmental responsibility",
        "financial compliance",
    ]

    RISK_LEVELS = {
        "low": 0.3,
        "medium": 0.6,
        "high": 0.9,
    }

    def validate_globally(self, decision: str) -> dict:
        violations = [
            c
            for c in self.GLOBAL_CONSTRAINTS
            if any(word in decision.lower() for word in c.split())
        ]
        return {
            "globally_approved": len(violations) == 0,
            "global_violations": violations,
        }

    def get_risk_threshold(self, level: str) -> float:
        return self.RISK_LEVELS.get(level, 0.6)
