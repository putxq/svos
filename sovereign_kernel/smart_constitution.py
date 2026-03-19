from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from core.config import settings
from core.llm_provider import LLMProvider

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


class ConstitutionVerdict(BaseModel):
    approved: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    conditions: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)


class SmartConstitution:
    """
    Smart constitutional evaluator using Claude.
    - Loads constitution.yaml per sphere/client
    - Evaluates decisions against mission/values/constraints/risk/history
    - Returns structured verdict with confidence and conditions
    """

    def __init__(
        self,
        constitution_path: str | Path = "constitution.yaml",
        model: str | None = None,
    ):
        self.llm = LLMProvider(provider="anthropic")
        self.model = model or settings.anthropic_model
        self.constitution_path = Path(constitution_path)
        self.constitution = self._load_constitution(self.constitution_path)

    def _default_constitution(self) -> dict[str, Any]:
        return {
            "mission": "",
            "values": [],
            "constraints": [],
            "risk_appetite": "moderate",
            "escalation_thresholds": {
                "auto_approve": 0.85,
                "team_discuss": 0.60,
                "board_review": 0.40,
                "founder_override": 0.20,
            },
        }

    def _load_constitution(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return self._default_constitution()

        text = path.read_text(encoding="utf-8")

        # Prefer YAML if installed, otherwise JSON fallback.
        if yaml is not None:
            data = yaml.safe_load(text) or {}
        else:
            try:
                data = json.loads(text)
            except Exception:
                data = {}

        base = self._default_constitution()
        base.update(data)
        if "escalation_thresholds" in data and isinstance(data["escalation_thresholds"], dict):
            merged = dict(base["escalation_thresholds"])
            merged.update(data["escalation_thresholds"])
            base["escalation_thresholds"] = merged
        return base

    async def evaluate_decision(
        self,
        decision: str,
        agent_name: str,
        context: dict,
        business_profile: dict,
    ) -> ConstitutionVerdict:
        constitution = self.constitution

        system_prompt = (
            "You are a strict constitutional governance evaluator for an autonomous business OS. "
            "Evaluate decision quality and compliance. Return ONLY valid JSON."
        )

        schema = {
            "approved": "bool",
            "confidence": "float in range 0..1",
            "reasoning": "string",
            "conditions": ["string"],
            "alternatives": ["string"],
        }

        user_prompt = (
            f"Agent: {agent_name}\n"
            f"Decision: {decision}\n"
            f"Context: {context}\n"
            f"Business profile: {business_profile}\n"
            f"Constitution: {constitution}\n"
            "Consider: client goals, client values, financial/ethical/legal constraints, prior history in context.\n"
            f"Output schema: {json.dumps(schema, ensure_ascii=False)}"
        )

        raw = await self.llm.complete(
            system_prompt=system_prompt,
            user_message=user_prompt,
            temperature=0.1,
        )

        try:
            parsed = json.loads(raw)
        except Exception:
            # Graceful fallback when model returns non-JSON
            parsed = {
                "approved": False,
                "confidence": 0.35,
                "reasoning": f"Non-JSON response from evaluator: {raw[:400]}",
                "conditions": ["Re-run evaluation with stricter output formatting"],
                "alternatives": ["Escalate to board review"],
            }

        # Normalize confidence range
        conf = float(parsed.get("confidence", 0.0) or 0.0)
        if conf > 1.0:
            conf = conf / 100.0
        conf = max(0.0, min(1.0, conf))

        verdict = ConstitutionVerdict(
            approved=bool(parsed.get("approved", False)),
            confidence=conf,
            reasoning=str(parsed.get("reasoning", "")),
            conditions=[str(x) for x in (parsed.get("conditions") or [])],
            alternatives=[str(x) for x in (parsed.get("alternatives") or [])],
        )

        return verdict
