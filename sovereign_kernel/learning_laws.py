class LearningLaws:
    @staticmethod
    def can_learn(trace_exists, test_results=None):
        if not trace_exists:
            return False

        if test_results is not None:
            pass_rate = sum(test_results) / len(test_results) if test_results else 0
            return pass_rate >= 0.8

        return True

    @staticmethod
    def law_5_human_never_disappears(risk_level, irreversible):
        if irreversible or risk_level == "critical":
            return "founder_approval_required"
        elif risk_level == "high":
            return "board_review_required"
        elif risk_level == "medium":
            return "team_discussion_required"
        return "auto_proceed"
