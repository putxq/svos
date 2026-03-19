from pydantic import BaseModel, Field


class ConfidenceResult(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    level: str
    factors: dict


class ConfidenceEngine:
    def calculate(
        self,
        task_clarity: float,
        data_availability: float,
        past_success_rate: float,
        constitution_alignment: float,
        market_volatility: float,
    ) -> ConfidenceResult:
        """
        score = (
          task_clarity * 0.25 +
          data_availability * 0.20 +
          past_success_rate * 0.25 +
          constitution_alignment * 0.20 +
          (1 - market_volatility) * 0.10
        )
        """

        def clamp(v: float) -> float:
            return max(0.0, min(1.0, float(v)))

        task_clarity = clamp(task_clarity)
        data_availability = clamp(data_availability)
        past_success_rate = clamp(past_success_rate)
        constitution_alignment = clamp(constitution_alignment)
        market_volatility = clamp(market_volatility)

        score = (
            task_clarity * 0.25
            + data_availability * 0.20
            + past_success_rate * 0.25
            + constitution_alignment * 0.20
            + (1 - market_volatility) * 0.10
        )
        score = round(clamp(score), 4)

        # default policy bands (can be overridden by route_decision thresholds)
        if score >= 0.85:
            level = "auto_execute"
        elif score >= 0.60:
            level = "team_discuss"
        elif score >= 0.40:
            level = "board_review"
        else:
            level = "founder_override"

        return ConfidenceResult(
            score=score,
            level=level,
            factors={
                "task_clarity": task_clarity,
                "data_availability": data_availability,
                "past_success_rate": past_success_rate,
                "constitution_alignment": constitution_alignment,
                "market_volatility": market_volatility,
                "stability_factor": round(1 - market_volatility, 4),
            },
        )

    def route_decision(self, score: float, thresholds: dict) -> str:
        """يوجه القرار حسب الحدود المعرّفة في الدستور"""
        score = max(0.0, min(1.0, float(score)))

        auto_approve = float(thresholds.get("auto_approve", 0.85))
        team_discuss = float(thresholds.get("team_discuss", 0.60))
        board_review = float(thresholds.get("board_review", 0.40))
        founder_override = float(thresholds.get("founder_override", 0.20))

        # ordered from highest confidence to lowest
        if score >= auto_approve:
            return "auto_execute"
        if score >= team_discuss:
            return "team_discuss"
        if score >= board_review:
            return "board_review"
        if score >= founder_override:
            return "founder_override"
        return "founder_override"
