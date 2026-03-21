"""
SVOS Company State — The Living Heart of Every Digital Company.

This is NOT a config file. This is the company's living memory.
Every cycle reads it, every cycle updates it.
Agents consume it for context. Decisions accumulate in it.

Storage: workspace/tenants/{customer_id}/company_state.json
Fallback: workspace/company_state.json (for legacy/system-level)

Schema versioned for safe migrations.
"""

import json
import logging
import time
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("svos.company_state")

CURRENT_SCHEMA_VERSION = "1.0"

# ── Maximum history sizes (prevent unbounded growth) ──
MAX_DECISIONS = 50
MAX_LESSONS = 30
MAX_PENDING_APPROVALS = 20
MAX_CYCLE_SNAPSHOTS = 10


def _default_state() -> dict:
    """Safe default state — used when file is missing or corrupted."""
    return {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "last_updated_at": datetime.utcnow().isoformat(),
        "created_at": datetime.utcnow().isoformat(),

        # ── Identity (from Blueprint, mostly stable) ──
        "identity": {
            "company_name": "",
            "industry": "general",
            "goal": "",
            "mission": "",
            "vision": "",
            "values": [],
            "domain_context": "",  # injected into every agent prompt
        },

        # ── Current Status (updated every cycle) ──
        "current_status": {
            "phase": "startup",  # startup | growth | stable | crisis
            "top_priorities": [],  # max 3
            "focus_area": "",
            "last_cycle": None,  # cycle number
            "last_cycle_at": None,
            "cycles_completed": 0,
            "health": "unknown",  # healthy | degraded | critical
        },

        # ── KPIs (domain-specific, tracked over time) ──
        "kpis": {
            "leads_total": 0,
            "leads_qualified": 0,
            "content_produced": 0,
            "landing_pages_created": 0,
            "emails_sent": 0,
            "decisions_made": 0,
            "successful_decisions": 0,
        },

        # ── Decisions History (accumulates, capped) ──
        "decisions": [],
        # Each: {"decision": str, "taken_at": str, "agent": str,
        #         "expected_outcome": str, "actual_outcome": null, "success": null}

        # ── Lessons Learned (accumulates, capped) ──
        "lessons": [],
        # Each: {"lesson": str, "learned_at": str, "category": str}

        # ── Controls (execution governance) ──
        "controls": {
            "execution_limits": {
                "emails_per_day": 5,
                "whatsapp_per_day": 3,
                "landing_pages_per_day": 3,
                "social_posts_per_day": 5,
            },
            "execution_today": {
                "emails": 0,
                "whatsapp": 0,
                "landing_pages": 0,
                "social_posts": 0,
                "date": "",
            },
            "auto_execute": ["content", "analysis", "market_scan", "report"],
            "require_approval": ["email", "whatsapp", "social_post"],
            "pending_approvals": [],
            # Each: {"id": str, "action": str, "tool": str, "params": dict,
            #         "created_at": str, "expires_at": str, "status": "pending"}
        },

        # ── Recent Cycle Snapshots (last N summaries for context) ──
        "recent_cycles": [],
        # Each: {"cycle": int, "summary": str, "actions_taken": int,
        #         "decisions_made": int, "at": str}
    }


class CompanyState:
    """Read, update, and persist the company state."""

    def __init__(self, state_path: str | Path | None = None, customer_id: str = ""):
        if state_path:
            self._path = Path(state_path)
        elif customer_id:
            from core.tenant import get_tenant_dir
            self._path = get_tenant_dir(customer_id) / "company_state.json"
        else:
            self._path = Path("workspace/company_state.json")

        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._state = self._load()

    def _load(self) -> dict:
        """Load state with safe fallback."""
        if not self._path.exists():
            logger.info(f"No company state found at {self._path}, creating default")
            state = _default_state()
            self._save(state)
            return state

        try:
            raw = self._path.read_text("utf-8")
            state = json.loads(raw)

            # Validate minimal structure
            if not isinstance(state, dict) or "schema_version" not in state:
                raise ValueError("Invalid state structure")

            # Merge with defaults (add any new fields from newer schema)
            default = _default_state()
            merged = self._deep_merge(default, state)
            merged["schema_version"] = CURRENT_SCHEMA_VERSION
            return merged

        except Exception as e:
            logger.warning(f"Company state corrupted at {self._path}: {e}. Using default.")
            # Backup corrupted file
            backup = self._path.with_suffix(".json.bak")
            try:
                self._path.rename(backup)
                logger.info(f"Corrupted state backed up to {backup}")
            except Exception:
                pass
            state = _default_state()
            self._save(state)
            return state

    def _save(self, state: dict | None = None):
        """Persist state to disk."""
        s = state or self._state
        s["last_updated_at"] = datetime.utcnow().isoformat()
        try:
            self._path.write_text(
                json.dumps(s, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error(f"Failed to save company state: {e}")

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Merge override into base, keeping new default fields."""
        result = deepcopy(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = deepcopy(value)
        return result

    # ── READ ──

    @property
    def state(self) -> dict:
        return self._state

    def get(self, dotpath: str, default: Any = None) -> Any:
        """Get nested value: get('controls.execution_limits.emails_per_day')"""
        keys = dotpath.split(".")
        val = self._state
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return default
            if val is None:
                return default
        return val

    def get_agent_context(self) -> str:
        """Build context string injected into every agent prompt."""
        s = self._state
        identity = s.get("identity", {})
        status = s.get("current_status", {})
        kpis = s.get("kpis", {})
        recent = s.get("recent_cycles", [])

        parts = []

        # Identity
        if identity.get("domain_context"):
            parts.append(identity["domain_context"])
        elif identity.get("company_name"):
            parts.append(
                f"Company: {identity['company_name']} | "
                f"Industry: {identity.get('industry', 'general')} | "
                f"Goal: {identity.get('goal', 'growth')}"
            )

        # Current priorities
        if status.get("top_priorities"):
            parts.append(f"Current priorities: {', '.join(status['top_priorities'][:3])}")

        # Phase
        if status.get("phase"):
            parts.append(f"Company phase: {status['phase']}")

        # Key KPIs
        active_kpis = {k: v for k, v in kpis.items() if v and v > 0}
        if active_kpis:
            kpi_str = ", ".join(f"{k}: {v}" for k, v in list(active_kpis.items())[:5])
            parts.append(f"Current KPIs: {kpi_str}")

        # Last decisions
        decisions = s.get("decisions", [])[-3:]
        if decisions:
            dec_str = "; ".join(d.get("decision", "")[:80] for d in decisions)
            parts.append(f"Recent decisions: {dec_str}")

        # Last lessons
        lessons = s.get("lessons", [])[-2:]
        if lessons:
            les_str = "; ".join(l.get("lesson", "")[:80] for l in lessons)
            parts.append(f"Lessons learned: {les_str}")

        # Last cycle summary
        if recent:
            last = recent[-1]
            parts.append(f"Last cycle summary: {last.get('summary', 'N/A')[:150]}")

        return "\n".join(parts) if parts else ""

    # ── WRITE ──

    def save(self):
        self._save()

    def update_identity(self, **kwargs):
        """Update identity fields from Blueprint or onboarding."""
        for k, v in kwargs.items():
            if k in self._state["identity"] and v:
                self._state["identity"][k] = v
        self._save()

    def update_status(self, **kwargs):
        """Update current status after a cycle."""
        for k, v in kwargs.items():
            if k in self._state["current_status"]:
                self._state["current_status"][k] = v
        self._save()

    def increment_kpi(self, kpi: str, amount: int = 1):
        if kpi in self._state["kpis"]:
            self._state["kpis"][kpi] = self._state["kpis"].get(kpi, 0) + amount
            self._save()

    def record_decision(self, decision: str, agent: str = "CEO",
                        expected_outcome: str = ""):
        entry = {
            "decision": decision[:300],
            "taken_at": datetime.utcnow().isoformat(),
            "agent": agent,
            "expected_outcome": expected_outcome[:200],
            "actual_outcome": None,
            "success": None,
        }
        self._state["decisions"].append(entry)
        # Cap size
        if len(self._state["decisions"]) > MAX_DECISIONS:
            self._state["decisions"] = self._state["decisions"][-MAX_DECISIONS:]
        self._state["kpis"]["decisions_made"] = self._state["kpis"].get("decisions_made", 0) + 1
        self._save()

    def evaluate_decision(self, index: int, actual_outcome: str, success: bool):
        """Fill in outcome for a past decision (weekly review)."""
        decisions = self._state["decisions"]
        if 0 <= index < len(decisions):
            decisions[index]["actual_outcome"] = actual_outcome[:200]
            decisions[index]["success"] = success
            if success:
                self._state["kpis"]["successful_decisions"] = \
                    self._state["kpis"].get("successful_decisions", 0) + 1
            self._save()

    def record_lesson(self, lesson: str, category: str = "general"):
        entry = {
            "lesson": lesson[:300],
            "learned_at": datetime.utcnow().isoformat(),
            "category": category,
        }
        self._state["lessons"].append(entry)
        if len(self._state["lessons"]) > MAX_LESSONS:
            self._state["lessons"] = self._state["lessons"][-MAX_LESSONS:]
        self._save()

    def add_cycle_snapshot(self, cycle: int, summary: str,
                           actions_taken: int = 0, decisions_made: int = 0):
        """Add a compact cycle snapshot for context loading."""
        entry = {
            "cycle": cycle,
            "summary": summary[:300],
            "actions_taken": actions_taken,
            "decisions_made": decisions_made,
            "at": datetime.utcnow().isoformat(),
        }
        self._state["recent_cycles"].append(entry)
        if len(self._state["recent_cycles"]) > MAX_CYCLE_SNAPSHOTS:
            self._state["recent_cycles"] = self._state["recent_cycles"][-MAX_CYCLE_SNAPSHOTS:]
        self._state["current_status"]["last_cycle"] = cycle
        self._state["current_status"]["last_cycle_at"] = entry["at"]
        self._state["current_status"]["cycles_completed"] = \
            self._state["current_status"].get("cycles_completed", 0) + 1
        self._save()

    # ── CONTROLS ──

    def check_execution_limit(self, tool: str) -> dict:
        """Check if a tool can be executed today."""
        controls = self._state["controls"]
        today = datetime.utcnow().strftime("%Y-%m-%d")

        # Reset daily counters
        if controls["execution_today"].get("date") != today:
            controls["execution_today"] = {
                "emails": 0, "whatsapp": 0,
                "landing_pages": 0, "social_posts": 0,
                "date": today,
            }

        limits = controls["execution_limits"]
        usage = controls["execution_today"]

        tool_map = {
            "email": ("emails", "emails_per_day"),
            "whatsapp": ("whatsapp", "whatsapp_per_day"),
            "landing_page": ("landing_pages", "landing_pages_per_day"),
            "social_post": ("social_posts", "social_posts_per_day"),
        }

        if tool not in tool_map:
            return {"allowed": True, "tool": tool, "reason": "no_limit_defined"}

        usage_key, limit_key = tool_map[tool]
        current = usage.get(usage_key, 0)
        limit = limits.get(limit_key, 999)

        return {
            "allowed": current < limit,
            "tool": tool,
            "current": current,
            "limit": limit,
            "reason": "" if current < limit else f"daily_limit_reached ({current}/{limit})",
        }

    def record_execution(self, tool: str):
        """Record a tool execution for daily tracking."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        controls = self._state["controls"]
        if controls["execution_today"].get("date") != today:
            controls["execution_today"] = {
                "emails": 0, "whatsapp": 0,
                "landing_pages": 0, "social_posts": 0,
                "date": today,
            }

        tool_map = {"email": "emails", "whatsapp": "whatsapp",
                    "landing_page": "landing_pages", "social_post": "social_posts"}
        key = tool_map.get(tool)
        if key:
            controls["execution_today"][key] = controls["execution_today"].get(key, 0) + 1
        self._save()

    def requires_approval(self, tool: str) -> bool:
        return tool in self._state["controls"].get("require_approval", [])

    def add_pending_approval(self, action: str, tool: str, params: dict) -> str:
        """Queue an action for human approval."""
        import uuid
        approval_id = f"appr_{uuid.uuid4().hex[:8]}"
        entry = {
            "id": approval_id,
            "action": action[:200],
            "tool": tool,
            "params": params,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": "",  # no auto-expiry for now
            "status": "pending",
        }
        pending = self._state["controls"]["pending_approvals"]
        pending.append(entry)
        if len(pending) > MAX_PENDING_APPROVALS:
            # Remove oldest resolved
            self._state["controls"]["pending_approvals"] = [
                p for p in pending if p["status"] == "pending"
            ][-MAX_PENDING_APPROVALS:]
        self._save()
        return approval_id

    def resolve_approval(self, approval_id: str, approved: bool) -> dict:
        """Approve or reject a pending action."""
        pending = self._state["controls"]["pending_approvals"]
        for p in pending:
            if p["id"] == approval_id and p["status"] == "pending":
                p["status"] = "approved" if approved else "rejected"
                p["resolved_at"] = datetime.utcnow().isoformat()
                self._save()
                return {"resolved": True, "status": p["status"], "action": p}
        return {"resolved": False, "reason": "not_found_or_already_resolved"}

    def get_pending_approvals(self) -> list:
        return [p for p in self._state["controls"]["pending_approvals"]
                if p["status"] == "pending"]


# ── Factory ──
_instances: dict[str, CompanyState] = {}


def get_company_state(customer_id: str = "") -> CompanyState:
    """Get or create CompanyState instance (cached per customer)."""
    key = customer_id or "_system"
    if key not in _instances:
        _instances[key] = CompanyState(customer_id=customer_id)
    return _instances[key]
