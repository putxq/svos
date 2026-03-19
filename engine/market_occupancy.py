class MarketOccupancy:
    def __init__(self):
        self.map = {"opportunities": [], "occupied": [], "risks": []}

    def update(self, opportunities: list[str], occupied: list[str], risks: list[str]):
        self.map = {
            "opportunities": opportunities,
            "occupied": occupied,
            "risks": risks,
        }
        return self.map

    def snapshot(self):
        return self.map
