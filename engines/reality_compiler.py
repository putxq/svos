"""
Reality Compiler
فكرة → PRD + كود + صفحة هبوط + عقد + خطة إطلاق
"""
from anthropic import AsyncAnthropic

from core.config import settings

client = AsyncAnthropic(api_key=settings.anthropic_api_key)
MODEL = "claude-haiku-4-5-20251001"


async def _call(system: str, user: str) -> str:
    msg = await client.messages.create(
        model=MODEL,
        max_tokens=800,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text.strip()


async def compile_reality(idea: str, audience: str) -> dict:
    base = f"الفكرة: {idea}\nالجمهور: {audience}"
    prd = await _call("اكتب PRD تنفيذي مختصر.", base)
    code_plan = await _call("اعط مخطط كود MVP قابل للتنفيذ.", base)
    landing = await _call("اكتب صفحة هبوط تحويلية.", base)
    contract = await _call("اكتب بنود عقد خدمة أساسية.", base)
    launch = await _call("اكتب خطة إطلاق 14 يوم.", base)
    return {
        "engine": "Reality Compiler ✅",
        "prd": prd,
        "code_plan": code_plan,
        "landing_page": landing,
        "contract_outline": contract,
        "launch_plan": launch,
    }
