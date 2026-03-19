import unittest

from agents.base_agent import BaseAgent, ThinkResult
from core.llm_provider import LLMAdapter, LLMProvider


class FakeAdapter(LLMAdapter):
    name = "fake"

    async def complete(self, system_prompt: str, user_message: str, temperature: float = 0.7) -> str:
        return "ok"

    async def complete_with_tools(self, system_prompt, user_message, tools, temperature=0.7):
        return {"text": "ok", "tool_calls": []}

    async def complete_structured(self, system_prompt, user_message, output_schema, temperature=0.2):
        return {
            "plan": ["step1", "step2"],
            "confidence": 0.82,
            "reasoning": "clear",
            "needs_discussion": False,
            "needs_escalation": False,
        }


class BaseAgentTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        llm = LLMProvider(provider="fake", adapters={"fake": FakeAdapter})
        self.agent = BaseAgent(
            name="test-agent",
            role="CEO",
            department="strategy",
            autonomy_level=0.8,
            llm_provider=llm,
        )

    async def test_think(self):
        result = await self.agent.think("task", {"x": 1})
        self.assertIsInstance(result, ThinkResult)
        self.assertEqual(len(result.plan), 2)

    async def test_memory(self):
        await self.agent.remember("k", "v", "semantic")
        out = await self.agent.recall("k", "semantic")
        self.assertTrue(len(out) >= 1)

    async def test_spawn_and_dismiss(self):
        sid = await self.agent.spawn_sub_agent("analyst", "help")
        self.assertIn(sid, self.agent.sub_agents)
        await self.agent.dismiss_sub_agent(sid)
        self.assertEqual(self.agent.sub_agents[sid]["status"], "dismissed")


if __name__ == "__main__":
    unittest.main()
