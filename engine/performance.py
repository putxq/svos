class PerformanceMonitor:
    def __init__(self):
        self.scores = {}

    def record(self, agent_id: str, task: str, success: bool, quality: float = 0.8):
        if agent_id not in self.scores:
            self.scores[agent_id] = {
                "tasks": 0,
                "successes": 0,
                "quality_sum": 0,
                "score": 100.0,
            }

        s = self.scores[agent_id]
        s["tasks"] += 1
        if success:
            s["successes"] += 1
        s["quality_sum"] += quality

        # حساب الـ score
        success_rate = s["successes"] / s["tasks"]
        avg_quality = s["quality_sum"] / s["tasks"]
        s["score"] = (success_rate * 60 + avg_quality * 40) * 100

        return s["score"]

    def should_terminate(self, agent_id: str) -> bool:
        s = self.scores.get(agent_id, {})
        return s.get("score", 100) < 40

    def top_performers(self) -> list:
        return sorted(
            self.scores.items(),
            key=lambda x: x[1]["score"],
            reverse=True,
        )[:3]
