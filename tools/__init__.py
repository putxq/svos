from tools.web_search import WebSearchTool
from tools.file_tool import FileTool
from tools.tool_registry import ToolRegistry

from .whatsapp_tool import WhatsAppTool
from .email_tool import EmailTool
from .landing_page_tool import LandingPageTool
from .social_tool import SocialPostTool


def create_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(WebSearchTool())
    registry.register(FileTool())
    registry.register(EmailTool())
    registry.register(LandingPageTool())
    registry.register(WhatsAppTool())
    registry.register(SocialPostTool())
    return registry


__all__ = [
    "WhatsAppTool",
    "EmailTool",
    "LandingPageTool",
    "SocialPostTool",
    "create_default_registry",
]
