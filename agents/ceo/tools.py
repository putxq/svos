from typing import Iterable

import httpx


def format_goals(goals: Iterable[str]) -> str:
    goals_list = [g for g in goals if g]
    if not goals_list:
        return "- لا توجد أهداف محددة"
    return "\n".join(f"- {g}" for g in goals_list)


async def search_market(query: str) -> str:
    url = "https://api.duckduckgo.com/"
    params = {
        "q": query,
        "format": "json",
        "no_html": 1,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, timeout=10)
    data = resp.json()
    return data.get("AbstractText", "No results found")
