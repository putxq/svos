import logging
from typing import Any

logger = logging.getLogger("svos.engines.confidence")


class ConfidenceEngine:
    """
    Centralized confidence scoring and normalization.

    Thresholds (from SmartConstitution):
    >= 0.85 -> auto_execute (agent acts independently)
    >= 0.60 -> discuss (agents discuss before acting)
    >= 0.40 -> board_review (C-suite board must approve)
    < 0.40 -> founder_required (human founder decides)
    """

    THRESHOLDS = {
        "auto_execute": 0.85,
        "discuss": 0.60,
        "board_review": 0.40,
        "founder_required": 0.0,
    }

    WORD_MAP = {
        "very high": 0.92,
        "very_high": 0.92,
        "high": 0.80,
        "medium-high": 0.70,
        "medium_high": 0.70,
        "medium": 0.55,
        "moderate": 0.55,
        "medium-low": 0.40,
        "medium_low": 0.40,
        "low": 0.25,
        "very low": 0.10,
        "very_low": 0.10,
        "none": 0.0,
    }

    @classmethod
    def normalize(cls, value: Any) -> float:
        """
        Normalize any confidence value to 0.0-1.0 float.
        Handles: float, int, string percentage, word labels, 0-100 scale.
        """
        if value is None:
            return 0.5

        if isinstance(value, (int, float)):
            v = float(value)
            if v > 1.0 and v <= 100.0:
                return round(v / 100.0, 4)
            elif v > 100.0:
                return 1.0
            elif v < 0.0:
                return 0.0
            return round(v, 4)

        if isinstance(value, str):
            text = value.strip().lower()

            text_clean = text.replace(" ", "").replace("%", "")
            try:
                v = float(text_clean)
                if v > 1.0 and v <= 100.0:
                    return round(v / 100.0, 4)
                elif v <= 1.0 and v >= 0.0:
                    return round(v, 4)
                elif v > 100.0:
                    return 1.0
                return 0.0
            except ValueError:
                pass

            if text in cls.WORD_MAP:
                return cls.WORD_MAP[text]

            for word, score in cls.WORD_MAP.items():
                if word in text:
                    return score

        logger.warning(f"Could not normalize confidence: {value!r}, defaulting to 0.5")
        return 0.5

    @classmethod
    def get_action_level(cls, confidence: float) -> str:
        """Determine what action level a confidence score maps to."""
        c = cls.normalize(confidence)
        if c >= cls.THRESHOLDS["auto_execute"]:
            return "auto_execute"
        elif c >= cls.THRESHOLDS["discuss"]:
            return "discuss"
        elif c >= cls.THRESHOLDS["board_review"]:
            return "board_review"
        else:
            return "founder_required"

    @classmethod
    def evaluate(cls, confidence: Any, context: str = "") -> dict:
        """
        Full confidence evaluation with normalized score and action level.
        """
        normalized = cls.normalize(confidence)
        action = cls.get_action_level(normalized)

        result = {
            "raw_value": confidence,
            "normalized": normalized,
            "percentage": f"{normalized * 100:.1f}%",
            "action_level": action,
            "auto_approve": action == "auto_execute",
            "needs_discussion": action == "discuss",
            "needs_board": action == "board_review",
            "needs_founder": action == "founder_required",
        }

        if context:
            result["context"] = context

        logger.info(
            f"Confidence: {confidence!r} -> {normalized:.3f} ({result['percentage']}) "
            f"-> {action}"
        )
        return result
