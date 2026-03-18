from pydantic import BaseModel, Field
from typing import Literal


class BusinessProfile(BaseModel):
    business_id: str = Field(..., min_length=2)
    name: str
    industry: str
    goals: list[str] = Field(default_factory=list)
    values: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class AgentSpec(BaseModel):
    agent_id: str = Field(..., min_length=2)
    role: str
    capabilities: list[str] = Field(default_factory=list)
    status: Literal['idle', 'active', 'paused', 'failed'] = 'idle'


class RegisterAgentRequest(BaseModel):
    name: str
    type: str
    sovereignty: Literal['full', 'bounded', 'partial'] = 'full'


class RegisterAgentResponse(BaseModel):
    agent_id: str
    port: int
    status: Literal['registered']


class AgentTaskRequest(BaseModel):
    business_context: str
    goals: list[str] = Field(default_factory=list)
    task: str


class AgentTaskResponse(BaseModel):
    decision: str
    passed_constitution: bool
    agent_id: str


class SwarmRunRequest(BaseModel):
    business_context: str
    goals: list[str] = Field(default_factory=list)
    task: str


class SwarmRunResponse(BaseModel):
    passed_constitution: bool
    decisions: dict


class DecisionRequest(BaseModel):
    business: BusinessProfile
    action: str
    rationale: str = ''


class DecisionResponse(BaseModel):
    status: Literal['approved', 'rejected']
    reasons: list[str] = Field(default_factory=list)


class SphereCreateRequest(BaseModel):
    owner: str
    business_type: str
    mission: str
    values: list[str]
    constraints: list[str]
    goals: list[str]
    risk_tolerance: str = "medium"


class SphereResponse(BaseModel):
    sphere_id: str
    owner: str
    status: str
    constitution: dict
