class ToolRegistry:
    """سجل كل الأدوات المتاحة — الوكيل يسأل ويحصل على الأداة"""

    def __init__(self):
        self._tools = {}

    def register(self, tool) -> None:
        """يسجل أداة جديدة"""
        self._tools[tool.name] = tool

    def get(self, name: str):
        """يجيب أداة باسمها"""
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        """قائمة كل الأدوات المتاحة — اسم + وصف"""
        return [
            {"name": t.name, "description": t.description}
            for t in self._tools.values()
        ]

    def get_tools_for_agent(self, agent_role: str) -> list:
        """يرجع الأدوات المسموحة لدور معين"""
        role_tools = {
            "CEO": ["web_search", "file_operations"],
            "CFO": ["file_operations"],
            "CMO": ["web_search", "send_email", "file_operations"],
            "COO": ["file_operations"],
            "CTO": ["web_search", "file_operations"],
            "CLO": ["web_search", "file_operations"],
            "CHRO": ["file_operations"],
            "Guardian": ["file_operations"],
            "Radar": ["web_search", "file_operations"],
        }
        allowed = role_tools.get(agent_role, ["file_operations"])
        return [self._tools[name] for name in allowed if name in self._tools]
