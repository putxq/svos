from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from core.llm_provider import LLMProvider
from core.logger import log_decision
from memory.memory_manager import MemoryManager


class ThinkResult(BaseModel):
    plan: list[str] = Field(default_factory=list)
    confidence: float = 0.0  # 0.0 - 1.0
    reasoning: str = ""
    needs_discussion: bool = False
    needs_escalation: bool = False


class ExecutionResult(BaseModel):
    success: bool
    steps_executed: list[str] = Field(default_factory=list)
    failed_step: str | None = None
    details: str = ""


class DiscussionResult(BaseModel):
    topic: str
    participants: list[str] = Field(default_factory=list)
    opinions: dict[str, str] = Field(default_factory=dict)
    confidences: dict[str, float] = Field(default_factory=dict)
    consensus: str = ""
    escalated: bool = False


class ShadowResult(BaseModel):
    task: str
    candidate_decision: str
    reference_decisions: list[str] = Field(default_factory=list)
    differences: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class BaseAgent:
    """SVOS unified base agent (Tesla-like end-to-end decision loop)."""

    def __init__(
        self,
        name: str,
        role: str,
        department: str,
        autonomy_level: float = 0.7,
        llm_provider: LLMProvider | None = None,
        memory_manager: MemoryManager | None = None,
    ):
        # === الهوية ===
        self.name = name
        self.role = role
        self.department = department
        self.autonomy_level = max(0.0, min(1.0, autonomy_level))

        self.llm = llm_provider or LLMProvider()
        self.memory = memory_manager or MemoryManager()
        self.sub_agents: dict[str, dict[str, Any]] = {}

    # === التفكير ===
    async def think(self, task: str, context: dict) -> ThinkResult:
        system_prompt = (
            "You are an executive AI agent. Think end-to-end: understand task, plan, "
            "estimate confidence, and decide if discussion/escalation is needed. "
            "Return strict JSON with keys: plan, confidence, reasoning, needs_discussion, needs_escalation."
        )
        user_message = f"Agent: {self.name} ({self.role})\nTask: {task}\nContext: {context}"

        schema = {
            "type": "object",
            "properties": {
                "plan": {"type": "array", "items": {"type": "string"}},
                "confidence": {"type": "number"},
                "reasoning": {"type": "string"},
                "needs_discussion": {"type": "boolean"},
                "needs_escalation": {"type": "boolean"},
            },
            "required": ["plan", "confidence", "reasoning", "needs_discussion", "needs_escalation"],
        }

        raw = await self.llm.complete_structured(system_prompt, user_message, schema)
        confidence_raw = float(raw.get("confidence", 0.0) or 0.0)

        # accept either 0-1 or 0-100 from model
        if confidence_raw > 1.0:
            confidence = max(0.0, min(1.0, confidence_raw / 100.0))
        else:
            confidence = max(0.0, min(1.0, confidence_raw))

        result = ThinkResult(
            plan=[str(x) for x in (raw.get("plan") or [])],
            confidence=confidence,
            reasoning=str(raw.get("reasoning", "")),
            needs_discussion=bool(raw.get("needs_discussion", False)),
            needs_escalation=bool(raw.get("needs_escalation", False)),
        )

        await self.remember("last_think", result.model_dump(), "episodic")
        return result

    # === الذاكرة ===
    async def remember(self, key: str, value: Any, memory_type: str):
        if memory_type == "episodic":
            self.memory.episodic.add(key, {"value": value})
        elif memory_type == "semantic":
            self.memory.semantic.set(key, str(value))
        elif memory_type == "strategic":
            if isinstance(value, dict):
                self.memory.strategic.record(
                    strategy=str(value.get("strategy", key)),
                    outcome=str(value.get("outcome", "unknown")),
                    why=str(value.get("why", "")),
                )
            else:
                self.memory.strategic.record(strategy=key, outcome="unknown", why=str(value))
        elif memory_type == "identity":
            if isinstance(value, dict):
                self.memory.identity.set_identity(
                    who_we_are=str(value.get("who_we_are", self.name)),
                    non_negotiables=list(value.get("non_negotiables", [])),
                )
        else:
            raise ValueError("memory_type must be one of episodic/semantic/strategic/identity")

    async def recall(self, query: str, memory_type: str = "all") -> list:
        out: list[Any] = []
        if memory_type in ("all", "episodic"):
            out.extend([e for e in self.memory.episodic.recent(100) if query in str(e)])
        if memory_type in ("all", "semantic"):
            sem = self.memory.semantic.all()
            out.extend([{k: v} for k, v in sem.items() if query in k or query in str(v)])
        if memory_type in ("all", "strategic"):
            out.extend([r for r in self.memory.strategic.records if query in str(r)])
        if memory_type in ("all", "identity"):
            ident = self.memory.identity.get_identity()
            if query in str(ident):
                out.append(ident)
        return out

    # === التنفيذ ===
    async def execute(self, plan: list[str]) -> ExecutionResult:
        executed: list[str] = []
        try:
            for step in plan:
                executed.append(step)
                await asyncio.sleep(0)  # hook for real execution
            res = ExecutionResult(success=True, steps_executed=executed, details="Plan executed")
            log_decision(self.name, "execute_plan", 100.0, "success")
            return res
        except Exception as exc:
            res = ExecutionResult(
                success=False,
                steps_executed=executed,
                failed_step=executed[-1] if executed else None,
                details=str(exc),
            )
            log_decision(self.name, "execute_plan", None, "failure")
            return res

    # === الأدوات ===
    async def use_tool(self, tool_name: str, params: dict) -> Any:
        # MCP-ready placeholder
        await self.remember("tool_call", {"tool": tool_name, "params": params}, "episodic")
        return {"tool": tool_name, "params": params, "result": "not_implemented"}

    # === النقاش ===
    async def discuss(self, topic: str, participants: list[str]) -> DiscussionResult:
        opinions: dict[str, str] = {}
        confidences: dict[str, float] = {}
        for p in participants:
            opinions[p] = f"{p}: رأي مبدئي حول {topic}"
            confidences[p] = 0.7
        escalated = any(c < 0.6 for c in confidences.values())
        consensus = "escalate" if escalated else "proceed"
        result = DiscussionResult(
            topic=topic,
            participants=participants,
            opinions=opinions,
            confidences=confidences,
            consensus=consensus,
            escalated=escalated,
        )
        await self.remember("last_discussion", result.model_dump(), "episodic")
        return result

    # === التكاثر المرن ===
    async def spawn_sub_agent(self, role: str, task: str) -> str:
        agent_id = f"{self.name}-sub-{uuid.uuid4().hex[:8]}"
        self.sub_agents[agent_id] = {
            "role": role,
            "task": task,
            "created_at": datetime.utcnow().isoformat(),
            "status": "active",
        }
        await self.remember("spawn", {"agent_id": agent_id, "role": role, "task": task}, "episodic")
        return agent_id

    async def dismiss_sub_agent(self, agent_id: str):
        if agent_id in self.sub_agents:
            self.sub_agents[agent_id]["status"] = "dismissed"
            await self.remember("dismiss", {"agent_id": agent_id}, "episodic")

    # === درجة الثقة (منطق تسلا) ===
    def calculate_confidence(self, factors: dict) -> float:
        task_clarity = float(factors.get("task_clarity", 0.5))
        data_availability = float(factors.get("data_availability", 0.5))
        strategic_similarity = float(factors.get("strategic_similarity", 0.5))
        constitution_alignment = float(factors.get("constitution_alignment", 0.5))

        score = (
            task_clarity * 0.25
            + data_availability * 0.25
            + strategic_similarity * 0.2
            + constitution_alignment * 0.3
        )
        return max(0.0, min(1.0, round(score, 4)))

    # === Shadow Mode (منطق تسلا) ===
    async def shadow_run(self, task: str) -> ShadowResult:
        candidate = await self.llm.complete(
            "أنت وكيل يعمل في وضع الظل. اقترح قرارًا مختصرًا.",
            f"المهمة: {task}",
            temperature=0.2,
        )
        references = [str(x) for x in await self.recall(task, memory_type="episodic")]
        diffs = ["no_reference"] if not references else ["partial_match"]
        conf = 0.6 if references else 0.45
        result = ShadowResult(
            task=task,
            candidate_decision=candidate,
            reference_decisions=references,
            differences=diffs,
            confidence=conf,
        )
        await self.remember("shadow", result.model_dump(), "episodic")
        return result

    # === التعلم ===
    async def learn_from_outcome(self, task: str, outcome: str, success: bool):
        await self.remember(
            key=f"learn:{task}",
            value={
                "strategy": task,
                "outcome": "success" if success else "failure",
                "why": outcome,
            },
            memory_type="strategic",
        )

    # === دورة الحياة ===
    async def heartbeat(self) -> dict:
        return {
            "agent": self.name,
            "role": self.role,
            "department": self.department,
            "autonomy_level": self.autonomy_level,
            "sub_agents_active": len([a for a in self.sub_agents.values() if a["status"] == "active"]),
            "status": "healthy",
            "ts": datetime.utcnow().isoformat(),
        }
