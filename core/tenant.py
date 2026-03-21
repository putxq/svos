"""
Tenant isolation for SVOS.
Every request gets a tenant context based on the authenticated customer_id.
Engines that need per-customer data use get_tenant_dir() to isolate storage.
"""

import os
from contextvars import ContextVar
from pathlib import Path
from typing import Any

# ── Context variable: set per-request in middleware ──
_current_tenant: ContextVar[dict] = ContextVar("current_tenant", default={})


def set_tenant(customer_id: str, plan_id: str = "", is_master: bool = False):
    _current_tenant.set({
        "customer_id": customer_id,
        "plan_id": plan_id,
        "is_master": is_master,
    })


def get_tenant() -> dict:
    return _current_tenant.get({})


def get_customer_id() -> str:
    return get_tenant().get("customer_id", "")


def require_customer_id() -> str:
    cid = get_customer_id()
    if not cid:
        raise PermissionError("No tenant context — request is not authenticated")
    return cid


# ── Per-tenant workspace directory ──
TENANTS_ROOT = Path("workspace/tenants")


def get_tenant_dir(customer_id: str | None = None) -> Path:
    """Return isolated workspace directory for a customer."""
    cid = customer_id or get_customer_id()
    if not cid:
        return Path("workspace")  # fallback for unauthenticated / legacy
    tenant_dir = TENANTS_ROOT / cid
    tenant_dir.mkdir(parents=True, exist_ok=True)
    return tenant_dir


def get_tenant_crm_dir(customer_id: str | None = None) -> Path:
    return get_tenant_dir(customer_id) / "crm"


def get_tenant_dna_dir(customer_id: str | None = None) -> Path:
    return get_tenant_dir(customer_id) / "dna"


def get_tenant_reports_dir(customer_id: str | None = None) -> Path:
    return get_tenant_dir(customer_id) / "reports"


def get_tenant_pages_dir(customer_id: str | None = None) -> Path:
    d = get_tenant_dir(customer_id) / "pages"
    d.mkdir(parents=True, exist_ok=True)
    return d


def init_tenant_workspace(customer_id: str) -> dict:
    """Create all subdirectories for a new tenant."""
    base = get_tenant_dir(customer_id)
    dirs = ["crm", "dna", "reports", "pages", "factory_output", "logs"]
    for d in dirs:
        (base / d).mkdir(parents=True, exist_ok=True)
    return {
        "customer_id": customer_id,
        "workspace": str(base),
        "dirs_created": dirs,
    }
