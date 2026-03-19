from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class MessageEnvelope(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid4()))
    correlation_id: str | None = None
    trace_id: str | None = None
    from_agent: str
    to_agent: str
    intent: str
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: Literal["low", "normal", "high", "critical"] = "normal"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SpawnRequest(BaseModel):
    parent_agent: str
    role: str
    objective: str
    budget_tokens: int = Field(default=1500, ge=100, le=200000)
    max_minutes: int = Field(default=30, ge=1, le=1440)
    context: dict[str, Any] = Field(default_factory=dict)


class SpawnResult(BaseModel):
    spawned: bool
    child_agent_id: str | None = None
    reason: str = ""


class RunCheckpoint(BaseModel):
    run_id: str
    agent_id: str
    state: Literal["created", "running", "waiting", "done", "failed"]
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    note: str = ""
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConstitutionCheckRequest(BaseModel):
    business_id: str
    actor: str
    action: str
    rationale: str = ""
    context: dict[str, Any] = Field(default_factory=dict)


class ConstitutionCheckResponse(BaseModel):
    approved: bool
    risk_score: float = Field(default=0.5, ge=0.0, le=1.0)
    reasons: list[str] = Field(default_factory=list)
    violated_rules: list[str] = Field(default_factory=list)
