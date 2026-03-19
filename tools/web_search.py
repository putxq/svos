from duckduckgo_search import DDGS


class WebSearchTool:
    """يبحث في الإنترنت — يستخدمه Radar Agent وCEO"""

    name = "web_search"
    description = "Search the web for current information"

    async def execute(self, query: str, max_results: int = 5) -> dict:
        try:
            raw = []
            with DDGS() as ddgs:
                for backend in ("auto", "html", "lite"):
                    try:
                        raw = list(ddgs.text(query, max_results=max_results, backend=backend))
                    except TypeError:
                        raw = list(ddgs.text(query, max_results=max_results))
                    if raw:
                        break

            results = [
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                }
                for r in raw
            ]
            return {"query": query, "results": results, "total": len(results)}
        except Exception as e:
            return {"query": query, "results": [], "total": 0, "error": str(e)}
