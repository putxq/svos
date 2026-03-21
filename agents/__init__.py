from agents.ceo.agent import CEOAgent
from agents.cfo.agent import CFOAgent
from agents.cmo.agent import CMOAgent
from agents.coo.agent import COOAgent
from agents.cto.agent import CTOAgent
from agents.clo.agent import CLOAgent
from agents.chro.agent import CHROAgent
from agents.guardian.agent import GuardianAgent
from agents.radar.agent import RadarAgent

AGENT_REGISTRY = {
    "CEO": CEOAgent,
    "CFO": CFOAgent,
    "CMO": CMOAgent,
    "COO": COOAgent,
    "CTO": CTOAgent,
    "CLO": CLOAgent,
    "CHRO": CHROAgent,
    "GUARDIAN": GuardianAgent,
    "RADAR": RadarAgent,
}


def get_agent_class(role: str):
    return AGENT_REGISTRY.get(role.upper())


def list_roles():
    return list(AGENT_REGISTRY.keys())
