import asyncio
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agents.ceo.agent import CEOAgent
from agents.cfo.agent import CFOAgent
from agents.radar.agent import RadarAgent
from agents.guardian.agent import GuardianAgent
from constitution.validator import ConstitutionValidator
from core.config import settings
from core.schemas import (
    AgentTaskRequest,
    AgentTaskResponse,
    BusinessProfile,
    DecisionRequest,
    DecisionResponse,
    RegisterAgentRequest,
    RegisterAgentResponse,
    SwarmRunRequest,
    SwarmRunResponse,
)
from engine.port_manager import PortManager
from engine.registry import AgentRegistry

registry = AgentRegistry()
port_manager = PortManager()
validator = ConstitutionValidator()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await registry.init()
    await port_manager.init()
    yield


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://192.168.100.24:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get('/health')
async def health() -> dict:
    return {'status': 'ok', 'svos': 'v1.0'}


@app.post('/constitution/validate', response_model=DecisionResponse)
async def validate_constitution(payload: DecisionRequest) -> DecisionResponse:
    return validator.validate(payload)


@app.post('/agents/register', response_model=RegisterAgentResponse)
async def register_agent(payload: RegisterAgentRequest) -> RegisterAgentResponse:
    agent_type = payload.type.upper().strip()
    if agent_type != 'CEO':
        raise HTTPException(status_code=400, detail='Only CEO agent is supported in this task')

    agent_id = str(uuid4())
    port = await port_manager.reserve(owner=payload.name)
    await registry.register_agent(
        agent_id=agent_id,
        name=payload.name,
        agent_type=agent_type,
        sovereignty=payload.sovereignty,
        port=port,
    )
    return RegisterAgentResponse(agent_id=agent_id, port=port, status='registered')


@app.post('/agents/{agent_id}/task', response_model=AgentTaskResponse)
async def run_agent_task(agent_id: str, payload: AgentTaskRequest) -> AgentTaskResponse:
    agent = await registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail='Agent not found')

    if agent['type'] != 'CEO':
        raise HTTPException(status_code=400, detail='Unsupported agent type')

    try:
        ceo = CEOAgent()
        decision = await ceo.decide(
            business_context=payload.business_context,
            goals=payload.goals,
            task=payload.task,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'CEO agent execution failed: {e}')

    decision_req = DecisionRequest(
        business=BusinessProfile(
            business_id=agent_id,
            name=payload.business_context,
            industry='general',
            goals=payload.goals,
            values=[],
            constraints=[],
        ),
        action=decision,
        rationale=payload.task,
    )
    validation = validator.validate(decision_req)
    passed = validation.status == 'approved'

    await registry.save_decision(
        agent_id=agent_id,
        task=payload.task,
        decision=decision,
        passed_constitution=passed,
    )

    return AgentTaskResponse(decision=decision, passed_constitution=passed, agent_id=agent_id)


@app.post('/swarm/run', response_model=SwarmRunResponse)
async def run_swarm(payload: SwarmRunRequest) -> SwarmRunResponse:
    try:
        ceo = CEOAgent()
        cfo = CFOAgent()
        radar = RadarAgent()

        ceo_decision, cfo_decision, radar_decision = await asyncio.gather(
            ceo.decide(payload.business_context, payload.goals, payload.task),
            cfo.decide(payload.business_context, payload.goals, payload.task),
            radar.decide(payload.business_context, payload.goals, payload.task),
        )

        guardian = GuardianAgent()
        guardian_review = await guardian.review(ceo_decision, cfo_decision, radar_decision)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Swarm execution failed: {e}')

    merged_action = (
        f"[CEO]\n{ceo_decision}\n\n"
        f"[CFO]\n{cfo_decision}\n\n"
        f"[Radar]\n{radar_decision}"
    )
    decision_req = DecisionRequest(
        business=BusinessProfile(
            business_id='swarm',
            name=payload.business_context,
            industry='general',
            goals=payload.goals,
            values=[],
            constraints=[],
        ),
        action=merged_action,
        rationale=payload.task,
    )
    validation = validator.validate(decision_req)
    passed = validation.status == 'approved'

    return SwarmRunResponse(
        passed_constitution=passed,
        decisions={
            'ceo': ceo_decision,
            'cfo': cfo_decision,
            'radar': radar_decision,
            'guardian': guardian_review,
        },
    )
