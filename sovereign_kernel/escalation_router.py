class EscalationRouter:
    """توجيه القرار حسب مستوى الثقة."""

    def __init__(self):
        self.routes = {
            "block": "reject",
            "review": "human_review",
            "auto_approve": "execute",
        }

    def dispatch(self, confidence_route: str) -> str:
        return self.routes.get(confidence_route, "human_review")
