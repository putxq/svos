import httpx

from core.config import settings
from core.exceptions import MCPError
from core.retry import async_retry


class MCPClient:
    def __init__(self):
        self.base_url = settings.mcp_base_url.rstrip("/")
        self.api_key = settings.mcp_api_key

    @async_retry(attempts=2)
    async def invoke(self, path: str, payload: dict) -> dict:
        if not self.base_url:
            raise MCPError("MCP_BASE_URL is not configured")

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
                resp = await client.post(f"{self.base_url}/{path.lstrip('/')}" , json=payload, headers=headers)
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            raise MCPError(f"MCP invoke failed: {exc}") from exc
