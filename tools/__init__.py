from tools.web_search import WebSearchTool
from tools.email_tool import EmailTool
from tools.file_tool import FileTool
from tools.tool_registry import ToolRegistry


def create_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(WebSearchTool())
    registry.register(EmailTool())
    registry.register(FileTool())
    return registry
