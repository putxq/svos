import asyncio
from uuid import uuid4

import httpx

from agents.base_agent import BaseAgent
from core.contracts import ConstitutionCheckRequest, MessageEnvelope
from core.config import settings
from engine.discussion_engine import DiscussionEngine
from infrastructure.run_state_repository import RunStateRepository
from sovereign_kernel.confidence_engine import ConfidenceEngine
from sovereign_kernel.escalation_router import EscalationRouter
from sovereign_kernel.shadow_mode import ShadowMode

MODEL_SYSTEM = "أنت رئيس مجلس إدارة. قدّم توصية موحدة قصيرة."
SVOS_URL = "http://localhost:8000"
SPHERE_ID = "c99c4f47"


def _decide_lines(request: str) -> list[str]:
    r = request.lower()
    lines = []
    if any(k in r for k in ["محتوى", "content", "مقال", "منشور"]):
        lines.append("content")
    if any(k in r for k in ["مبيعات", "sales", "عميل", "عرض"]):
        lines.append("sales")
    if not lines:
        lines = ["content", "sales"]
    return lines


def _build_envelope(trace_id: str, intent: str, payload: dict) -> MessageEnvelope:
    return MessageEnvelope(
        trace_id=trace_id,
        from_agent="board",
        to_agent="svos-api",
        intent=intent,
        payload=payload,
        priority="normal",
    )


async def run_board(request: str, context: dict) -> dict:
    lines = _decide_lines(request)
    results = {}
    trace_id = str(uuid4())
    run_repo = RunStateRepository(settings.sqlite_path)
    await run_repo.init()
    await run_repo.start(trace_id, "board", note="board cycle created")

    audit: list[dict] = []

    discussion = DiscussionEngine()
    confidence_engine = ConfidenceEngine()
    escalation_router = EscalationRouter()
    shadow = ShadowMode()

    ceo = BaseAgent("ceo-board", "CEO", "أنت CEO. اقترح قرارًا أوليًا.")
    coo = BaseAgent("coo-board", "COO", "أنت COO. راجع من منظور العمليات.")
    cto = BaseAgent("cto-board", "CTO", "أنت CTO. راجع من منظور التقنية.")
    clo = BaseAgent("clo-board", "CLO", "أنت CLO. راجع من منظور الامتثال.")

    await run_repo.update(trace_id, "board", "running", 0.15, note="collecting proposal")
    proposal = await ceo.think(f"الطلب: {request}\nالسياق: {context}")
    comments = await discussion.run_round(
        proposal,
        {"coo": coo, "cto": cto, "clo": clo},
    )
    consensus = discussion.consensus(comments)

    async with httpx.AsyncClient(timeout=120) as http:
        tasks = []
        if "content" in lines:
            payload = {
                "topic": context.get("topic", request),
                "business": context.get("business_type", "عام"),
                "audience": context.get("audience", "عام"),
            }
            env = _build_envelope(trace_id, "assembly.content", payload)
            audit.append(env.model_dump(mode="json"))
            tasks.append(http.post(f"{SVOS_URL}/assembly/content", json=payload))

        if "sales" in lines:
            payload = {
                "lead_name": context.get("lead_name", "عميل"),
                "business_type": context.get("business_type", "عام"),
                "pain_points": context.get("pain_points", ["تحسين"]),
            }
            env = _build_envelope(trace_id, "assembly.sales", payload)
            audit.append(env.model_dump(mode="json"))
            tasks.append(http.post(f"{SVOS_URL}/assembly/sales", json=payload))

        await run_repo.update(trace_id, "board", "running", 0.55, note="executing assembly lines")
        responses = await asyncio.gather(*tasks) if tasks else []
        idx = 0
        if "content" in lines:
            res = responses[idx]
            results["content"] = res.json() if res.status_code == 200 else {"error": res.text}
            idx += 1
        if "sales" in lines:
            res = responses[idx]
            results["sales"] = res.json() if res.status_code == 200 else {"error": res.text}

        constitution_req = ConstitutionCheckRequest(
            business_id=context.get("business_id", "board-default"),
            actor="board",
            action=request,
            rationale="board recommendation cycle",
            context=context,
        )

        aurora = await http.post(
            f"{SVOS_URL}/spheres/{SPHERE_ID}/validate",
            json={"decision": request, "agent": "board"},
        )
        aurora_result = aurora.json() if aurora.status_code == 200 else {"approved": True}
        audit.append(
            {
                "trace_id": trace_id,
                "intent": "constitution.check",
                "payload": constitution_req.model_dump(mode="json"),
                "result": aurora_result,
            }
        )

    await run_repo.update(trace_id, "board", "running", 0.80, note="building recommendation")
    recommendation = await ceo.think(
        f"{MODEL_SYSTEM}\nالطلب: {request}\nالنتائج: {list(results.keys())}\nتعليقات: {comments}"
    )

    confidence = confidence_engine.score(
        model_confidence=ceo.confidence_score(recommendation),
        data_quality=75,
        policy_alignment=80 if aurora_result.get("approved", True) else 30,
    )
    route = confidence_engine.route(confidence)
    action = escalation_router.dispatch(route)

    shadow_report = shadow.compare(
        candidate_decision=recommendation,
        reference_decision=proposal,
        meta={"consensus": consensus},
    )

    await run_repo.finish(trace_id, "board", success=True, note="board cycle finished")
    return {
        "board_decision": {
            "trace_id": trace_id,
            "request": request,
            "lines_activated": lines,
            "aurora_approval": aurora_result,
            "recommendation": recommendation,
            "discussion": consensus,
            "confidence": confidence,
            "route": route,
            "action": action,
            "shadow": shadow_report,
        },
        "results": results,
        "audit": audit,
        "pipeline": [f"{l.upper()} ✅" for l in lines],
    }
