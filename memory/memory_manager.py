from memory.episodic_store import EpisodicStore
from memory.semantic_store import SemanticStore
from memory.strategic_store import StrategicStore
from memory.identity_store import IdentityStore


class MemoryManager:
    def __init__(self):
        self.episodic = EpisodicStore()
        self.semantic = SemanticStore()
        self.strategic = StrategicStore()
        self.identity = IdentityStore()

    def snapshot(self):
        return {
            "episodic_recent": self.episodic.recent(),
            "semantic": self.semantic.all(),
            "strategic_best": self.strategic.best_practices(),
            "identity": self.identity.get_identity(),
        }
