from pydantic import BaseModel, Field


class SkillGenome(BaseModel):
    skill_id: str
    name: str
    purpose: str
    created_by: str
    version: int = 1
    success_count: int = 0
    failure_count: int = 0
    avg_confidence: float = 0.0
    status: str = "active"

    def success_rate(self):
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0


class SkillRegistry:
    def __init__(self):
        self._skills = {}

    def register(self, skill):
        self._skills[skill.skill_id] = skill

    def get(self, skill_id):
        return self._skills.get(skill_id)

    def record_outcome(self, skill_id, success, confidence):
        s = self._skills.get(skill_id)
        if not s:
            return
        if success:
            s.success_count += 1
        else:
            s.failure_count += 1
