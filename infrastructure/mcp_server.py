"""
MCP Tool Server - Exposes SVOS tools as MCP-compatible tools.
Follows the Model Context Protocol specification.
Any MCP client (Claude Desktop, Cursor, etc.) can discover and use SVOS tools.
"""

import logging

logger = logging.getLogger("svos.mcp.server")


class MCPToolDefinition:
    """Represents a single tool in MCP format."""

    def __init__(self, name: str, description: str, input_schema: dict, handler):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.handler = handler

    def to_mcp_format(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": self.input_schema.get("properties", {}),
                "required": self.input_schema.get("required", []),
            },
        }


class MCPToolServer:
    """
    Serves SVOS tools via MCP protocol.
    Bridges ToolRegistry -> MCP format.
    """

    def __init__(self):
        self._tools: dict[str, MCPToolDefinition] = {}
        self._initialized = False
        logger.info("MCPToolServer created")

    def register_tool(self, name: str, description: str, input_schema: dict, handler) -> None:
        self._tools[name] = MCPToolDefinition(name, description, input_schema, handler)
        logger.info(f"MCP tool registered: {name}")

    def list_tools(self) -> list[dict]:
        return [t.to_mcp_format() for t in self._tools.values()]

    async def call_tool(self, name: str, arguments: dict) -> dict:
        tool = self._tools.get(name)
        if not tool:
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Tool '{name}' not found"}],
            }

        try:
            if callable(tool.handler):
                import asyncio

                if asyncio.iscoroutinefunction(tool.handler):
                    result = await tool.handler(**arguments)
                else:
                    result = tool.handler(**arguments)
            else:
                result = {"error": "handler not callable"}

            return {
                "isError": False,
                "content": [{"type": "text", "text": str(result)}],
                "structuredContent": result if isinstance(result, dict) else {"result": result},
            }
        except Exception as e:
            logger.error(f"MCP tool '{name}' execution error: {e}")
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
            }

    def handle_request(self, request: dict) -> dict:
        """Handle a JSON-RPC MCP request."""
        method = request.get("method", "")
        req_id = request.get("id", 1)
        params = request.get("params", {})

        if method == "initialize":
            return self._response(
                req_id,
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {
                        "name": "svos-mcp-server",
                        "version": "1.0.0",
                    },
                },
            )
        elif method == "tools/list":
            return self._response(req_id, {"tools": self.list_tools()})
        elif method == "tools/call":
            import asyncio

            name = params.get("name", "")
            arguments = params.get("arguments", {})
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = pool.submit(asyncio.run, self.call_tool(name, arguments)).result()
            else:
                result = asyncio.run(self.call_tool(name, arguments))
            return self._response(req_id, result)

        return self._error(req_id, -32601, f"Method not found: {method}")

    def _response(self, req_id, result):
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    def _error(self, req_id, code, message):
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def build_mcp_server() -> MCPToolServer:
    """Build MCP server with all SVOS tools registered."""
    from tool_registry import build_registry

    server = MCPToolServer()
    registry = build_registry()

    server.register_tool(
        name="svos_whatsapp_send",
        description="Send a WhatsApp message to a phone number via SVOS",
        input_schema={
            "properties": {
                "to": {"type": "string", "description": "Phone number with country code, e.g. +966501234567"},
                "body": {"type": "string", "description": "Message text to send"},
            },
            "required": ["to", "body"],
        },
        handler=lambda to, body: registry.execute("whatsapp", "CMO", "send", to=to, body=body),
    )

    server.register_tool(
        name="svos_email_send",
        description="Send an email with subject and body via SVOS",
        input_schema={
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Email body text"},
            },
            "required": ["to", "subject", "body"],
        },
        handler=lambda to, subject, body: registry.execute("email", "CMO", "send", to=to, subject=subject, body=body),
    )

    server.register_tool(
        name="svos_landing_page_generate",
        description="Generate an HTML landing page for a marketing campaign",
        input_schema={
            "properties": {
                "title": {"type": "string", "description": "Page title"},
                "headline": {"type": "string", "description": "Main headline"},
                "sub_headline": {"type": "string", "description": "Sub-headline text"},
                "lang": {"type": "string", "description": "Language: 'ar' or 'en'", "default": "ar"},
            },
            "required": ["title", "headline"],
        },
        handler=lambda title, headline, sub_headline="", lang="ar": registry.execute(
            "landing_page", "CMO", "generate", title=title, headline=headline, sub_headline=sub_headline, lang=lang
        ),
    )

    server.register_tool(
        name="svos_social_post",
        description="Post content to social media platforms via SVOS",
        input_schema={
            "properties": {
                "content": {"type": "string", "description": "Post content text"},
                "platform": {"type": "string", "description": "Platform: 'twitter'", "default": "twitter"},
            },
            "required": ["content"],
        },
        handler=lambda content, platform="twitter": registry.execute(
            "social_post", "CMO", "post", content=content, platform=platform
        ),
    )

    logger.info(f"MCP server built with {len(server._tools)} tools")
    return server
