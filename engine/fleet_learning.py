class FleetLearning:
    def __init__(self):
        self.lessons = []

    def ingest(self, sphere_id: str, success: bool, what_worked: str, what_failed: str):
        self.lessons.append(
            {
                "sphere_id": sphere_id,
                "success": success,
                "what_worked": what_worked,
                "what_failed": what_failed,
            }
        )

    def best_practices(self):
        return [l for l in self.lessons if l["success"]]
