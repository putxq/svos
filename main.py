from pathlib import Path
import os
import asyncio
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

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
from billing.auth import verify_api_key as verify_customer_api_key, issue_api_key, list_keys
from core.config import settings
from core.tenant import set_tenant, get_customer_id, get_tenant_dir, get_tenant_crm_dir, get_tenant_dna_dir
from core.activity_log import log_activity, get_recent_activity, get_activity_summary
from billing.onboarding import onboard_customer, get_onboarding_status
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

PROTECTED_PREFIXES = ("/dashboard", "/tools", "/billing", "/scheduler", "/a2a", "/mcp", "/my")
PUBLIC_EXACT = {"/", "/health", "/billing/plans", "/billing/checkout", "/auth/issue-key", "/auth/ping", "/onboard", "/onboard/status", "/llm/providers"}
PUBLIC_PREFIXES = ("/web", "/pages", "/.well-known")


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    import time as _time
    path = request.url.path
    start = _time.time()
    customer_id = ""

    if path in PUBLIC_EXACT or any(path.startswith(p) for p in PUBLIC_PREFIXES):
        response = await call_next(request)
        return response

    if any(path.startswith(p) for p in PROTECTED_PREFIXES):
        key = request.headers.get("x-api-key", "")
        auth = verify_customer_api_key(key)
        if not auth.get("ok"):
            log_activity("", request.method, path, 401, detail=auth.get("reason", ""))
            return JSONResponse(status_code=401, content={"error": "unauthorized", "reason": auth.get("reason", "invalid_api_key")})
        request.state.auth = auth
        customer_id = auth.get("customer_id", "")
        # Set tenant context for this request
        set_tenant(
            customer_id=customer_id,
            plan_id=auth.get("plan_id", ""),
            is_master=auth.get("is_master", False),
        )

    response = await call_next(request)
    duration_ms = (_time.time() - start) * 1000
    if customer_id:
        log_activity(customer_id, request.method, path, response.status_code, duration_ms)
    return response



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


# =====================================================================
# REVENUE ENGINE ENDPOINTS
# =====================================================================
from engines.revenue_engine import RevenueEngine

_revenue = RevenueEngine()


@app.post('/revenue/discover')
async def revenue_discover(body: dict):
    return await _revenue.discover_streams(
        business=body.get("business", ""),
        current_revenue=body.get("current_revenue", ""),
        goals=body.get("goals", []),
    )


@app.post('/revenue/evaluate')
async def revenue_evaluate(body: dict):
    return await _revenue.evaluate_stream(
        stream_name=body.get("stream_name", ""),
        business_context=body.get("business", ""),
    )


@app.post('/revenue/pricing')
async def revenue_pricing(body: dict):
    return await _revenue.generate_pricing(
        product=body.get("product", ""),
        target_market=body.get("target_market", ""),
        competitors=body.get("competitors", ""),
    )


@app.post('/revenue/forecast')
async def revenue_forecast(body: dict):
    return await _revenue.forecast(
        business=body.get("business", ""),
        streams=body.get("streams", []),
        months=body.get("months", 12),
    )


@app.get('/revenue/summary')
async def revenue_summary():
    return _revenue.get_summary()


# =====================================================================
# COMPANY DNA ENDPOINTS
# =====================================================================
from engines.company_dna import CompanyDNA

_dna = CompanyDNA()


@app.post('/dna/initialize')
async def dna_init(body: dict):
    return _dna.initialize(
        name=body.get("name", ""),
        mission=body.get("mission", ""),
        vision=body.get("vision", ""),
        values=body.get("values", []),
        personality=body.get("personality"),
    )


@app.get('/dna/profile')
async def dna_profile():
    return _dna.get_dna()


@app.post('/dna/record-decision')
async def dna_record_decision(body: dict):
    _dna.record_decision(
        decision=body.get("decision", ""),
        outcome=body.get("outcome", ""),
        success=body.get("success", False),
    )
    return {"recorded": True, "success_rate": _dna.get_success_rate()}


@app.post('/dna/record-lesson')
async def dna_record_lesson(body: dict):
    _dna.record_lesson(
        lesson=body.get("lesson", ""),
        category=body.get("category", "general"),
    )
    return {"recorded": True}


@app.post('/dna/evolve')
async def dna_evolve():
    return await _dna.evolve()


@app.post('/dna/brand-voice')
async def dna_brand_voice():
    return await _dna.generate_brand_voice()


# static web app
BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / 'web'
PAGES_DIR = BASE_DIR / 'workspace' / 'pages'
if WEB_DIR.exists():
    app.mount('/web', StaticFiles(directory=str(WEB_DIR)), name='web')
if PAGES_DIR.exists():
    app.mount('/pages', StaticFiles(directory=str(PAGES_DIR)), name='pages')


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

# ============================================================
# TOOL EXECUTION ENDPOINTS (Added by SVOS Tool System)
# ============================================================
from tool_registry import build_registry

tool_registry = build_registry()


@app.get('/tools/list')
async def list_tools():
    return {"tools": tool_registry.list_all()}


@app.get('/tools/for-role/{role}')
async def tools_for_role(role: str):
    return {"role": role, "tools": tool_registry.get_tools_for_role(role)}


@app.post('/tools/execute')
async def execute_tool(body: dict):
    tool_name = body.get("tool", "")
    agent_role = body.get("agent_role", "")
    method = body.get("method", "")
    params = body.get("params", {})

    if not all([tool_name, agent_role, method]):
        raise HTTPException(400, "Required: tool, agent_role, method")

    return tool_registry.execute(tool_name, agent_role, method, **params)


@app.post('/tools/whatsapp/send')
async def send_whatsapp(body: dict):
    return tool_registry.execute(
        "whatsapp",
        body.get("agent_role", "CMO"),
        "send",
        to=body.get("to", ""),
        body=body.get("body", "")
    )


@app.post('/tools/email/send')
async def send_email(body: dict):
    return tool_registry.execute(
        "email",
        body.get("agent_role", "CMO"),
        "send",
        to=body.get("to", ""),
        subject=body.get("subject", ""),
        body=body.get("body", ""),
        html=body.get("html", None)
    )


@app.post('/tools/landing-page/generate')
async def generate_landing_page(body: dict):
    return tool_registry.execute(
        "landing_page",
        body.get("agent_role", "CMO"),
        "generate",
        title=body.get("title", ""),
        headline=body.get("headline", ""),
        sub_headline=body.get("sub_headline", ""),
        cta_text=body.get("cta_text", "Get Started"),
        cta_link=body.get("cta_link", "#"),
        features=body.get("features", None),
        lang=body.get("lang", "ar")
    )


@app.post('/tools/social/post')
async def social_post(body: dict):
    return tool_registry.execute(
        "social_post",
        body.get("agent_role", "CMO"),
        "post",
        content=body.get("content", ""),
        platform=body.get("platform", "twitter")
    )


@app.get('/dashboard/agent/{role}')
async def dashboard_agent_detail(role: str):
    """Get detailed info about a specific agent."""
    from agents import AGENT_REGISTRY
    from tool_registry import build_registry

    role_upper = role.upper()
    if role_upper not in AGENT_REGISTRY:
        raise HTTPException(404, f"Agent '{role_upper}' not found")

    registry = build_registry()
    tools = registry.get_tools_for_role(role_upper)

    return {
        "success": True,
        "agent": {
            "role": role_upper,
            "class": AGENT_REGISTRY[role_upper].__name__,
            "tools": tools,
            "endpoints": {
                "think": f"/agents/{role_upper}/think",
                "discuss": "/dashboard/discuss",
                "chat": "/dashboard/chat",
            },
        },
    }

@app.get('/dashboard')
async def dashboard_page():
    """Serve the founder dashboard UI."""
    dash_path = Path('web/dashboard.html')
    if dash_path.exists():
        return FileResponse(str(dash_path))
    return {'error': 'Dashboard not found. Expected at web/dashboard.html'}

# ============================================================
# AUTONOMOUS LOOP ENDPOINTS (Priority 3 - Scheduler + Self-Healing)
# ============================================================
from scheduler import get_scheduler


@app.get('/scheduler/status')
async def scheduler_status_v2():
    s = get_scheduler()
    return {"success": True, "scheduler": s.get_status()}


@app.post('/scheduler/start')
async def scheduler_start_v2(body: dict = {}):
    s = get_scheduler()
    hours = body.get("cycle_hours", None)
    if hours:
        s.cycle_hours = float(hours)
    await s.start()
    return {"success": True, "message": f"Scheduler started (cycle every {s.cycle_hours}h)"}


@app.post('/scheduler/stop')
async def scheduler_stop_v2():
    s = get_scheduler()
    await s.stop()
    return {"success": True, "message": "Scheduler stopped"}


@app.post('/scheduler/run-now')
async def scheduler_run_now():
    s = get_scheduler()
    try:
        result = await s._run_cycle()
        return {"success": True, "cycle": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get('/scheduler/heartbeat')
async def scheduler_heartbeat():
    s = get_scheduler()
    health = await s.heartbeat()
    return {"success": True, "health": health}


@app.get('/scheduler/history')
async def scheduler_history_v2():
    s = get_scheduler()
    return {
        "success": True,
        "total_cycles": len(s.cycle_history),
        "recent": s.cycle_history[-5:] if s.cycle_history else [],
        "errors": s.errors[-10:] if s.errors else [],
    }

# ============================================================
# CONFIDENCE ENGINE ENDPOINT
# ============================================================
@app.post('/dashboard/confidence')
async def dashboard_confidence(body: dict):
    """Calculate confidence score for a decision."""
    from engines.confidence_engine import ConfidenceEngine

    decision = body.get("decision", "")
    context = body.get("context", {})
    raw_confidence = body.get("confidence", None)

    if raw_confidence is not None:
        result = ConfidenceEngine.evaluate(raw_confidence, context=decision)
        return {"success": True, "evaluation": result}

    try:
        from engines.time_engine import TimeEngine

        engine = TimeEngine()
        sim = await engine.should_proceed(decision, context)
        conf = sim.get("avg_confidence", 0.5)
        result = ConfidenceEngine.evaluate(conf, context=decision)
        result["simulation"] = sim
        return {"success": True, "evaluation": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ============================================================
# BILLING ENDPOINTS (Priority 5 - Economy)
# ============================================================
from billing.plans import list_plans, get_plan
from billing.checkout import get_provider
from billing.subscriptions import get_subscription_manager


@app.get('/billing/plans')
async def billing_plans():
    """List all available subscription plans."""
    return {"success": True, "plans": list_plans()}


@app.get('/billing/plan/{plan_id}')
async def billing_plan_detail(plan_id: str):
    """Get details of a specific plan."""
    plan = get_plan(plan_id)
    return {"success": True, "plan": plan}


@app.post('/billing/checkout')
async def billing_checkout(body: dict):
    """
    Create a checkout session.
    Body:
    {
      "plan_id": "professional",
      "email": "customer@example.com",
      "region": "international" | "sa",
      "success_url": "https://...",
      "cancel_url": "https://..."
    }
    """
    plan_id = body.get("plan_id", "starter")
    email = body.get("email", "")
    region = body.get("region", "international")
    success_url = body.get("success_url", "https://svos.ai/success")
    cancel_url = body.get("cancel_url", "https://svos.ai/cancel")

    if not email:
        raise HTTPException(400, "email is required")

    provider = get_provider(region)
    if region in ("sa", "saudi", "sar", "local"):
        result = provider.create_payment(plan_id, email, success_url)
    else:
        result = provider.create_checkout_session(plan_id, email, success_url, cancel_url)

    return {"success": True, "checkout": result}


@app.post('/billing/webhook/stripe')
async def billing_webhook_stripe(request):
    """Handle Stripe webhook events."""
    body = await request.body()
    sig = request.headers.get("stripe-signature", "")

    provider = get_provider("international")
    verification = provider.verify_webhook(body, sig)

    if not verification.get("verified"):
        return {"success": False, "reason": verification.get("reason", "unverified")}

    event = verification["event"]
    event_type = event.get("type", "")

    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        customer_email = session.get("customer_email", "")
        plan_id = session.get("metadata", {}).get("plan_id", "starter")
        customer_id = session.get("customer", session.get("id", ""))

        mgr = get_subscription_manager()
        result = mgr.provision(customer_id, plan_id, customer_email, payment_ref=session.get("id", ""))

        return {"success": True, "provisioned": True, "result": result}

    return {"success": True, "event_type": event_type, "action": "ignored"}


@app.post('/billing/provision')
async def billing_provision(body: dict):
    """
    Manually provision a subscription (for testing or manual sales).
    Body: {"customer_id": "...", "plan_id": "professional", "email": "..."}
    """
    customer_id = body.get("customer_id", "")
    plan_id = body.get("plan_id", "starter")
    email = body.get("email", "")

    if not customer_id or not email:
        raise HTTPException(400, "customer_id and email required")

    mgr = get_subscription_manager()
    result = mgr.provision(customer_id, plan_id, email)
    return {"success": True, "result": result}


@app.get('/billing/subscription/{customer_id}')
async def billing_subscription(customer_id: str):
    """Get subscription status for a customer."""
    mgr = get_subscription_manager()
    return mgr.get_subscription(customer_id)


@app.post('/billing/check-limit')
async def billing_check_limit(body: dict):
    """
    Check if a customer can use a resource.
    Body: {"customer_id": "...", "resource": "cycle" | "api_call" | "tool:whatsapp"}
    """
    customer_id = body.get("customer_id", "")
    resource = body.get("resource", "")

    if not customer_id or not resource:
        raise HTTPException(400, "customer_id and resource required")

    mgr = get_subscription_manager()
    return mgr.check_limit(customer_id, resource)


@app.post('/billing/record-usage')
async def billing_record_usage(body: dict):
    """Record usage for metering."""
    customer_id = body.get("customer_id", "")
    resource = body.get("resource", "")
    amount = body.get("amount", 1)

    mgr = get_subscription_manager()
    return mgr.record_usage(customer_id, resource, amount)


@app.get('/billing/customers')
async def billing_customers():
    """List all subscriptions (admin)."""
    mgr = get_subscription_manager()
    subs = mgr.list_all()
    return {"success": True, "total": len(subs), "customers": subs}

# ============================================================
# MCP PROTOCOL ENDPOINTS
# ============================================================
from infrastructure.mcp_server import build_mcp_server

_mcp_server = None


def get_mcp_server():
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = build_mcp_server()
    return _mcp_server


@app.get('/mcp/tools')
async def mcp_list_tools():
    """List all SVOS tools in MCP format."""
    server = get_mcp_server()
    return {"tools": server.list_tools()}


@app.post('/mcp/tools/call')
async def mcp_call_tool(body: dict):
    """Call an SVOS tool via MCP protocol."""
    server = get_mcp_server()
    name = body.get("name", "")
    arguments = body.get("arguments", {})
    result = await server.call_tool(name, arguments)
    return result


@app.post('/mcp/rpc')
async def mcp_json_rpc(body: dict):
    """Handle MCP JSON-RPC requests (initialize, tools/list, tools/call)."""
    server = get_mcp_server()
    return server.handle_request(body)


# ============================================================
# A2A PROTOCOL ENDPOINTS
# ============================================================
from infrastructure.a2a_protocol import get_a2a_handler


@app.get('/.well-known/agent.json')
async def a2a_well_known():
    """A2A discovery endpoint - returns list of all agent cards."""
    handler = get_a2a_handler()
    return {
        "name": "SVOS - Sovereign Virtual Operating System",
        "description": "AI-powered autonomous digital company platform with 9 C-suite agents",
        "url": "https://svos.ai",
        "version": "1.0.0",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
        },
        "agents": handler.list_agent_cards(),
    }


@app.get('/a2a/agents')
async def a2a_list_agents():
    """List all SVOS agents with their A2A cards."""
    handler = get_a2a_handler()
    return {"agents": handler.list_agent_cards()}


@app.get('/a2a/agents/{role}')
async def a2a_agent_card(role: str):
    """Get A2A agent card for a specific role."""
    handler = get_a2a_handler()
    card = handler.get_agent_card(role)
    if not card:
        raise HTTPException(404, f"Agent '{role}' not found")
    return card


@app.post('/a2a/tasks')
async def a2a_create_task(body: dict):
    """
    Create and execute an A2A task.
    Body:
    {
      "agent": "CEO",
      "message": "Analyze the Saudi restaurant market",
      "metadata": {}
    }
    """
    agent_role = body.get("agent", "CEO")
    message = body.get("message", "")
    metadata = body.get("metadata", {})

    if not message:
        raise HTTPException(400, "message is required")

    handler = get_a2a_handler()
    task = await handler.create_task(agent_role, message, metadata)
    return {"task": task.to_dict()}


@app.get('/a2a/tasks/{task_id}')
async def a2a_get_task(task_id: str):
    """Get status and results of an A2A task."""
    handler = get_a2a_handler()
    task = handler.get_task(task_id)
    if not task:
        raise HTTPException(404, f"Task '{task_id}' not found")
    return {"task": task.to_dict()}


@app.get('/a2a/tasks')
async def a2a_list_tasks():
    """List recent A2A tasks."""
    handler = get_a2a_handler()
    return {"tasks": handler.list_tasks()}




# ============================================================
# AUTH ENDPOINTS (Phase 2 - simple API key auth)
# ============================================================
@app.post('/auth/issue-key')
async def auth_issue_key(body: dict):
    customer_id = body.get("customer_id", "")
    label = body.get("label", "default")
    master = body.get("master_key", "")

    if master != os.getenv("SVOS_MASTER_KEY", ""):
        raise HTTPException(401, "invalid master key")
    if not customer_id:
        raise HTTPException(400, "customer_id required")

    issued = issue_api_key(customer_id=customer_id, label=label)
    return {"success": True, "issued": issued}


@app.get('/auth/ping')
async def auth_ping(request: Request):
    auth = getattr(request.state, "auth", None)
    return {"ok": True, "auth": auth or {"public": True}}


@app.get('/auth/keys')
async def auth_keys(body: dict):
    if body.get("master_key", "") != os.getenv("SVOS_MASTER_KEY", ""):
        raise HTTPException(401, "invalid master key")
    return {"keys": list_keys()}


# ============================================================
# ONBOARDING ENDPOINTS (Phase 2 - Step 2)
# ============================================================
@app.post('/onboard')
async def onboard(body: dict):
    """
    Full customer onboarding in one call.
    Body: {
      "customer_id": "cust_abc123",
      "email": "user@example.com",
      "plan_id": "starter",
      "company_name": "My AI Company",
      "company_description": "Digital marketing agency",
      "mission": "...", "vision": "...", "values": [...],
      "industry": "marketing", "country": "Saudi Arabia",
      "llm_provider": "anthropic", "llm_api_key": "sk-ant-...", "llm_model": "claude-haiku-4-5-20251001",
      "master_key": "..." (required)
    }
    """
    master = body.get("master_key", "")
    if master != os.getenv("SVOS_MASTER_KEY", ""):
        raise HTTPException(401, "invalid master key")

    customer_id = body.get("customer_id", "")
    email = body.get("email", "")
    if not customer_id or not email:
        raise HTTPException(400, "customer_id and email required")

    result = onboard_customer(
        customer_id=customer_id,
        email=email,
        plan_id=body.get("plan_id", "starter"),
        company_name=body.get("company_name", ""),
        company_description=body.get("company_description", ""),
        mission=body.get("mission", ""),
        vision=body.get("vision", ""),
        values=body.get("values"),
        industry=body.get("industry", "general"),
        country=body.get("country", "Saudi Arabia"),
        risk_appetite=body.get("risk_appetite", "moderate"),
        payment_ref=body.get("payment_ref", ""),
        llm_provider=body.get("llm_provider", ""),
        llm_api_key=body.get("llm_api_key", ""),
        llm_model=body.get("llm_model", ""),
        ollama_base_url=body.get("ollama_base_url", "http://localhost:11434"),
    )
    return result


@app.post('/onboard/status')
async def onboard_status(body: dict):
    """Check onboarding status for a customer."""
    customer_id = body.get("customer_id", "")
    if not customer_id:
        raise HTTPException(400, "customer_id required")
    return get_onboarding_status(customer_id)


# ============================================================
# LLM CONFIGURATION ENDPOINTS (BYOK - Bring Your Own Key)
# ============================================================
from core.tenant_llm_config import (
    save_llm_config, load_llm_config, get_llm_status,
    delete_llm_config, list_providers as list_llm_providers,
)


@app.get('/llm/providers')
async def llm_providers():
    """List available LLM providers with details for UI."""
    return {"success": True, "providers": list_llm_providers()}


@app.post('/my/llm/configure')
async def my_llm_configure(body: dict, request: Request):
    """
    Set or update LLM provider and API key for authenticated customer.
    Body: {"provider": "anthropic", "api_key": "sk-ant-...", "model": "claude-haiku-4-5-20251001"}
    """
    auth = getattr(request.state, "auth", {})
    cid = auth.get("customer_id", "")
    if not cid:
        raise HTTPException(401, "auth required")

    provider = body.get("provider", "")
    if not provider:
        raise HTTPException(400, "provider is required")

    result = save_llm_config(
        customer_id=cid,
        provider=provider,
        api_key=body.get("api_key", ""),
        model=body.get("model", ""),
        ollama_base_url=body.get("ollama_base_url", "http://localhost:11434"),
    )
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Failed to save LLM config"))
    return result


@app.get('/my/llm/status')
async def my_llm_status(request: Request):
    """Check LLM configuration status for authenticated customer."""
    auth = getattr(request.state, "auth", {})
    cid = auth.get("customer_id", "")
    if not cid:
        raise HTTPException(401, "auth required")
    return get_llm_status(cid)


@app.delete('/my/llm/configure')
async def my_llm_delete(request: Request):
    """Remove LLM config (to reconfigure)."""
    auth = getattr(request.state, "auth", {})
    cid = auth.get("customer_id", "")
    if not cid:
        raise HTTPException(401, "auth required")
    return delete_llm_config(cid)


@app.post('/my/llm/test')
async def my_llm_test(request: Request):
    """Test the customer's LLM configuration with a simple prompt."""
    auth = getattr(request.state, "auth", {})
    cid = auth.get("customer_id", "")
    if not cid:
        raise HTTPException(401, "auth required")

    config = load_llm_config(cid)
    if not config:
        return {"success": False, "error": "No LLM configured. Use /my/llm/configure first."}

    try:
        llm = LLMProvider(tenant_config=config)
        response = await llm.complete(
            system_prompt="You are a helpful assistant. Reply in 1 sentence.",
            user_message="Say hello and confirm you are working.",
            max_tokens=100,
        )
        return {
            "success": True,
            "provider": config["provider"],
            "model": config.get("model", ""),
            "response": response,
        }
    except Exception as e:
        return {
            "success": False,
            "provider": config["provider"],
            "error": str(e),
            "hint": "Check your API key and try again.",
        }


# ============================================================
# ACTIVITY LOG ENDPOINTS
# ============================================================
@app.get('/dashboard/activity')
async def dashboard_activity(request: Request):
    """Get recent activity log for the authenticated customer."""
    auth = getattr(request.state, "auth", {})
    customer_id = auth.get("customer_id", "")
    if not customer_id:
        raise HTTPException(401, "authentication required")

    is_master = auth.get("is_master", False)
    limit = 50

    if is_master:
        # master can query any customer
        from fastapi import Query
        # default to showing master's own activity
        pass

    activity = get_recent_activity(customer_id, limit=limit)
    summary = get_activity_summary(customer_id)
    return {
        "success": True,
        "customer_id": customer_id,
        "summary": summary,
        "recent": activity,
    }


# ============================================================
# TENANT-AWARE CRM ENDPOINTS
# ============================================================
@app.post('/my/crm/leads')
async def my_crm_add_lead(body: dict, request: Request):
    """Add a lead to MY CRM (tenant-isolated)."""
    auth = getattr(request.state, "auth", {})
    cid = auth.get("customer_id", "")
    if not cid:
        raise HTTPException(401, "auth required")

    from engines.crm_engine import CRMEngine
    crm = CRMEngine(data_dir=str(get_tenant_crm_dir(cid)))
    return crm.add_lead(
        name=body.get("name", ""),
        email=body.get("email", ""),
        phone=body.get("phone", ""),
        company=body.get("company", ""),
        source=body.get("source", "manual"),
        notes=body.get("notes", ""),
        value_estimate=body.get("value_estimate", ""),
    )


@app.get('/my/crm/pipeline')
async def my_crm_pipeline(request: Request):
    """Get MY CRM pipeline (tenant-isolated)."""
    auth = getattr(request.state, "auth", {})
    cid = auth.get("customer_id", "")
    if not cid:
        raise HTTPException(401, "auth required")

    from engines.crm_engine import CRMEngine
    crm = CRMEngine(data_dir=str(get_tenant_crm_dir(cid)))
    return crm.get_pipeline()


# ============================================================
# TENANT-AWARE DNA ENDPOINTS
# ============================================================
@app.get('/my/dna/profile')
async def my_dna_profile(request: Request):
    """Get MY company DNA (tenant-isolated)."""
    auth = getattr(request.state, "auth", {})
    cid = auth.get("customer_id", "")
    if not cid:
        raise HTTPException(401, "auth required")

    from engines.company_dna import CompanyDNA
    dna = CompanyDNA(company_id=cid, data_dir=str(get_tenant_dna_dir(cid)))
    return dna.get_dna()


@app.post('/my/dna/evolve')
async def my_dna_evolve(request: Request):
    """Evolve MY company DNA (tenant-isolated)."""
    auth = getattr(request.state, "auth", {})
    cid = auth.get("customer_id", "")
    if not cid:
        raise HTTPException(401, "auth required")

    from engines.company_dna import CompanyDNA
    dna = CompanyDNA(company_id=cid, data_dir=str(get_tenant_dna_dir(cid)))
    return await dna.evolve()


# ============================================================
# ONBOARDING UI
# ============================================================
@app.get('/onboard')
async def onboard_page():
    """Serve the onboarding wizard UI."""
    p = Path('web/onboard.html')
    if p.exists():
        return FileResponse(str(p))
    return {'error': 'Onboarding page not found at web/onboard.html'}


# ============================================================
# COMPANY STATE ENDPOINTS (Phase 1 — The Company Remembers)
# ============================================================
from engines.company_state import get_company_state


@app.get('/my/company/state')
async def my_company_state(request: Request):
    """Get full company state (raw JSON for developers/integrations)."""
    auth = getattr(request.state, "auth", {})
    cid = auth.get("customer_id", "")
    if not cid:
        raise HTTPException(401, "auth required")
    state = get_company_state(cid)
    return {"success": True, "state": state.state}


@app.get('/my/company/summary')
async def my_company_summary(request: Request):
    """Get executive summary + KPIs (for dashboard display)."""
    auth = getattr(request.state, "auth", {})
    cid = auth.get("customer_id", "")
    if not cid:
        raise HTTPException(401, "auth required")

    state = get_company_state(cid)
    s = state.state
    recent = s.get("recent_cycles", [])
    pending = state.get_pending_approvals()

    return {
        "success": True,
        "company_name": s.get("identity", {}).get("company_name", ""),
        "phase": s.get("current_status", {}).get("phase", "startup"),
        "health": s.get("current_status", {}).get("health", "unknown"),
        "cycles_completed": s.get("current_status", {}).get("cycles_completed", 0),
        "kpis": s.get("kpis", {}),
        "top_priorities": s.get("current_status", {}).get("top_priorities", []),
        "last_narrative": recent[-1].get("summary", "") if recent else "",
        "pending_approvals": len(pending),
        "pending_actions": pending,
    }


@app.post('/my/company/priorities')
async def my_company_priorities(body: dict, request: Request):
    """Update company priorities."""
    auth = getattr(request.state, "auth", {})
    cid = auth.get("customer_id", "")
    if not cid:
        raise HTTPException(401, "auth required")

    priorities = body.get("priorities", [])
    if not priorities:
        raise HTTPException(400, "priorities list required")

    state = get_company_state(cid)
    state.update_status(top_priorities=priorities[:3])
    return {"success": True, "priorities": priorities[:3]}


@app.post('/my/company/approve')
async def my_company_approve(body: dict, request: Request):
    """Approve or reject a pending action."""
    auth = getattr(request.state, "auth", {})
    cid = auth.get("customer_id", "")
    if not cid:
        raise HTTPException(401, "auth required")

    approval_id = body.get("approval_id", "")
    approved = body.get("approved", False)

    if not approval_id:
        raise HTTPException(400, "approval_id required")

    state = get_company_state(cid)
    result = state.resolve_approval(approval_id, approved)
    if not result.get("resolved"):
        raise HTTPException(404, result.get("reason", "not found"))

    # If approved, execute the action
    if approved and result.get("action"):
        action = result["action"]
        try:
            tool_name = action.get("tool", "")
            params = action.get("params", {})
            executed = tool_registry.execute(tool_name, "CEO", "execute", **params)
            result["execution"] = executed
            state.record_execution(tool_name)
        except Exception as e:
            result["execution_error"] = str(e)

    return {"success": True, "result": result}


@app.get('/my/company/approvals')
async def my_company_approvals(request: Request):
    """List all pending approvals."""
    auth = getattr(request.state, "auth", {})
    cid = auth.get("customer_id", "")
    if not cid:
        raise HTTPException(401, "auth required")

    state = get_company_state(cid)
    return {"success": True, "pending": state.get_pending_approvals()}


@app.post('/my/company/controls')
async def my_company_controls(body: dict, request: Request):
    """Update execution controls (limits, auto-execute, require-approval lists)."""
    auth = getattr(request.state, "auth", {})
    cid = auth.get("customer_id", "")
    if not cid:
        raise HTTPException(401, "auth required")

    state = get_company_state(cid)
    controls = state.state.get("controls", {})

    if "execution_limits" in body:
        controls["execution_limits"].update(body["execution_limits"])
    if "auto_execute" in body:
        controls["auto_execute"] = body["auto_execute"]
    if "require_approval" in body:
        controls["require_approval"] = body["require_approval"]

    state.save()
    return {"success": True, "controls": controls}



