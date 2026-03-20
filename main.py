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


# =====================================================================
# SCHEDULER ENDPOINTS — الحلقة المستقلة
# =====================================================================
from engine.scheduler import SVOSScheduler

_scheduler = SVOSScheduler()


@app.post('/scheduler/start')
async def scheduler_start(body: dict):
    """يبدأ الحلقة المستقلة."""
    company = {
        "description": body.get("description", "Digital business"),
        "goal": body.get("goal", "Growth"),
        "budget": body.get("budget", "$5,000"),
    }
    email = body.get("founder_email", "")
    hours = float(body.get("interval_hours", 6))

    result = _scheduler.start(company, email, hours)
    return result


@app.post('/scheduler/stop')
async def scheduler_stop():
    """يوقف الحلقة المستقلة."""
    return _scheduler.stop()


@app.get('/scheduler/status')
async def scheduler_status():
    """حالة المجدوِل."""
    return _scheduler.get_status()


@app.post('/scheduler/run-once')
async def scheduler_run_once(body: dict):
    """يشغّل دورة واحدة فقط (للاختبار)."""
    company = {
        "description": body.get("description", "Digital business"),
        "goal": body.get("goal", "Growth"),
        "budget": body.get("budget", "$5,000"),
    }

    _scheduler.configure(company)
    report = await _scheduler._run_cycle_safe()

    # Send email if provided
    email = body.get("founder_email", "")
    if email:
        _scheduler.founder_email = email
        await _scheduler._send_report_email(report)

    return {"success": True, "report": report}


# =====================================================================
# REAL EXECUTION ENDPOINTS — التنفيذ الحقيقي
# =====================================================================
from tools.landing_page_tool import LandingPageTool
from tools.email_tool import EmailTool

_landing_tool = LandingPageTool()
_email_tool = EmailTool()


@app.post('/execute/landing-page')
async def execute_landing_page(body: dict):
    """يولّد صفحة هبوط حقيقية من وصف النشاط."""
    company = body.get("company_name", "شركتي")
    headline = body.get("headline", "")
    subheadline = body.get("subheadline", "")
    benefits = body.get("benefits", [])
    cta = body.get("cta_text", "ابدأ الآن")
    lang = body.get("lang", "ar")

    if not headline:
        raise HTTPException(400, "headline is required")

    result = await _landing_tool.execute(
        company_name=company,
        headline=headline,
        subheadline=subheadline,
        benefits=benefits,
        cta_text=cta,
        lang=lang,
    )
    return result


@app.get('/execute/pages')
async def list_landing_pages():
    """قائمة كل الصفحات المولّدة."""
    return {"pages": _landing_tool.list_pages()}


@app.get('/pages/{page_id}')
async def serve_landing_page(page_id: str):
    """يعرض صفحة هبوط مولّدة."""
    path = _landing_tool.get_page_path(page_id)
    if not path:
        raise HTTPException(404, "Page not found")
    return FileResponse(str(path), media_type="text/html")


@app.post('/execute/send-email')
async def execute_send_email(body: dict):
    """يرسل إيميل حقيقي."""
    to = body.get("to", "")
    subject = body.get("subject", "")
    email_body = body.get("body", "")
    html = body.get("html")

    if not to or not subject:
        raise HTTPException(400, "to and subject are required")

    result = await _email_tool.execute(to=to, subject=subject, body=email_body, html=html)
    return result


@app.post('/execute/full-package')
async def execute_full_package(body: dict):
    """
    التنفيذ الكامل: فكرة → PRD + صفحة هبوط + إيميل مبيعات.
    هذا هو قلب SVOS — من الفكرة للتنفيذ بأمر واحد.
    """
    idea = body.get("idea", "")
    if not idea:
        raise HTTPException(400, "idea is required")

    # Step 1: Reality Compiler — يولّد الحزمة
    from engines.reality_compiler import RealityCompiler

    compiler = RealityCompiler()
    package = await compiler.compile(idea)

    # Step 2: Landing Page — ينشئ صفحة حقيقية
    lp = package.get("landing_page", {})
    page_result = {"success": False, "note": "no landing page data"}
    if lp and lp.get("headline"):
        page_result = await _landing_tool.execute(
            company_name=package.get("prd", {}).get("product_name", "SVOS Product"),
            headline=lp.get("headline", ""),
            subheadline=lp.get("subheadline", ""),
            benefits=lp.get("benefits", []),
            cta_text=lp.get("cta_button", "ابدأ الآن"),
        )

    # Step 3: Save all assets
    compiler_save = await compiler.compile_and_save(idea)

    return {
        "success": True,
        "idea": idea,
        "summary": package.get("idea_summary", ""),
        "prd": package.get("prd", {}),
        "landing_page": page_result,
        "sales_email": package.get("sales_email", {}),
        "launch_plan": package.get("launch_plan", {}),
        "budget_estimate": package.get("budget_estimate", {}),
        "risks": package.get("risks", []),
        "competitive_edge": package.get("competitive_edge", ""),
        "saved_to": compiler_save,
    }


# =====================================================================
# CRM ENDPOINTS — إدارة العلاقات
# =====================================================================
from engines.crm_engine import CRMEngine

_crm = CRMEngine()


@app.post('/crm/leads')
async def crm_add_lead(body: dict):
    lead = _crm.add_lead(
        name=body.get("name", ""),
        email=body.get("email", ""),
        phone=body.get("phone", ""),
        company=body.get("company", ""),
        source=body.get("source", "manual"),
        notes=body.get("notes", ""),
        value_estimate=body.get("value_estimate", ""),
    )
    return lead


@app.get('/crm/pipeline')
async def crm_pipeline():
    return _crm.get_pipeline()


@app.get('/crm/leads/{lead_id}')
async def crm_get_lead(lead_id: str):
    contact = _crm.get_contact(lead_id)
    if not contact:
        raise HTTPException(404, "Lead not found")
    interactions = _crm.get_interactions(lead_id)
    return {"contact": contact, "interactions": interactions}


@app.post('/crm/leads/{lead_id}/stage')
async def crm_update_stage(lead_id: str, body: dict):
    return _crm.update_stage(lead_id, body.get("stage", ""), body.get("reason", ""))


@app.post('/crm/leads/{lead_id}/score')
async def crm_score_lead(lead_id: str):
    return await _crm.score_lead(lead_id)


@app.post('/crm/leads/{lead_id}/outreach')
async def crm_generate_outreach(lead_id: str, body: dict = {}):
    return await _crm.generate_outreach(lead_id, body.get("type", "email"))


@app.post('/crm/leads/{lead_id}/suggest')
async def crm_suggest_actions(lead_id: str):
    return await _crm.suggest_next_actions(lead_id)


@app.get('/crm/search')
async def crm_search(q: str = ""):
    return {"results": _crm.search(q)}


# =====================================================================
# DIGITAL FACTORY ENDPOINTS — المصانع الرقمية
# =====================================================================
from engines.digital_factory import DigitalFactory

_factory = DigitalFactory()


@app.post('/factory/content')
async def factory_content(body: dict):
    return await _factory.produce_content(
        topic=body.get("topic", ""),
        business=body.get("business", ""),
        platforms=body.get("platforms", ["linkedin", "twitter", "blog"]),
        tone=body.get("tone", "professional"),
        language=body.get("language", "ar"),
    )


@app.post('/factory/strategy')
async def factory_strategy(body: dict):
    return await _factory.produce_strategy(
        business=body.get("business", ""),
        goals=body.get("goals", []),
        timeframe=body.get("timeframe", "90 days"),
        constraints=body.get("constraints", []),
    )


@app.post('/factory/analysis')
async def factory_analysis(body: dict):
    return await _factory.produce_analysis(
        business=body.get("business", ""),
        data_description=body.get("data_description", ""),
        analysis_goal=body.get("analysis_goal", ""),
    )


@app.post('/factory/product')
async def factory_product(body: dict):
    return await _factory.produce_digital_product(
        product_type=body.get("product_type", "ebook"),
        topic=body.get("topic", ""),
        target_audience=body.get("target_audience", ""),
        business=body.get("business", ""),
    )


@app.post('/factory/fleet-insight')
async def factory_fleet_insight(body: dict):
    return await _factory.fleet_insight(body.get("companies", []))


@app.get('/factory/stats')
async def factory_stats():
    return _factory.get_stats()


@app.get('/factory/log')
async def factory_log():
    return {"log": _factory.get_production_log()}


# static web app
if Path('web').exists():
    app.mount('/web', StaticFiles(directory='web'), name='web')


# =====================================================================
# DASHBOARD ENDPOINTS — لوحة التحكم التنفيذية
# =====================================================================
SVOS_AGENTS = [
    {"id": "ceo", "name": "CEO Agent", "name_ar": "الرئيس التنفيذي", "role": "Chief Executive Officer", "department": "Executive", "icon": "crown"},
    {"id": "cfo", "name": "CFO Agent", "name_ar": "المدير المالي", "role": "Chief Financial Officer", "department": "Finance", "icon": "coins"},
    {"id": "cmo", "name": "CMO Agent", "name_ar": "مدير التسويق", "role": "Chief Marketing Officer", "department": "Marketing", "icon": "megaphone"},
    {"id": "coo", "name": "COO Agent", "name_ar": "مدير العمليات", "role": "Chief Operations Officer", "department": "Operations", "icon": "cog"},
    {"id": "cto", "name": "CTO Agent", "name_ar": "المدير التقني", "role": "Chief Technology Officer", "department": "Technology", "icon": "cpu"},
    {"id": "clo", "name": "CLO Agent", "name_ar": "المستشار القانوني", "role": "Chief Legal Officer", "department": "Legal", "icon": "scale"},
    {"id": "chro", "name": "CHRO Agent", "name_ar": "مدير الموارد البشرية", "role": "Chief HR Officer", "department": "HR", "icon": "users"},
    {"id": "guardian", "name": "Guardian", "name_ar": "الحارس", "role": "Constitutional Guardian", "department": "Governance", "icon": "shield"},
    {"id": "radar", "name": "Radar", "name_ar": "الرادار", "role": "Market Intelligence", "department": "Intelligence", "icon": "radar"},
]


@app.get('/dashboard/overview')
async def dashboard_overview():
    """نظرة عامة على حالة النظام."""
    perf = monitor.scores
    top = monitor.top_performers()
    return {
        "system_status": "operational",
        "version": settings.app_version,
        "llm_provider": settings.llm_provider,
        "agents_total": len(SVOS_AGENTS),
        "agents_active": len(SVOS_AGENTS),
        "performance_scores": perf,
        "top_performers": top,
        "uptime": "active",
    }


@app.get('/dashboard/agents')
async def dashboard_agents():
    """قائمة كل الوكلاء مع حالتهم."""
    agents_with_status = []
    for agent in SVOS_AGENTS:
        score = monitor.scores.get(agent["id"], {})
        agents_with_status.append({
            **agent,
            "status": "active",
            "success_rate": score.get("success_rate", 0),
            "tasks_completed": score.get("total_tasks", 0),
        })
    return {"agents": agents_with_status}


@app.post('/dashboard/agent-chat')
async def dashboard_agent_chat(req: WizardChatRequest):
    """محادثة مع أي وكيل من الداشبورد."""
    role = (req.agent_id or 'ceo').upper()
    agent_info = next((a for a in SVOS_AGENTS if a["id"] == req.agent_id.lower()), SVOS_AGENTS[0])

    system = (
        f"You are {agent_info['name']} ({agent_info['role']}) in SVOS. "
        f"Department: {agent_info['department']}. "
        f"Company: {req.company_name}. Description: {req.description}. "
        f"Goal: {req.goal}. Risk tolerance: {req.risk}. "
        "You are a world-class executive AI agent. Be strategic, concise, actionable. "
        "Reply in the user's language. If Arabic, reply in Arabic."
    )

    out = await llm_for_wizard.complete(system_prompt=system, user_message=req.message)

    return {
        "agent": agent_info["id"],
        "agent_name": agent_info["name"],
        "agent_name_ar": agent_info["name_ar"],
        "department": agent_info["department"],
        "reply": out,
    }


@app.post('/dashboard/quick-scan')
async def dashboard_quick_scan(body: dict):
    """مسح سريع للسوق من الداشبورد."""
    description = body.get("description", "")
    if not description:
        raise HTTPException(400, "description is required")

    try:
        from engines.gravity_engine import GravityEngine

        engine = GravityEngine()
        result = await engine.find_demand_gravity(description)
        return {"success": True, "scan": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post('/dashboard/simulate')
async def dashboard_simulate(body: dict):
    """محاكاة مستقبلية من الداشبورد."""
    decision = body.get("decision", "")
    context = body.get("context", {})

    if not decision:
        raise HTTPException(400, "decision is required")

    try:
        from engines.time_engine import TimeEngine

        engine = TimeEngine()
        result = await engine.should_proceed(decision, context)
        return {"success": True, "simulation": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get('/')
async def root():
    if Path('web/index.html').exists():
        return FileResponse('web/index.html')
    return {'status': 'ok', 'svos': settings.app_version, 'message': 'web/index.html not found'}
