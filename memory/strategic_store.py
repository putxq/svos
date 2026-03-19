class StrategicStore:
    def __init__(self):
        self.records = []

    def record(self, strategy: str, outcome: str, why: str):
        self.records.append(
            {
                "strategy": strategy,
                "outcome": outcome,
                "why": why,
            }
        )

    def best_practices(self):
        return [r for r in self.records if r["outcome"] == "success"]
