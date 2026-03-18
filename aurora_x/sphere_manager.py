"""
Sphere Manager — حضارة رقمية لكل عميل
"""
import uuid

from aurora_x.constitution_engine import ConstitutionEngine


class Sphere:
    def __init__(self, owner: str, business_type: str):
        self.sphere_id = str(uuid.uuid4())[:8]
        self.owner = owner
        self.business_type = business_type
        self.constitution = ConstitutionEngine(self.sphere_id)
        self.ventures = []
        self.treasury = 0.0
        self.status = "active"

    def initialize(
        self,
        mission: str,
        values: list[str],
        constraints: list[str],
        goals: list[str],
    ) -> dict:
        self.constitution.build_from_input(mission, values, constraints, goals)
        return {
            "sphere_id": self.sphere_id,
            "owner": self.owner,
            "business_type": self.business_type,
            "status": self.status,
            "constitution": self.constitution.constitution,
        }

    def validate(self, decision: str, agent: str) -> dict:
        return self.constitution.validate_decision(decision, agent)

    def get_status(self) -> dict:
        return {
            "sphere_id": self.sphere_id,
            "owner": self.owner,
            "business_type": self.business_type,
            "ventures": len(self.ventures),
            "treasury": self.treasury,
            "constitution_summary": self.constitution.get_summary(),
        }


class SphereManager:
    def __init__(self):
        self.spheres: dict[str, Sphere] = {}

    def create_sphere(self, owner: str, business_type: str) -> Sphere:
        sphere = Sphere(owner, business_type)
        self.spheres[sphere.sphere_id] = sphere
        return sphere

    def get_sphere(self, sphere_id: str) -> Sphere | None:
        return self.spheres.get(sphere_id)

    def list_spheres(self) -> list[dict]:
        return [s.get_status() for s in self.spheres.values()]
