from typing import Iterable


def format_goals(goals: Iterable[str]) -> str:
    goals_list = [g for g in goals if g]
    if not goals_list:
        return "- لا توجد أهداف محددة"
    return "\n".join(f"- {g}" for g in goals_list)
