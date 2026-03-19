from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from engine.registry import AgentRegistry
from memory.memory_manager import MemoryManager


class SpawnedAgent(BaseModel):
    agent_id: str
    parent_agent: str
    role: str
    task: str
    status: str = "active"
    created_at: str
    expires_at: str


class ElasticSpawner:
    def __init__(
        self,
        registry: AgentRegistry | None = None,
        memory: MemoryManager | None = None,
    ):
        self.registry = registry or AgentRegistry()
        self.memory = memory or MemoryManager()
        self._active: dict[str, list[dict[str, Any]]] = {}

    async def spawn(
        self,
        parent_agent: str,
        role: str,
        task: str,
        ttl_minutes: int = 60,
    ) -> SpawnedAgent:
        """
        1) register in registry
        2) attach task + context
        3) bind to constitution/memory context (through metadata)
        4) start execution (simulated async task)
        5) auto-dismiss on completion or TTL
        """
        now = datetime.utcnow()
        expires = now + timedelta(minutes=max(1, ttl_minutes))
        agent_id = f"{parent_agent}-spawn-{uuid4().hex[:8]}"

        # Ensure DB schema exists (safe idempotent)
        await self.registry.init()
        await self.registry.register_agent(
            agent_id=agent_id,
            name=agent_id,
            agent_type=role,
            sovereignty="bounded",
            port=0,
        )

        spawned = SpawnedAgent(
            agent_id=agent_id,
            parent_agent=parent_agent,
            role=role,
            task=task,
            status="active",
            created_at=now.isoformat(),
            expires_at=expires.isoformat(),
        )

        self._active.setdefault(parent_agent, []).append(spawned.model_dump())

        # memory linkage (parent-side episodic trace)
        self.memory.episodic.add(
            "spawn_created",
            {
                "parent": parent_agent,
                "agent_id": agent_id,
                "role": role,
                "task": task,
                "ttl_minutes": ttl_minutes,
            },
        )

        # Simulated background lifecycle: complete quickly then dismiss
        async def _run_and_cleanup():
            await asyncio.sleep(0)  # hook for real execution launcher
            await self.dismiss(agent_id)

        asyncio.create_task(_run_and_cleanup())

        return spawned

    async def dismiss(self, agent_id: str) -> dict:
        """
        1) persist results to parent episodic memory
        2) remove from active registry cache
        3) free resources (metadata cleanup)
        """
        parent_found = None
        spawn_obj = None
        for parent, items in self._active.items():
            for item in items:
                if item.get("agent_id") == agent_id:
                    parent_found = parent
                    spawn_obj = item
                    break
            if parent_found:
                break

        if not spawn_obj:
            return {"agent_id": agent_id, "dismissed": False, "reason": "not_found"}

        # save completion trace into parent's memory
        self.memory.episodic.add(
            "spawn_dismissed",
            {
                "parent": parent_found,
                "agent_id": agent_id,
                "role": spawn_obj.get("role"),
                "task": spawn_obj.get("task"),
                "status": "dismissed",
            },
        )

        # remove from active list
        self._active[parent_found] = [x for x in self._active[parent_found] if x.get("agent_id") != agent_id]
        if not self._active[parent_found]:
            self._active.pop(parent_found, None)

        # release resources / mark done in local response
        return {
            "agent_id": agent_id,
            "dismissed": True,
            "parent_agent": parent_found,
            "released": True,
        }

    async def get_active_spawns(self, parent_agent: str) -> list:
        return self._active.get(parent_agent, [])
