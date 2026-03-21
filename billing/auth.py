"""Simple API-key auth for SVOS customers."""

import hashlib
import json
import os
import secrets
import time
from pathlib import Path

AUTH_DIR = Path("workspace/auth")
AUTH_DIR.mkdir(parents=True, exist_ok=True)
AUTH_FILE = AUTH_DIR / "api_keys.json"


def _load() -> dict:
    if not AUTH_FILE.exists():
        return {"keys": {}}
    try:
        return json.loads(AUTH_FILE.read_text("utf-8"))
    except Exception:
        return {"keys": {}}


def _save(data: dict) -> None:
    AUTH_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def issue_api_key(customer_id: str, label: str = "default") -> dict:
    token = f"svos_{secrets.token_urlsafe(24)}"
    key_hash = _hash_key(token)
    data = _load()
    data.setdefault("keys", {})[key_hash] = {
        "customer_id": customer_id,
        "label": label,
        "created_at": time.time(),
        "active": True,
    }
    _save(data)
    return {
        "api_key": token,
        "customer_id": customer_id,
        "label": label,
    }


def verify_api_key(raw_key: str | None) -> dict:
    master = os.getenv("SVOS_MASTER_KEY", "").strip()
    if raw_key and master and secrets.compare_digest(raw_key, master):
        return {
            "ok": True,
            "is_master": True,
            "customer_id": "master",
            "source": "master",
        }

    if not raw_key:
        return {"ok": False, "reason": "missing_api_key"}

    data = _load()
    rec = data.get("keys", {}).get(_hash_key(raw_key))
    if not rec:
        return {"ok": False, "reason": "invalid_api_key"}
    if not rec.get("active", True):
        return {"ok": False, "reason": "inactive_api_key"}

    return {
        "ok": True,
        "is_master": False,
        "customer_id": rec.get("customer_id", "unknown"),
        "source": "customer",
        "label": rec.get("label", "default"),
    }


def list_keys() -> list[dict]:
    data = _load()
    out = []
    for _, v in data.get("keys", {}).items():
        out.append(v)
    return out
