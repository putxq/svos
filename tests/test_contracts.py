from core.contracts import (
    ConstitutionCheckRequest,
    MessageEnvelope,
    RunCheckpoint,
    SpawnRequest,
)


def test_message_envelope_defaults():
    env = MessageEnvelope(
        from_agent="ceo",
        to_agent="coo",
        intent="delegate_task",
        payload={"task": "optimize ops"},
    )
    assert env.message_id
    assert env.priority == "normal"
    assert env.payload["task"] == "optimize ops"


def test_spawn_request_limits():
    req = SpawnRequest(parent_agent="ceo", role="analyst", objective="analyze market")
    assert req.budget_tokens == 1500
    assert req.max_minutes == 30


def test_checkpoint_bounds():
    cp = RunCheckpoint(run_id="r1", agent_id="ceo", state="running", progress=0.7)
    assert cp.progress == 0.7


def test_constitution_request():
    c = ConstitutionCheckRequest(
        business_id="b1",
        actor="ceo",
        action="launch pricing change",
        context={"market": "sa"},
    )
    assert c.business_id == "b1"
    assert c.context["market"] == "sa"
