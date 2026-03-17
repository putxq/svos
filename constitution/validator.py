from core.schemas import DecisionRequest, DecisionResponse


class ConstitutionValidator:
    """Validates decisions against business constitution constraints."""

    def validate(self, payload: DecisionRequest) -> DecisionResponse:
        reasons: list[str] = []

        action_l = payload.action.lower()
        constraints_l = [c.lower() for c in payload.business.constraints]

        for rule in constraints_l:
            if rule and rule in action_l:
                reasons.append(f"Action conflicts with business constraint: {rule}")

        if not payload.business.goals:
            reasons.append('Business goals are empty; cannot align decision')

        if reasons:
            return DecisionResponse(status='rejected', reasons=reasons)

        return DecisionResponse(status='approved', reasons=['Complies with constitution'])
