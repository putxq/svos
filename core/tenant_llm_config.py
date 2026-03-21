"""
SVOS Tenant LLM Config — BYOK (Bring Your Own Key).
Each customer provides their own LLM provider + API key.
SVOS is the car, the customer brings the fuel.

Storage: workspace/tenants/{customer_id}/llm_config.json
"""

import json
import logging
from pathlib import Path
from typing import Any

from core.tenant import get_tenant_dir, get_customer_id

logger = logging.getLogger("svos.tenant_llm")

# Valid providers
VALID_PROVIDERS = {"anthropic", "openai", "gemini", "ollama"}

# Default models per provider
DEFAULT_MODELS = {
    "anthropic": "claude-haiku-4-5-20251001",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.0-flash",
    "ollama": "llama3.2:3b",
}

# Provider display info (for onboarding UI)
PROVIDER_INFO = [
    {
        "id": "anthropic",
        "name": "Claude (Anthropic)",
        "name_ar": "كلود (Anthropic)",
        "models": ["claude-haiku-4-5-20251001", "claude-sonnet-4-20250514"],
        "default_model": "claude-haiku-4-5-20251001",
        "key_prefix": "sk-ant-",
        "get_key_url": "https://console.anthropic.com",
        "recommended": True,
    },
    {
        "id": "openai",
        "name": "GPT (OpenAI)",
        "name_ar": "جي بي تي (OpenAI)",
        "models": ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1-nano"],
        "default_model": "gpt-4o-mini",
        "key_prefix": "sk-",
        "get_key_url": "https://platform.openai.com/api-keys",
        "recommended": False,
    },
    {
        "id": "gemini",
        "name": "Gemini (Google)",
        "name_ar": "جيمناي (Google)",
        "models": ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-pro"],
        "default_model": "gemini-2.0-flash",
        "key_prefix": "AI",
        "get_key_url": "https://aistudio.google.com/apikey",
        "recommended": False,
    },
    {
        "id": "ollama",
        "name": "Ollama (Local)",
        "name_ar": "أولاما (محلي)",
        "models": ["llama3.2:3b", "llama3.1:8b", "mistral:7b", "qwen2.5:7b"],
        "default_model": "llama3.2:3b",
        "key_prefix": "",
        "get_key_url": "https://ollama.com",
        "recommended": False,
        "note": "Requires Ollama running locally — no API key needed",
    },
]


def _config_path(customer_id: str) -> Path:
    return get_tenant_dir(customer_id) / "llm_config.json"


def save_llm_config(
    customer_id: str,
    provider: str,
    api_key: str = "",
    model: str = "",
    ollama_base_url: str = "http://localhost:11434",
) -> dict:
    """Save LLM configuration for a tenant."""
    provider = provider.lower().strip()
    if provider not in VALID_PROVIDERS:
        return {"success": False, "error": f"Invalid provider: {provider}. Valid: {', '.join(VALID_PROVIDERS)}"}

    if provider != "ollama" and not api_key:
        return {"success": False, "error": f"API key is required for {provider}"}

    config = {
        "provider": provider,
        "api_key": api_key,
        "model": model or DEFAULT_MODELS.get(provider, ""),
        "ollama_base_url": ollama_base_url if provider == "ollama" else "",
    }

    path = _config_path(customer_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"LLM config saved for {customer_id}: provider={provider}, model={config['model']}")

    return {
        "success": True,
        "provider": provider,
        "model": config["model"],
        "has_key": bool(api_key),
    }


def load_llm_config(customer_id: str | None = None) -> dict | None:
    """Load LLM config for a tenant. Returns None if not configured."""
    cid = customer_id or get_customer_id()
    if not cid:
        return None

    path = _config_path(cid)
    if not path.exists():
        return None

    try:
        config = json.loads(path.read_text("utf-8"))
        if config.get("provider") and (config.get("api_key") or config.get("provider") == "ollama"):
            return config
        return None
    except Exception as e:
        logger.warning(f"Failed to load LLM config for {cid}: {e}")
        return None


def get_llm_status(customer_id: str) -> dict:
    """Check if LLM is configured for a tenant."""
    config = load_llm_config(customer_id)
    if not config:
        return {
            "configured": False,
            "provider": None,
            "model": None,
            "message": "No LLM configured — please add your API key",
        }

    return {
        "configured": True,
        "provider": config["provider"],
        "model": config.get("model", ""),
        "has_key": bool(config.get("api_key")),
    }


def delete_llm_config(customer_id: str) -> dict:
    """Remove LLM config (e.g., when customer wants to change provider)."""
    path = _config_path(customer_id)
    if path.exists():
        path.unlink()
        return {"deleted": True}
    return {"deleted": False, "reason": "no config found"}


def list_providers() -> list[dict]:
    """Return provider list for the onboarding UI."""
    return PROVIDER_INFO
