import asyncio
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Any

import httpx
from anthropic import AsyncAnthropic

try:
    from core.config import settings
except Exception:  # pragma: no cover
    settings = None


logger = logging.getLogger("svos.llm_provider")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


class LLMAdapter(ABC):
    name: str = "base"

    @abstractmethod
    async def complete(self, system_prompt: str, user_message: str, temperature: float = 0.7, max_tokens: int = 2048) -> str:
        raise NotImplementedError

    async def complete_with_tools(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[dict[str, Any]],
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        # Default fallback: no native tool use, returns text only.
        text = await self.complete(system_prompt, user_message, temperature=temperature, max_tokens=2048)
        return {"text": text, "tool_calls": []}

    async def complete_structured(
        self,
        system_prompt: str,
        user_message: str,
        output_schema: dict[str, Any],
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        schema_text = json.dumps(output_schema, ensure_ascii=False)
        prompt = (
            f"{user_message}\n\n"
            f"Return ONLY valid JSON matching this schema:\n{schema_text}"
        )
        raw = await self.complete(system_prompt, prompt, temperature=temperature, max_tokens=2048)
        try:
            return json.loads(raw)
        except Exception:
            return {"raw": raw, "_parse_error": True}


class AnthropicAdapter(LLMAdapter):
    name = "anthropic"

    def __init__(self, api_key: str | None, model: str = "claude-haiku-4-5-20251001"):
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY missing")
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model

    async def complete(self, system_prompt: str, user_message: str, temperature: float = 0.7, max_tokens: int = 2048) -> str:
        msg = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return msg.content[0].text.strip()

    async def complete_with_tools(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[dict[str, Any]],
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        msg = await self.client.messages.create(
            model=self.model,
            max_tokens=800,
            temperature=temperature,
            system=system_prompt,
            tools=tools,
            messages=[{"role": "user", "content": user_message}],
        )
        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        for block in msg.content:
            btype = getattr(block, "type", "")
            if btype == "text":
                text_parts.append(getattr(block, "text", ""))
            if btype == "tool_use":
                tool_calls.append(
                    {
                        "id": getattr(block, "id", None),
                        "name": getattr(block, "name", None),
                        "input": getattr(block, "input", None),
                    }
                )
        return {"text": "\n".join(text_parts).strip(), "tool_calls": tool_calls}


class OllamaAdapter(LLMAdapter):
    name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen3:7b"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def complete(self, system_prompt: str, user_message: str, temperature: float = 0.7, max_tokens: int = 2048) -> str:
        payload = {
            "model": self.model,
            "prompt": f"SYSTEM:\n{system_prompt}\n\nUSER:\n{user_message}",
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{self.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return (data.get("response") or "").strip()


class LLMProvider:
    def __init__(self, provider: str | None = None, adapters: dict[str, type[LLMAdapter]] | None = None):
        self.provider_name = (provider or self._from_settings("LLM_PROVIDER") or "anthropic").lower()
        self.adapters = adapters or {
            "anthropic": AnthropicAdapter,
            "claude": AnthropicAdapter,
            "ollama": OllamaAdapter,
        }
        self.adapter = self._build_adapter(self.provider_name)

    def _from_settings(self, key: str) -> str | None:
        # priority: process env -> settings object
        v = os.getenv(key)
        if v:
            return v
        if settings is None:
            return None
        key_l = key.lower()
        if key_l == "llm_provider":
            return getattr(settings, "llm_provider", None)
        if key_l == "anthropic_api_key":
            return getattr(settings, "anthropic_api_key", None)
        if key_l == "ollama_base_url":
            return getattr(settings, "ollama_base_url", None) or getattr(settings, "OLLAMA_BASE_URL", None)
        if key_l == "ollama_model":
            return getattr(settings, "ollama_model", None) or getattr(settings, "OLLAMA_MODEL", None)
        if key_l == "anthropic_model":
            return getattr(settings, "anthropic_model", None)
        return None

    def _build_adapter(self, provider_name: str) -> LLMAdapter:
        cls = self.adapters.get(provider_name)
        if cls is None:
            raise ValueError(f"Unsupported provider: {provider_name}")

        if cls is AnthropicAdapter:
            return cls(
                api_key=self._from_settings("ANTHROPIC_API_KEY"),
                model=self._from_settings("ANTHROPIC_MODEL") or "claude-haiku-4-5-20251001",
            )
        if cls is OllamaAdapter:
            return cls(
                base_url=self._from_settings("OLLAMA_BASE_URL") or "http://localhost:11434",
                model=self._from_settings("OLLAMA_MODEL") or "qwen3:7b",
            )
        return cls()

    def _estimate_cost_usd(self, output_text: str) -> float:
        # rough placeholder for ops observability only
        chars = len(output_text or "")
        return round(chars * 0.0000005, 6)

    def _log(self, operation: str, started: float, output_text: str | None = None, error: str | None = None):
        elapsed_ms = round((time.time() - started) * 1000, 2)
        payload = {
            "event": "llm_call",
            "provider": self.provider_name,
            "adapter": getattr(self.adapter, "name", "unknown"),
            "operation": operation,
            "elapsed_ms": elapsed_ms,
            "estimated_cost_usd": self._estimate_cost_usd(output_text or ""),
            "ok": error is None,
            "error": error,
        }
        logger.info(json.dumps(payload, ensure_ascii=False))

    async def _with_retry(self, coro_factory, operation: str):
        retries = 3
        backoff = 0.7
        last_error = None
        for attempt in range(1, retries + 1):
            started = time.time()
            try:
                result = await coro_factory()
                out_text = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
                self._log(operation, started, output_text=out_text)
                return result
            except Exception as exc:
                last_error = exc
                self._log(operation, started, error=str(exc))
                if attempt < retries:
                    await asyncio.sleep(backoff)
                    backoff *= 2
        raise RuntimeError(f"LLM call failed after {retries} retries: {last_error}")

    async def complete(self, system_prompt: str, user_message: str, temperature: float = 0.7, max_tokens: int = 2048) -> str:
        return await self._with_retry(
            lambda: self.adapter.complete(system_prompt, user_message, temperature=temperature, max_tokens=max_tokens),
            operation="complete",
        )

    async def complete_with_tools(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[dict[str, Any]],
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        return await self._with_retry(
            lambda: self.adapter.complete_with_tools(
                system_prompt,
                user_message,
                tools,
                temperature=temperature,
            ),
            operation="complete_with_tools",
        )

    async def complete_structured(
        self,
        system_prompt: str,
        user_message: str,
        output_schema: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._with_retry(
            lambda: self.adapter.complete_structured(
                system_prompt,
                user_message,
                output_schema,
                temperature=0.2,
            ),
            operation="complete_structured",
        )
