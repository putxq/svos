from datetime import datetime


class EpisodicStore:
    def __init__(self):
        self.events = []

    def add(self, event_type: str, payload: dict):
        self.events.append(
            {
                "ts": datetime.utcnow().isoformat(),
                "type": event_type,
                "payload": payload,
            }
        )

    def recent(self, limit: int = 20):
        return self.events[-limit:]
