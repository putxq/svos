"""
Pydantic response schemas for SVOS LLM outputs.
Forces structured, validated responses from all engines.
"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from engines.confidence_engine import ConfidenceEngine


class OpportunitySchema(BaseModel):
    """Schema for a single opportunity from GravityEngine."""

    name: str = Field(default="Unknown Opportunity")
    description: str = Field(default="")
    confidence: float = Field(default=0.5)
    market_size: str = Field(default="unknown")
    competition: str = Field(default="unknown")
    recommendation: str = Field(default="evaluate")

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, v):
        return ConfidenceEngine.normalize(v)


class GravityResult(BaseModel):
    """Schema for GravityEngine full response."""

    opportunities: list[OpportunitySchema] = Field(default_factory=list)
    scan_summary: str = Field(default="")
    total_found: int = Field(default=0)

    @field_validator("total_found", mode="before")
    @classmethod
    def set_total(cls, v):
        return 0 if v is None else v


class ScenarioSchema(BaseModel):
    """Schema for a single TimeEngine scenario."""

    timeframe: str = Field(default="unknown")
    prediction: str = Field(default="")
    confidence: float = Field(default=0.5)
    risks: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, v):
        return ConfidenceEngine.normalize(v)


class TimeResult(BaseModel):
    """Schema for TimeEngine full response."""

    decision: str = Field(default="")
    scenarios: list[ScenarioSchema] = Field(default_factory=list)
    recommendation: str = Field(default="proceed_with_caution")
    avg_confidence: float = Field(default=0.5)

    @field_validator("recommendation", mode="before")
    @classmethod
    def normalize_recommendation(cls, v):
        if not isinstance(v, str):
            return "proceed_with_caution"
        v = v.strip().lower()
        valid = ["proceed", "stop", "proceed_with_caution", "caution_with_proceed"]
        if v in valid:
            if v == "caution_with_proceed":
                return "proceed_with_caution"
            return v
        if "proceed" in v:
            return "proceed_with_caution"
        if "stop" in v:
            return "stop"
        return "proceed_with_caution"

    @field_validator("avg_confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, v):
        return ConfidenceEngine.normalize(v)


class AgentThinkResult(BaseModel):
    """Schema for agent think() output."""

    analysis: str = Field(default="")
    recommendation: str = Field(default="")
    confidence: float = Field(default=0.5)
    next_steps: list[str] = Field(default_factory=list)

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, v):
        return ConfidenceEngine.normalize(v)


class CompilerOutput(BaseModel):
    """Schema for RealityCompiler output."""

    project_name: str = Field(default="")
    prd_summary: str = Field(default="")
    landing_page_content: dict = Field(default_factory=dict)
    launch_steps: list[str] = Field(default_factory=list)
    email_draft: str = Field(default="")
    confidence: float = Field(default=0.5)

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, v):
        return ConfidenceEngine.normalize(v)


def validate_response(data: dict, schema_class) -> dict:
    """
    Validate and normalize any LLM response against a Pydantic schema.
    Returns clean dict with all fields guaranteed.
    """
    try:
        obj = schema_class(**data)
        out = obj.model_dump()
        if schema_class is GravityResult and out.get("total_found", 0) == 0:
            out["total_found"] = len(out.get("opportunities", []))
        return out
    except Exception as e:
        import logging

        logging.getLogger("svos.schemas").warning(
            f"Schema validation partial fail for {schema_class.__name__}: {e}. "
            f"Using defaults for missing fields."
        )
        try:
            obj = schema_class()
            clean = obj.model_dump()
            for k, v in data.items():
                if k in clean and v is not None:
                    clean[k] = v
            out = schema_class(**clean).model_dump()
            if schema_class is GravityResult and out.get("total_found", 0) == 0:
                out["total_found"] = len(out.get("opportunities", []))
            return out
        except Exception:
            out = schema_class().model_dump()
            if schema_class is GravityResult and out.get("total_found", 0) == 0:
                out["total_found"] = len(out.get("opportunities", []))
            return out
