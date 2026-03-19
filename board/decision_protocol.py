class DecisionProtocol:
    def finalize(self, proposal: str, consensus: dict, confidence: float) -> dict:
        if consensus.get("escalate"):
            return {
                "status": "escalated",
                "reason": "Peer objections detected",
                "proposal": proposal,
                "confidence": confidence,
                "consensus": consensus,
            }
        return {
            "status": "approved",
            "proposal": proposal,
            "confidence": confidence,
            "consensus": consensus,
        }
