from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from typing import Any

from pydantic import BaseModel, Field

from core.llm_provider import LLMProvider
from memory.memory_manager import MemoryManager


class DiscussionArgument(BaseModel):
    round: int
    agent: str
    stance: str
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str


class DiscussionResult(BaseModel):
    decision: str
    consensus: float = Field(ge=0.0, le=1.0)
    arguments: list[dict] = Field(default_factory=list)
    dissents: list[dict] = Field(default_factory=list)


class DiscussionEngine:
    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        memory_manager: MemoryManager | None = None,
        role_prompts: dict[str, str] | None = None,
    ):
        self.llm = llm_provider or LLMProvider()
        self.memory = memory_manager or MemoryManager()
        self.role_prompts = role_prompts or {}

    def _agent_prompt(self, agent: str) -> str:
        return self.role_prompts.get(
            agent,
            f"You are agent {agent}. Reply in concise executive Arabic with confidence score.",
        )

    async def _agent_opinion(
        self,
        topic: str,
        agent: str,
        context: dict,
        round_no: int,
        prior_arguments: list[dict],
        constitution: dict | None = None,
    ) -> DiscussionArgument:
        strategic = self.memory.strategic.best_practices()
        user_message = (
            f"Topic: {topic}\n"
            f"Round: {round_no}\n"
            f"Context: {context}\n"
            f"Prior arguments: {prior_arguments}\n"
            f"Strategic memory: {strategic}\n"
            f"Constitution: {constitution or {}}\n\n"
            "Return strict JSON with keys: stance, confidence(0..1), rationale"
        )
        schema = {
            "type": "object",
            "properties": {
                "stance": {"type": "string"},
                "confidence": {"type": "number"},
                "rationale": {"type": "string"},
            },
            "required": ["stance", "confidence", "rationale"],
        }
        out = await self.llm.complete_structured(
            self._agent_prompt(agent),
            user_message,
            schema,
        )

        conf = float(out.get("confidence", 0.5) or 0.5)
        if conf > 1:
            conf = conf / 100.0
        conf = max(0.0, min(1.0, conf))

        return DiscussionArgument(
            round=round_no,
            agent=agent,
            stance=str(out.get("stance", "neutral")),
            confidence=conf,
            rationale=str(out.get("rationale", "")),
        )

    async def open_discussion(
        self,
        topic: str,
        initiator: str,
        participants: list[str],
        context: dict,
        max_rounds: int = 3,
    ) -> DiscussionResult:
        """
        الجولة 1: كل مشارك يعطي رأيه + درجة ثقته
        الجولة 2: كل مشارك يعلق على آراء الآخرين
        الجولة 3: تصويت نهائي

        إذا اتفقوا (ثقة جماعية > 75%): القرار يمر
        إذا اختلفوا: يُصعّد لمجلس الإدارة
        """
        agents = [initiator] + [p for p in participants if p != initiator]
        arguments: list[dict[str, Any]] = []

        # pull constitution snapshot from semantic memory if exists
        constitution = self.memory.semantic.get("constitution", {})

        for round_no in range(1, max_rounds + 1):
            round_args: list[DiscussionArgument] = []
            for agent in agents:
                arg = await self._agent_opinion(
                    topic=topic,
                    agent=agent,
                    context=context,
                    round_no=round_no,
                    prior_arguments=arguments,
                    constitution=constitution,
                )
                round_args.append(arg)
                arg_dict = arg.model_dump()
                arguments.append(arg_dict)

                # episodic logging of discussion turns
                self.memory.episodic.add(
                    event_type="discussion_turn",
                    payload={
                        "topic": topic,
                        "initiator": initiator,
                        "agent": agent,
                        "round": round_no,
                        "argument": arg_dict,
                    },
                )

            # optional early stop after round 2 if consensus is already very high
            round_consensus = sum(a.confidence for a in round_args) / max(len(round_args), 1)
            if round_no >= 2 and round_consensus >= 0.90:
                break

        # final consensus over all contributions
        confidences = [float(a.get("confidence", 0.0)) for a in arguments]
        consensus = sum(confidences) / max(len(confidences), 1)

        dissents = [a for a in arguments if float(a.get("confidence", 0.0)) < 0.5]

        if consensus > 0.75:
            decision = "approved"
        else:
            decision = "escalate_to_board"

        result = DiscussionResult(
            decision=decision,
            consensus=round(consensus, 4),
            arguments=arguments,
            dissents=dissents,
        )

        self.memory.episodic.add(
            event_type="discussion_result",
            payload={
                "topic": topic,
                "initiator": initiator,
                "participants": participants,
                "result": result.model_dump(),
            },
        )

        return result
