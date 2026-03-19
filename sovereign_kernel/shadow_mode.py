from datetime import datetime


class ShadowMode:
    """وضع المراقبة الصامتة: مقارنة قرار وكيل جديد بقرار مرجعي دون تنفيذ."""

    def __init__(self):
        self.logs = []

    def compare(self, candidate_decision: str, reference_decision: str, meta: dict | None = None) -> dict:
        aligned = candidate_decision.strip()[:120] == reference_decision.strip()[:120]
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "aligned": aligned,
            "candidate": candidate_decision,
            "reference": reference_decision,
            "meta": meta or {},
        }
        self.logs.append(result)
        return result
