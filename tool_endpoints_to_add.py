# ===== TOOL EXECUTION ENDPOINTS =====
# Add this block to main.py (paste at the end, before the final if name block)

from tool_registry import build_registry

# Initialize registry once at startup
tool_registry = build_registry()


@app.get("/tools/list")
async def list_tools():
    """List all registered tools and their allowed roles."""
    return {"tools": tool_registry.list_all()}


@app.get("/tools/for-role/{role}")
async def tools_for_role(role: str):
    """List tools available for a specific agent role."""
    return {"role": role, "tools": tool_registry.get_tools_for_role(role)}


@app.post("/tools/execute")
async def execute_tool(request: dict):
    """
    Execute a tool action.

    Body:
    {
      "tool": "whatsapp",
      "agent_role": "CMO",
      "method": "send",
      "params": {"to": "+966...", "body": "Hello"}
    }
    """
    tool_name = request.get("tool", "")
    agent_role = request.get("agent_role", "")
    method = request.get("method", "")
    params = request.get("params", {})if not all([tool_name, agent_role, method]):
        return {"status": "error", "message": "Required: tool, agent_role, method"}

    result = tool_registry.execute(tool_name, agent_role, method, **params)
    return result


@app.post("/tools/whatsapp/send")
async def send_whatsapp(request: dict):
    """Quick endpoint: Send WhatsApp message."""
    result = tool_registry.execute(
        "whatsapp",
        request.get("agent_role", "CMO"),
        "send",
        to=request.get("to", ""),
        body=request.get("body", "")
    )
    return result


@app.post("/tools/email/send")
async def send_email(request: dict):
    """Quick endpoint: Send email."""
    result = tool_registry.execute(
        "email",
        request.get("agent_role", "CMO"),
        "send",
        to=request.get("to", ""),
        subject=request.get("subject", ""),
        body=request.get("body", ""),
        html=request.get("html", None)
    )
    return result


@app.post("/tools/landing-page/generate")
async def generate_landing_page(request: dict):
    """Quick endpoint: Generate a landing page."""
    result = tool_registry.execute(
        "landing_page",
        request.get("agent_role", "CMO"),
        "generate",
        title=request.get("title", ""),
        headline=request.get("headline", ""),
        sub_headline=request.get("sub_headline", ""),
        cta_text=request.get("cta_text", "Get Started"),
        cta_link=request.get("cta_link", "#"),
        features=request.get("features", None),
        lang=request.get("lang", "ar")
    )
    return result


@app.post("/tools/social/post")
async def social_post(request: dict):
    """Quick endpoint: Post to social media."""
    result = tool_registry.execute(
        "social_post",
        request.get("agent_role", "CMO"),
        "post",
        content=request.get("content", ""),
        platform=request.get("platform", "twitter")
    )
    return result
