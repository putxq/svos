from core.schemas import DecisionRequest, DecisionResponse


class ConstitutionValidator:
    """Validates decisions against business constitution constraints."""

    def validate(self, payload: DecisionRequest) -> DecisionResponse:
        reject_reasons: list[str] = []
        notes: list[str] = []

        action_l = payload.action.lower()
        constraints_l = [c.lower().strip() for c in payload.business.constraints]

        # Reject only for meaningful, explicit constraint matches.
        for rule in constraints_l:
            if rule and len(rule) > 3 and rule in action_l:
                reject_reasons.append(f"Action conflicts with business constraint: {rule}")

        # Missing goals is warning/note, not a hard rejection.
        if not payload.business.goals:
            notes.append('Warning: business goals are empty')

        if reject_reasons:
            return DecisionResponse(status='rejected', reasons=reject_reasons)

        reasons = ['Complies with constitution'] + notes
        return DecisionResponse(status='approved', reasons=reasons)
