import re
from pydantic import BaseModel, Field
from datetime import datetime


class SafetyVerdict(BaseModel):
    safe: bool
    risk_score: float = Field(ge=0.0, le=1.0)
    flags: list[str] = Field(default_factory=list)
    action: str = "proceed"


class TrustSafetyKernel:
    SENSITIVE_PATTERNS = [
        r"password|secret|token|api[_-]?key|credential",
        r"delete\s+(all|everything|database|table)",
        r"drop\s+table",
        r"rm\s+-rf",
        r"send\s+money|transfer\s+funds",
    ]

    IRREVERSIBLE_ACTIONS = [
        "delete_data",
        "send_payment",
        "publish_public",
        "terminate_contract",
        "fire_agent",
        "external_api_write",
    ]

    def __init__(self):
        self._kill_switch_active = False
        self._incident_log = []

    def evaluate_action(self, action, agent_name, data_involved="", action_type="general"):
        flags = []
        risk_score = 0.0

        if self._kill_switch_active:
            return SafetyVerdict(safe=False, risk_score=1.0, flags=["KILL_SWITCH_ACTIVE"], action="kill")

        for pattern in self.SENSITIVE_PATTERNS:
            if re.search(pattern, data_involved.lower()):
                flags.append(f"sensitive_data: {pattern}")
                risk_score += 0.3

        if action_type in self.IRREVERSIBLE_ACTIONS:
            flags.append(f"irreversible: {action_type}")
            risk_score += 0.4

        risk_score = min(1.0, risk_score)

        if risk_score >= 0.8:
            va = "block"
        elif risk_score >= 0.5:
            va = "warn"
        else:
            va = "proceed"

        return SafetyVerdict(safe=risk_score < 0.5, risk_score=risk_score, flags=flags, action=va)

    def activate_kill_switch(self, reason):
        self._kill_switch_active = True

    def deactivate_kill_switch(self):
        self._kill_switch_active = False

    def get_incident_log(self):
        return self._incident_log.copy()
