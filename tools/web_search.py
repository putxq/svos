import re
from urllib.parse import quote_plus

import httpx


class WebSearchTool:
    """يبحث في الإنترنت — يستخدمه Radar Agent وCEO"""

    name = "web_search"
    description = "Search the web for current information"

    async def execute(self, query: str, max_results: int = 5) -> dict:
        """
        يبحث عبر DuckDuckGo API (مجاني بدون مفتاح)
        إذا فشل API يستخدم html.duckduckgo.com مع استخراج regex بسيط.
        """
        results: list[dict] = []
        q = (query or "").strip()
        if not q:
            return {"query": query, "results": [], "total": 0}

        api_url = f"https://api.duckduckgo.com/?q={quote_plus(q)}&format=json&no_redirect=1"
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                r = await client.get(api_url)
                r.raise_for_status()
                data = r.json()

            # DuckDuckGo API غالباً يرجع RelatedTopics
            related = data.get("RelatedTopics") or []
            for item in related:
                if isinstance(item, dict) and item.get("Text") and item.get("FirstURL"):
                    results.append(
                        {
                            "title": item.get("Text", "")[:120],
                            "url": item.get("FirstURL", ""),
                            "snippet": item.get("Text", ""),
                        }
                    )
                # أحياناً nested topics
                for sub in (item.get("Topics") or []) if isinstance(item, dict) else []:
                    if sub.get("Text") and sub.get("FirstURL"):
                        results.append(
                            {
                                "title": sub.get("Text", "")[:120],
                                "url": sub.get("FirstURL", ""),
                                "snippet": sub.get("Text", ""),
                            }
                        )
                if len(results) >= max_results:
                    break
        except Exception:
            results = []

        if not results:
            html_url = f"https://html.duckduckgo.com/html/?q={quote_plus(q)}"
            try:
                async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                    r = await client.get(html_url)
                    r.raise_for_status()
                    html = r.text

                pattern = re.compile(
                    r'<a[^>]*class="result__a"[^>]*href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>.*?'
                    r'<a[^>]*class="result__snippet"[^>]*>(?P<snippet>.*?)</a>',
                    re.IGNORECASE | re.DOTALL,
                )
                tag_re = re.compile(r"<[^>]+>")
                for m in pattern.finditer(html):
                    title = tag_re.sub("", m.group("title")).strip()
                    snippet = tag_re.sub("", m.group("snippet")).strip()
                    url = m.group("url").strip()
                    results.append({"title": title, "url": url, "snippet": snippet})
                    if len(results) >= max_results:
                        break
            except Exception:
                results = []

        return {"query": query, "results": results[:max_results], "total": len(results[:max_results])}
