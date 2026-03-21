"""
A2A (Agent2Agent) Protocol Implementation for SVOS.
Each C-suite agent is exposed as a discoverable A2A service.
Follows the Agent2Agent Protocol specification (Linux Foundation).
"""

import logging
import time
import uuid
from typing import Any

logger = logging.getLogger("svos.a2a")


AGENT_CARDS = {
    "CEO": {
        "name": "SVOS CEO Agent",
        "description": "Chief Executive Officer - Strategic leadership, final decisions, company vision",
        "url": "/a2a/agents/CEO",
        "version": "1.0.0",
        "capabilities": {"streaming": False, "pushNotifications": False, "stateTransitionHistory": True},
        "skills": [
            {
                "id": "strategic_thinking",
                "name": "Strategic Analysis",
                "description": "Analyze business situations and provide strategic recommendations",
                "tags": ["strategy", "leadership", "decision-making"],
            },
            {
                "id": "company_creation",
                "name": "Company Creation",
                "description": "Design and launch new digital companies",
                "tags": ["startup", "business-model", "launch"],
            },
        ],
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["text"],
    },
    "CFO": {
        "name": "SVOS CFO Agent",
        "description": "Chief Financial Officer - Financial analysis, budgeting, revenue strategy",
        "url": "/a2a/agents/CFO",
        "version": "1.0.0",
        "capabilities": {"streaming": False, "pushNotifications": False, "stateTransitionHistory": True},
        "skills": [
            {
                "id": "financial_analysis",
                "name": "Financial Analysis",
                "description": "Analyze financial data and provide insights",
                "tags": ["finance", "analysis", "budgeting"],
            },
            {
                "id": "revenue_modeling",
                "name": "Revenue Modeling",
                "description": "Build and evaluate revenue models",
                "tags": ["revenue", "pricing", "forecasting"],
            },
        ],
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["text"],
    },
    "CMO": {
        "name": "SVOS CMO Agent",
        "description": "Chief Marketing Officer - Marketing strategy, campaigns, growth",
        "url": "/a2a/agents/CMO",
        "version": "1.0.0",
        "capabilities": {"streaming": False, "pushNotifications": False, "stateTransitionHistory": True},
        "skills": [
            {
                "id": "campaign_design",
                "name": "Campaign Design",
                "description": "Design marketing campaigns across channels",
                "tags": ["marketing", "campaigns", "growth"],
            },
            {
                "id": "content_creation",
                "name": "Content Strategy",
                "description": "Create marketing content and landing pages",
                "tags": ["content", "copywriting", "landing-pages"],
            },
        ],
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["text"],
    },
    "COO": {
        "name": "SVOS COO Agent",
        "description": "Chief Operating Officer - Operations, processes, efficiency",
        "url": "/a2a/agents/COO",
        "version": "1.0.0",
        "capabilities": {"streaming": False, "pushNotifications": False, "stateTransitionHistory": True},
        "skills": [
            {
                "id": "operations_optimization",
                "name": "Operations Optimization",
                "description": "Streamline and optimize business operations",
                "tags": ["operations", "efficiency", "processes"],
            }
        ],
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["text"],
    },
    "CTO": {
        "name": "SVOS CTO Agent",
        "description": "Chief Technology Officer - Technology strategy, architecture, innovation",
        "url": "/a2a/agents/CTO",
        "version": "1.0.0",
        "capabilities": {"streaming": False, "pushNotifications": False, "stateTransitionHistory": True},
        "skills": [
            {
                "id": "tech_architecture",
                "name": "Technical Architecture",
                "description": "Design and evaluate system architectures",
                "tags": ["architecture", "technology", "systems"],
            },
            {
                "id": "tech_evaluation",
                "name": "Technology Evaluation",
                "description": "Evaluate tools, frameworks, and platforms",
                "tags": ["evaluation", "tools", "platforms"],
            },
        ],
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["text"],
    },
    "CLO": {
        "name": "SVOS CLO Agent",
        "description": "Chief Legal Officer - Legal compliance, contracts, regulations",
        "url": "/a2a/agents/CLO",
        "version": "1.0.0",
        "capabilities": {"streaming": False, "pushNotifications": False, "stateTransitionHistory": True},
        "skills": [
            {
                "id": "compliance_check",
                "name": "Compliance Analysis",
                "description": "Verify regulatory and legal compliance",
                "tags": ["legal", "compliance", "regulations"],
            }
        ],
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["text"],
    },
    "CHRO": {
        "name": "SVOS CHRO Agent",
        "description": "Chief Human Resources Officer - HR strategy, talent, culture",
        "url": "/a2a/agents/CHRO",
        "version": "1.0.0",
        "capabilities": {"streaming": False, "pushNotifications": False, "stateTransitionHistory": True},
        "skills": [
            {
                "id": "hr_strategy",
                "name": "HR Strategy",
                "description": "Design HR policies and talent strategies",
                "tags": ["hr", "talent", "culture"],
            }
        ],
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["text"],
    },
    "GUARDIAN": {
        "name": "SVOS Guardian Agent",
        "description": "System Guardian - Safety, security, trust verification",
        "url": "/a2a/agents/GUARDIAN",
        "version": "1.0.0",
        "capabilities": {"streaming": False, "pushNotifications": False, "stateTransitionHistory": True},
        "skills": [
            {
                "id": "safety_check",
                "name": "Safety Verification",
                "description": "Verify actions against safety policies",
                "tags": ["safety", "security", "trust"],
            }
        ],
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["text"],
    },
    "RADAR": {
        "name": "SVOS Radar Agent",
        "description": "Market Intelligence - Trend detection, opportunity scanning, competitive analysis",
        "url": "/a2a/agents/RADAR",
        "version": "1.0.0",
        "capabilities": {"streaming": False, "pushNotifications": False, "stateTransitionHistory": True},
        "skills": [
            {
                "id": "market_scan",
                "name": "Market Intelligence",
                "description": "Scan markets for opportunities and threats",
                "tags": ["market", "intelligence", "trends"],
            }
        ],
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["text"],
    },
}


class A2ATask:
    """Represents an A2A task with lifecycle states."""

    STATES = ["submitted", "working", "input-required", "completed", "failed", "canceled"]

    def __init__(self, task_id: str = None):
        self.id = task_id or str(uuid.uuid4())
        self.state = "submitted"
        self.messages = []
        self.artifacts = []
        self.created_at = time.time()
        self.updated_at = time.time()
        self.metadata = {}

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "parts": [{"type": "text", "text": content}], "timestamp": time.time()})
        self.updated_at = time.time()

    def add_artifact(self, name: str, data: Any):
        self.artifacts.append({"name": name, "parts": [{"type": "text", "text": str(data)}], "timestamp": time.time()})
        self.updated_at = time.time()

    def set_state(self, state: str):
        if state in self.STATES:
            self.state = state
            self.updated_at = time.time()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "state": self.state,
            "messages": self.messages,
            "artifacts": self.artifacts,
            "metadata": self.metadata,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }


class A2AProtocolHandler:
    """
    Handles A2A protocol requests for SVOS agents.
    Implements: discovery, task creation, task execution.
    """

    def __init__(self):
        self._tasks: dict[str, A2ATask] = {}
        logger.info("A2AProtocolHandler initialized")

    def get_agent_card(self, role: str) -> dict:
        return AGENT_CARDS.get(role.upper())

    def list_agent_cards(self) -> list[dict]:
        return list(AGENT_CARDS.values())

    async def create_task(self, agent_role: str, message: str, metadata: dict = None) -> A2ATask:
        task = A2ATask()
        task.metadata = metadata or {}
        task.metadata["agent_role"] = agent_role
        task.add_message("user", message)
        task.set_state("working")
        self._tasks[task.id] = task

        try:
            from agents import AGENT_REGISTRY

            agent_cls = AGENT_REGISTRY.get(agent_role.upper())
            if not agent_cls:
                task.set_state("failed")
                task.add_message("agent", f"Agent '{agent_role}' not found")
                return task

            agent = agent_cls()
            result = await agent.think(
                task=message,
                context=f"You are responding to an external A2A protocol request. Task ID: {task.id}",
            )

            response_text = str(result) if result else "No response generated"
            task.add_message("agent", response_text)
            task.add_artifact("think_result", result)
            task.set_state("completed")

        except Exception as e:
            logger.error(f"A2A task execution error: {e}")
            task.set_state("failed")
            task.add_message("agent", f"Execution error: {str(e)}")

        return task

    def get_task(self, task_id: str) -> A2ATask:
        return self._tasks.get(task_id)

    def list_tasks(self, limit: int = 20) -> list[dict]:
        tasks = sorted(self._tasks.values(), key=lambda t: t.updated_at, reverse=True)
        return [t.to_dict() for t in tasks[:limit]]


_handler = None


def get_a2a_handler() -> A2AProtocolHandler:
    global _handler
    if _handler is None:
        _handler = A2AProtocolHandler()
    return _handler
