"""
SVOS Activity Log — structured audit trail.
Records every API call: who, what, when, result.
Stored per-tenant in JSON Lines format for simplicity.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("svos.activity")

LOG_DIR = Path("workspace/activity_logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)


def _log_file(customer_id: str) -> Path:
    if not customer_id:
        return LOG_DIR / "anonymous.jsonl"
    return LOG_DIR / f"{customer_id}.jsonl"


def log_activity(
    customer_id: str,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float = 0,
    detail: str = "",
):
    """Append one log line per API call."""
    entry = {
        "ts": datetime.utcnow().isoformat(),
        "customer_id": customer_id or "anonymous",
        "method": method,
        "path": path,
        "status": status_code,
        "duration_ms": round(duration_ms, 1),
        "detail": detail[:500],
    }

    try:
        with open(_log_file(customer_id), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"Failed to write activity log: {e}")


def get_recent_activity(customer_id: str, limit: int = 50) -> list[dict]:
    """Read last N activity entries for a customer."""
    path = _log_file(customer_id)
    if not path.exists():
        return []

    lines = path.read_text("utf-8").strip().split("\n")
    entries = []
    for line in lines[-limit:]:
        try:
            entries.append(json.loads(line))
        except Exception:
            pass
    return list(reversed(entries))  # newest first


def get_activity_summary(customer_id: str) -> dict:
    """Quick summary: total calls, last active, top endpoints."""
    entries = get_recent_activity(customer_id, limit=500)
    if not entries:
        return {"total_calls": 0, "last_active": None, "top_endpoints": []}

    from collections import Counter
    endpoints = Counter(e["path"] for e in entries)

    return {
        "total_calls": len(entries),
        "last_active": entries[0]["ts"] if entries else None,
        "top_endpoints": endpoints.most_common(5),
        "error_count": sum(1 for e in entries if e.get("status", 200) >= 400),
    }
