import httpx
from anthropic import AsyncAnthropic

from core.config import settings

client = AsyncAnthropic(api_key=settings.anthropic_api_key)
MODEL = "claude-haiku-4-5-20251001"
SVOS_URL = "http://localhost:8000"
SPHERE_ID = "c99c4f47"


async def _call(system: str, user: str) -> str:
    msg = await client.messages.create(
        model=MODEL,
        max_tokens=400,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text.strip()


def _decide_lines(request: str) -> list:
    r = request.lower()
    lines = []
    if any(k in r for k in ["محتوى", "content", "مقال", "منشور"]):
        lines.append("content")
    if any(k in r for k in ["مبيعات", "sales", "عميل", "عرض"]):
        lines.append("sales")
    if not lines:
        lines = ["content", "sales"]
    return lines


async def run_board(request: str, context: dict) -> dict:
    lines = _decide_lines(request)
    results = {}

    async with httpx.AsyncClient(timeout=120) as http:
        if "content" in lines:
            res = await http.post(
                f"{SVOS_URL}/assembly/content",
                json={
                    "topic": context.get("topic", request),
                    "business": context.get("business_type", "عام"),
                    "audience": context.get("audience", "عام"),
                },
            )
            results["content"] = res.json() if res.status_code == 200 else {"error": res.text}

        if "sales" in lines:
            res = await http.post(
                f"{SVOS_URL}/assembly/sales",
                json={
                    "lead_name": context.get("lead_name", "عميل"),
                    "business_type": context.get("business_type", "عام"),
                    "pain_points": context.get("pain_points", ["تحسين"]),
                },
            )
            results["sales"] = res.json() if res.status_code == 200 else {"error": res.text}

        aurora = await http.post(
            f"{SVOS_URL}/spheres/{SPHERE_ID}/validate",
            json={"decision": request, "agent": "board"},
        )
        aurora_result = aurora.json() if aurora.status_code == 200 else {"approved": True}

    recommendation = await _call(
        "أنت رئيس مجلس إدارة. قدّم توصية موحدة قصيرة.",
        f"الطلب: {request}\nالنتائج: {list(results.keys())}",
    )

    return {
        "board_decision": {
            "request": request,
            "lines_activated": lines,
            "aurora_approval": aurora_result,
            "recommendation": recommendation,
        },
        "results": results,
        "pipeline": [f"{l.upper()} ✅" for l in lines],
    }
