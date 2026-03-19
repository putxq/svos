class IdentityStore:
    def __init__(self):
        self.identity = {
            "who_we_are": "SVOS Sovereign Kernel",
            "non_negotiables": [],
        }

    def set_identity(self, who_we_are: str, non_negotiables: list[str]):
        self.identity["who_we_are"] = who_we_are
        self.identity["non_negotiables"] = non_negotiables

    def get_identity(self):
        return self.identity
