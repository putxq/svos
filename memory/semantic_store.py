class SemanticStore:
    def __init__(self):
        self.knowledge = {}

    def set(self, key: str, value: str):
        self.knowledge[key] = value

    def get(self, key: str, default=None):
        return self.knowledge.get(key, default)

    def all(self):
        return self.knowledge
