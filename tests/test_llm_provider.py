import unittest

from core.llm_provider import LLMAdapter, LLMProvider


class FakeAdapter(LLMAdapter):
    name = "fake"

    async def complete(self, system_prompt: str, user_message: str, temperature: float = 0.7) -> str:
        return f"ok:{user_message}"

    async def complete_with_tools(self, system_prompt, user_message, tools, temperature=0.7):
        return {"text": "ok-tools", "tool_calls": [{"name": "demo"}]}

    async def complete_structured(self, system_prompt, user_message, output_schema, temperature=0.2):
        return {"ok": True, "schema_keys": list(output_schema.keys())}


class LLMProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_complete(self):
        provider = LLMProvider(provider="fake", adapters={"fake": FakeAdapter})
        out = await provider.complete("sys", "hello")
        self.assertTrue(out.startswith("ok:"))

    async def test_complete_with_tools(self):
        provider = LLMProvider(provider="fake", adapters={"fake": FakeAdapter})
        out = await provider.complete_with_tools("sys", "hello", tools=[])
        self.assertIn("tool_calls", out)

    async def test_complete_structured(self):
        provider = LLMProvider(provider="fake", adapters={"fake": FakeAdapter})
        out = await provider.complete_structured("sys", "hello", output_schema={"a": "int"})
        self.assertEqual(out.get("ok"), True)


if __name__ == "__main__":
    unittest.main()
