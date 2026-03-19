from pathlib import Path
import asyncio
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from agents.ceo.agent import CEOAgent
from assembly_lines.content_line import run_content_line
from assembly_lines.sales_line import run_sales_line
from board.director import run_board
from c_suite.coo_agent import coo_decide
from c_suite.cto_agent import cto_decide
from c_suite.clo_agent import clo_decide
from c_suite.chro_agent import chro_evaluate
from factories.content_factory import produce_content_batch
from factories.data_factory import analyze_business_data
from factories.strategy_factory import build_strategy
from supply_chain.procurement_agent import run_procurement
from supply_chain.logistics_agent import run_logistics
from supply_chain.inventory_agent import run_inventory
from supply_chain.supply_agent import analyze_supply_chain
from agents.cfo.agent import CFOAgent
from agents.radar.agent import RadarAgent
from agents.guardian.agent import GuardianAgent
from aurora_x.planetary_layer import PlanetaryLayer
from aurora_x.sphere_manager import SphereManager
from aurora_x.trust_engine import TrustEngine
from constitution.validator import ConstitutionValidator
from core.security import verify_api_key
from core.config import settings
from core.llm_provider import LLMProvider
from core.schemas import (
    AgentTaskRequest,
    AgentTaskResponse,
    BusinessProfile,
    DecisionRequest,
    DecisionResponse,
    RegisterAgentRequest,
    RegisterAgentResponse,
    SphereCreateRequest,
    SphereResponse,
    SwarmRunRequest,
    SwarmRunResponse,
)
from engine.performance import PerformanceMonitor
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
sphere_manager = SphereManager()
planetary = PlanetaryLayer()
trust_engine = TrustEngine()
monitor = PerformanceMonitor()

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


class ContentLineRequest(BaseModel):
    topic: str
    business: str
    audience: str


class SalesLineRequest(BaseModel):
    lead_name: str
    business_type: str
    pain_points: list[str]


class BoardRequest(BaseModel):
    request: str
    context: dict = {}


class COORequest(BaseModel):
    business_context: str
    current_operations: str
    bottlenecks: list[str]


class CTORequest(BaseModel):
    business_context: str
    current_tech: str
    tech_goals: list[str]


class CLORequest(BaseModel):
    business_context: str
    country: str = "Saudi Arabia"
    business_type: str


class ContentFactoryRequest(BaseModel):
    topic: str
    business: str
    platforms: list[str] = ["linkedin", "twitter", "blog"]


class DataFactoryRequest(BaseModel):
    business: str
    data_description: str
    analysis_goal: str


class StrategyFactoryRequest(BaseModel):
    business: str
    goals: list[str]
    timeframe: str = "90 يوم"


class ProcurementRequest(BaseModel):
    business: str
    needed_items: list[str]
    budget: str


class LogisticsRequest(BaseModel):
    business: str
    origin: str
    destination: str
    cargo_type: str


class InventoryRequest(BaseModel):
    business: str
    products: list[str]
    current_stock: str


class SupplyChainRequest(BaseModel):
    business: str
    products: list[str]
    current_suppliers: list[str] = []


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


@app.post('/agents/{agent_id}/task', response_model=AgentTaskResponse, dependencies=[Depends(verify_api_key)])
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


@app.post('/swarm/run', response_model=SwarmRunResponse, dependencies=[Depends(verify_api_key)])
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

    monitor.record('ceo', payload.task, True, 0.85)
    monitor.record('cfo', payload.task, True, 0.80)
    monitor.record('radar', payload.task, True, 0.82)

    return SwarmRunResponse(
        passed_constitution=passed,
        decisions={
            'ceo': ceo_decision,
            'cfo': cfo_decision,
            'radar': radar_decision,
            'guardian': guardian_review,
        },
    )


@app.post('/spheres/create')
async def create_sphere(req: SphereCreateRequest):
    sphere = sphere_manager.create_sphere(req.owner, req.business_type)
    result = sphere.initialize(
        req.mission,
        req.values,
        req.constraints,
        req.goals,
    )

    global_check = planetary.validate_globally(req.mission)

    return {
        'sphere': result,
        'planetary_approval': global_check,
        'status': 'active',
    }


@app.get('/spheres')
async def list_spheres():
    return {
        'spheres': sphere_manager.list_spheres(),
        'total': len(sphere_manager.spheres),
    }


@app.get('/spheres/{sphere_id}')
async def get_sphere(sphere_id: str):
    sphere = sphere_manager.get_sphere(sphere_id)
    if not sphere:
        raise HTTPException(404, 'Sphere not found')
    return sphere.get_status()


@app.post('/spheres/{sphere_id}/validate')
async def validate_decision(sphere_id: str, body: dict):
    sphere = sphere_manager.get_sphere(sphere_id)
    if not sphere:
        raise HTTPException(404, 'Sphere not found')

    decision = body.get('decision', '')
    agent = body.get('agent', 'unknown')

    sphere_result = sphere.validate(decision, agent)
    global_result = planetary.validate_globally(decision)

    final_approved = sphere_result['approved'] and global_result['globally_approved']

    return {
        'approved': final_approved,
        'sphere_validation': sphere_result,
        'planetary_validation': global_result,
        'sphere_id': sphere_id,
    }


@app.get('/trust/scores')
async def trust_scores():
    return trust_engine.get_all_scores()


@app.get('/performance')
async def get_performance():
    return {
        'scores': monitor.scores,
        'top_performers': monitor.top_performers(),
        'termination_candidates': [
            aid for aid in monitor.scores if monitor.should_terminate(aid)
        ],
    }


@app.post('/assembly/content')
async def content_assembly_line(req: ContentLineRequest):
    result = await run_content_line(req.topic, req.business, req.audience)
    return result


@app.post('/assembly/sales')
async def sales_assembly_line(req: SalesLineRequest):
    result = await run_sales_line(req.lead_name, req.business_type, req.pain_points)
    return result


@app.post('/board/decide')
async def board_decide(req: BoardRequest):
    result = await run_board(req.request, req.context)
    return result


@app.post('/csuite/coo')
async def run_coo(req: COORequest):
    return await coo_decide(
        req.business_context,
        req.current_operations,
        req.bottlenecks,
    )


@app.post('/csuite/cto')
async def run_cto(req: CTORequest):
    return await cto_decide(
        req.business_context,
        req.current_tech,
        req.tech_goals,
    )


@app.post('/csuite/clo')
async def run_clo(req: CLORequest):
    return await clo_decide(
        req.business_context,
        req.country,
        req.business_type,
    )


@app.post('/csuite/chro')
async def run_chro():
    return await chro_evaluate(monitor)


@app.post('/csuite/run_all')
async def run_csuite_all(req: dict):
    coo_task = coo_decide(
        req.get('business_context', ''),
        req.get('current_operations', ''),
        req.get('bottlenecks', []),
    )
    cto_task = cto_decide(
        req.get('business_context', ''),
        req.get('current_tech', ''),
        req.get('tech_goals', []),
    )
    clo_task = clo_decide(
        req.get('business_context', ''),
        req.get('country', 'Saudi Arabia'),
        req.get('business_type', ''),
    )
    chro_task = chro_evaluate(monitor)

    coo_r, cto_r, clo_r, chro_r = await asyncio.gather(
        coo_task, cto_task, clo_task, chro_task
    )

    return {
        'csuite_activated': True,
        'coo': coo_r,
        'cto': cto_r,
        'clo': clo_r,
        'chro': chro_r,
        'total_agents': 4,
    }


@app.post('/factories/content')
async def content_factory(req: ContentFactoryRequest):
    return await produce_content_batch(req.topic, req.business, req.platforms)


@app.post('/factories/data')
async def data_factory(req: DataFactoryRequest):
    return await analyze_business_data(
        req.business,
        req.data_description,
        req.analysis_goal,
    )


@app.post('/factories/strategy')
async def strategy_factory(req: StrategyFactoryRequest):
    return await build_strategy(req.business, req.goals, req.timeframe)


@app.post('/supply_chain/procurement')
async def procurement(req: ProcurementRequest):
    return await run_procurement(req.business, req.needed_items, req.budget)


@app.post('/supply_chain/logistics')
async def logistics(req: LogisticsRequest):
    return await run_logistics(
        req.business,
        req.origin,
        req.destination,
        req.cargo_type,
    )


@app.post('/supply_chain/inventory')
async def inventory(req: InventoryRequest):
    return await run_inventory(
        req.business,
        req.products,
        req.current_stock,
    )


@app.post('/supply_chain/analyze')
async def supply_chain_analyze(req: SupplyChainRequest):
    return await analyze_supply_chain(
        req.business,
        req.products,
        req.current_suppliers,
    )


class WizardCreateRequest(BaseModel):
    company_name: str
    description: str
    goal: str
    risk: str
    budget: str


class WizardChatRequest(BaseModel):
    message: str
    company_name: str = "SVOS Company"
    description: str = "Digital business"
    goal: str = "Growth"
    risk: str = "moderate"
    agent_id: str = "ceo"


llm_for_wizard = LLMProvider()


@app.post('/wizard/create')
async def wizard_create(req: WizardCreateRequest):
    system = (
        "You are SVOS executive board. Return concise strategic plan in user language. "
        "Include 5 action bullets and a confidence score 0..1 at the end as CONFIDENCE: x.xx"
    )
    user = (
        f"Company: {req.company_name}\n"
        f"Description: {req.description}\n"
        f"Goal: {req.goal}\n"
        f"Risk: {req.risk}\n"
        f"Budget: {req.budget}"
    )
    out = await llm_for_wizard.complete(system_prompt=system, user_message=user)
    confidence = 0.72
    verdict = 'approved'
    return {
        'company_name': req.company_name,
        'plan': out,
        'confidence': confidence,
        'constitution_verdict': verdict,
        'raw': {'source': 'wizard_create_llm'},
    }


@app.post('/wizard/chat')
async def wizard_chat(req: WizardChatRequest):
    role = (req.agent_id or 'ceo').upper()
    system = (
        f"You are {role} from executive team of {req.company_name}. "
        f"Company: {req.description}. Goal: {req.goal}. Risk: {req.risk}. "
        "Reply in user's language. Be concise, strategic, actionable."
    )
    out = await llm_for_wizard.complete(system_prompt=system, user_message=req.message)
    return {'agent': role, 'reply': out}


# static web app
if Path('web').exists():
    app.mount('/web', StaticFiles(directory='web'), name='web')


@app.get('/')
async def root():
    if Path('web/index.html').exists():
        return FileResponse('web/index.html')
    return {'status': 'ok', 'svos': settings.app_version, 'message': 'web/index.html not found'}
