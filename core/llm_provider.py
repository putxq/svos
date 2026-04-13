import asyncio
import json
from core.json_parser import parse_llm_json
import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Any

import httpx
from anthropic import AsyncAnthropic

try:
    from core.config import settings
except Exception:
    settings = None

logger = logging.getLogger("svos.llm_provider")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# =====================================================================
# SVOS LLM Provider — حرية كاملة للمستخدم
# الافتراضي: Claude (الموصى به)
# مدعوم: OpenAI, Gemini, Ollama, أو أي نموذج مستقبلي
# =====================================================================
SUPPORTED_PROVIDERS = {
    "anthropic": "Claude by Anthropic (recommended)",
    "claude": "Claude by Anthropic (recommended)",
    "openai": "GPT by OpenAI",
    "gpt": "GPT by OpenAI",
    "gemini": "Gemini by Google",
    "google": "Gemini by Google",
    "ollama": "Local models via Ollama",
}


class LLMAdapter(ABC):
    name: str = "base"

    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        raise NotImplementedError

    async def complete_with_tools(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[dict[str, Any]],
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        text = await self.complete(
            system_prompt,
            user_message,
            temperature=temperature,
            max_tokens=2048,
        )
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
        raw = await self.complete(
            system_prompt,
            prompt,
            temperature=temperature,
            max_tokens=2048,
        )
        try:
            parsed = parse_llm_json(raw)
            if parsed is None:
                raise ValueError(f'Failed to parse LLM response as JSON: {raw[:200]}')
            return parsed
        except Exception:
            return {"raw": raw, "_parse_error": True}


# ----- Anthropic (Claude) — الافتراضي والموصى به -----
class AnthropicAdapter(LLMAdapter):
    name = "anthropic"

    def __init__(self, api_key: str | None, model: str = "claude-haiku-4-5-20251001"):
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is missing")
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
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
                tool_calls.append({
                    "id": getattr(block, "id", None),
                    "name": getattr(block, "name", None),
                    "input": getattr(block, "input", None),
                })
        return {"text": "\n".join(text_parts).strip(), "tool_calls": tool_calls}


# ----- OpenAI (GPT) -----
class OpenAIAdapter(LLMAdapter):
    name = "openai"

    def __init__(self, api_key: str | None, model: str = "gpt-4o-mini"):
        if not api_key:
            raise ValueError(
                "\n╔══════════════════════════════════════════════════╗\n"
                "║ OPENAI_API_KEY is missing!                     ║\n"
                "║ Get your key: https://platform.openai.com      ║\n"
                "║ Add to .env: OPENAI_API_KEY=sk-...             ║\n"
                "╚══════════════════════════════════════════════════╝"
            )
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.openai.com/v1/chat/completions"

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(self.base_url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"].strip()

    async def complete_with_tools(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[dict[str, Any]],
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        # Convert Anthropic tool format to OpenAI format
        openai_tools = []
        for tool in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool.get("name", ""),
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {}),
                },
            })

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "tools": openai_tools,
            "temperature": temperature,
            "max_tokens": 800,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(self.base_url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        choice = data["choices"][0]["message"]
        text = choice.get("content", "") or ""
        tool_calls = []
        for tc in choice.get("tool_calls", []):
            tool_calls.append({
                "id": tc.get("id"),
                "name": tc["function"]["name"],
                "input": json.loads(tc["function"].get("arguments", "{}")),
            })

        return {"text": text.strip(), "tool_calls": tool_calls}


# ----- Google (Gemini) -----
class GeminiAdapter(LLMAdapter):
    name = "gemini"

    def __init__(self, api_key: str | None, model: str = "gemini-2.0-flash"):
        if not api_key:
            raise ValueError(
                "\n╔══════════════════════════════════════════════════╗\n"
                "║ GEMINI_API_KEY is missing!                     ║\n"
                "║ Get your key: https://aistudio.google.com      ║\n"
                "║ Add to .env: GEMINI_API_KEY=AI...              ║\n"
                "╚══════════════════════════════════════════════════╝"
            )
        self.api_key = api_key
        self.model = model

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_message}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "").strip()
        return ""


# ----- Ollama (محلي) -----
class OllamaAdapter(LLMAdapter):
    name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2:3b"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        payload = {
            "model": self.model,
            "prompt": f"SYSTEM:\n{system_prompt}\n\nUSER:\n{user_message}",
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(f"{self.base_url}/api/generate", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return (data.get("response") or "").strip()
        except httpx.ConnectError:
            raise ConnectionError(
                f"\n╔══════════════════════════════════════════════════╗\n"
                f"║ Cannot connect to Ollama at {self.base_url} ║\n"
                f"║ Make sure Ollama is running: ollama serve     ║\n"
                f"║ Or switch to Claude: LLM_PROVIDER=anthropic   ║\n"
                f"╚══════════════════════════════════════════════════╝"
            )


# ----- Dry-Run Adapter (no API key needed) -----
class DryRunAdapter(LLMAdapter):
    name = "dry_run"

    async def complete(self, system_prompt, user_message, temperature=0.7, max_tokens=2048) -> str:
        return (
            '{"status":"dry_run","message":"Add ANTHROPIC_API_KEY to .env to enable real AI responses.",'
            '"action":"Configure API key at /dashboard"}'
        )


# =====================================================================
# LLMProvider — الموزع الذكي
# =====================================================================
class LLMProvider:
    """
    يقرأ LLM_PROVIDER من .env ويبني الـ adapter المناسب.
    الافتراضي: anthropic (Claude) — الأقوى والموصى به.
    المدعوم: anthropic, openai, gemini, ollama.
    المستخدم يختار بحرية — ما نفرض شيء.

    BYOK Mode: If a tenant has configured their own LLM key,
    we use it instead of the global key. SVOS is the car,
    the customer brings the fuel.
    """

    # Map aliases to canonical names
    PROVIDER_ALIASES = {
        "anthropic": "anthropic",
        "claude": "anthropic",
        "openai": "openai",
        "gpt": "openai",
        "gemini": "gemini",
        "google": "gemini",
        "ollama": "ollama",
        "local": "ollama",
    }

    def __init__(self, provider: str | None = None, tenant_config: dict | None = None):
        # ── BYOK: Try tenant config first ──
        if tenant_config is None and provider is None:
            try:
                from core.tenant_llm_config import load_llm_config
                from core.tenant import get_customer_id
                tenant_config = load_llm_config()

                # If there's an authenticated tenant but NO LLM config → block.
                # Global key is for system/scheduler only, not free rides.
                if tenant_config is None and get_customer_id():
                    raise ValueError(
                        "Please configure your AI provider. "
                        "Use POST /my/llm/configure to add your API key."
                    )
            except ValueError:
                raise  # re-raise our own error
            except Exception:
                tenant_config = None

        if tenant_config and tenant_config.get("provider"):
            # Customer's own key
            raw_name = tenant_config["provider"].lower().strip()
            self._tenant_config = tenant_config
            self._source = "tenant"
        else:
            # Global / env — only for system-level calls (scheduler, internal)
            raw_name = (provider or self._env("LLM_PROVIDER") or "anthropic").lower().strip()
            self._tenant_config = None
            self._source = "global"

        self.provider_name = self.PROVIDER_ALIASES.get(raw_name, raw_name)

        if self.provider_name not in ("anthropic", "openai", "gemini", "ollama"):
            supported = ", ".join(sorted(SUPPORTED_PROVIDERS.keys()))
            raise ValueError(
                f"Unknown LLM provider: '{raw_name}'\n"
                f"Supported: {supported}\n"
                f"Set LLM_PROVIDER in .env to one of these."
            )

        self.adapter = self._build_adapter()

        logger.info(
            json.dumps({
                "event": "llm_provider_init",
                "provider": self.provider_name,
                "adapter": self.adapter.name,
                "model": getattr(self.adapter, "model", "unknown"),
                "source": self._source,
            })
        )

    def _env(self, key: str) -> str | None:
        """Read from env vars first, then settings object."""
        v = os.getenv(key)
        if v:
            return v
        if settings is None:
            return None
        attr = key.lower()
        return getattr(settings, attr, None)

    def _build_adapter(self) -> LLMAdapter:
        p = self.provider_name
        tc = self._tenant_config  # None if using global

        if p == "anthropic":
            key = (tc or {}).get("api_key") or self._env("ANTHROPIC_API_KEY")
            if not key:
                logger.warning("ANTHROPIC_API_KEY not set — running in dry-run mode")
                return DryRunAdapter()
            return AnthropicAdapter(
                api_key=key,
                model=(tc or {}).get("model") or self._env("ANTHROPIC_MODEL") or "claude-haiku-4-5-20251001",
            )

        if p == "openai":
            return OpenAIAdapter(
                api_key=(tc or {}).get("api_key") or self._env("OPENAI_API_KEY"),
                model=(tc or {}).get("model") or self._env("OPENAI_MODEL") or "gpt-4o-mini",
            )

        if p == "gemini":
            return GeminiAdapter(
                api_key=(tc or {}).get("api_key") or self._env("GEMINI_API_KEY"),
                model=(tc or {}).get("model") or self._env("GEMINI_MODEL") or "gemini-2.0-flash",
            )

        if p == "ollama":
            return OllamaAdapter(
                base_url=(tc or {}).get("ollama_base_url") or self._env("OLLAMA_BASE_URL") or "http://localhost:11434",
                model=(tc or {}).get("model") or self._env("OLLAMA_MODEL") or "llama3.2:3b",
            )

        raise ValueError(f"No adapter for provider: {p}")

    def _estimate_cost_usd(self, output_text: str) -> float:
        chars = len(output_text or "")
        return round(chars * 0.0000005, 6)

    def _log(self, operation: str, started: float, output_text: str | None = None, error: str | None = None):
        elapsed_ms = round((time.time() - started) * 1000, 2)
        payload = {
            "event": "llm_call",
            "provider": self.provider_name,
            "adapter": self.adapter.name,
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
            lambda: self.adapter.complete_with_tools(system_prompt, user_message, tools, temperature=temperature),
            operation="complete_with_tools",
        )

    async def complete_structured(
        self,
        system_prompt: str,
        user_message: str,
        output_schema: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._with_retry(
            lambda: self.adapter.complete_structured(system_prompt, user_message, output_schema, temperature=0.2),
            operation="complete_structured",
        )

