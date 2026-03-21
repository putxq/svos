import logging
from typing import Optional

logger = logging.getLogger("svos.tool_registry")


class ToolRegistry:
    """
    Central registry that maps tools to agents by role.
    Each tool declares allowed_roles.
    Agents can only use tools matching their role.
    """

    def __init__(self):
        self._tools = {}
        self._role_map = {}
        logger.info("ToolRegistry initialized")

    def register(self, tool) -> None:
        name = getattr(tool, "name", tool.__class__.__name__)
        allowed = getattr(tool, "allowed_roles", [])

        self._tools[name] = {
            "instance": tool,
            "allowed_roles": allowed,
            "description": getattr(tool, "description", ""),
        }

        for role in allowed:
            if role not in self._role_map:
                self._role_map[role] = []
            self._role_map[role].append(name)

        logger.info(f"Registered tool '{name}' for roles: {allowed}")

    def get_tool(self, tool_name: str, agent_role: str) -> Optional[object]:
        entry = self._tools.get(tool_name)
        if not entry:
            logger.warning(f"Tool '{tool_name}' not found in registry")
            return None

        if agent_role not in entry["allowed_roles"]:
            logger.warning(
                f"Agent role '{agent_role}' denied access to tool '{tool_name}'. "
                f"Allowed: {entry['allowed_roles']}"
            )
            return None

        return entry["instance"]

    def get_tools_for_role(self, role: str) -> dict:
        tool_names = self._role_map.get(role, [])
        return {
            name: {
                "description": self._tools[name]["description"],
                "available": True,
            }
            for name in tool_names
        }

    def list_all(self) -> dict:
        return {
            name: {
                "allowed_roles": info["allowed_roles"],
                "description": info["description"],
            }
            for name, info in self._tools.items()
        }

    def execute(self, tool_name: str, agent_role: str, method: str, **kwargs) -> dict:
        tool = self.get_tool(tool_name, agent_role)
        if tool is None:
            return {
                "status": "denied",
                "reason": f"Tool '{tool_name}' not available for role '{agent_role}'",
            }

        fn = getattr(tool, method, None)
        if fn is None:
            return {
                "status": "error",
                "reason": f"Method '{method}' not found on tool '{tool_name}'",
            }

        try:
            result = fn(**kwargs)
            logger.info(f"Tool '{tool_name}.{method}' executed by '{agent_role}' -> {result.get('status', 'ok')}")
            return result
        except Exception as e:
            logger.error(f"Tool '{tool_name}.{method}' execution failed: {e}")
            return {"status": "error", "error": str(e)}



def build_registry() -> ToolRegistry:
    from tools.whatsapp_tool import WhatsAppTool
    from tools.email_tool import EmailTool
    from tools.landing_page_tool import LandingPageTool
    from tools.social_tool import SocialPostTool

    registry = ToolRegistry()
    registry.register(WhatsAppTool())
    registry.register(EmailTool())
    registry.register(LandingPageTool())
    registry.register(SocialPostTool())

    logger.info(f"Registry built with {len(registry._tools)} tools")
    return registry
