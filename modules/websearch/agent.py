"""
ATHU Module - Web Search Agent
Brave Search API (free tier) or DuckDuckGo as fallback.
Playwright for page fetching and content extraction.
"""

import logging
import httpx
from typing import Callable
from modules.base_module import BaseModule

logger = logging.getLogger("athu.websearch")


class WebSearchAgent(BaseModule):
    MODULE_NAME = "websearch"

    def get_tools(self) -> list[tuple[str, dict, Callable]]:
        return [
            (
                "web_search",
                {
                    "name": "web_search",
                    "description": "Search the web for information.",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string", "description": "Search query"}},
                        "required": ["query"],
                    },
                },
                self.web_search,
            ),
            (
                "fetch_page",
                {
                    "name": "fetch_page",
                    "description": "Fetch and extract text content from a URL.",
                    "parameters": {
                        "type": "object",
                        "properties": {"url": {"type": "string", "description": "URL to fetch"}},
                        "required": ["url"],
                    },
                },
                self.fetch_page,
            ),
        ]

    async def web_search(self, query: str) -> str:
        brave_key = self.module_config.get("brave_api_key", "") or self.config["api_keys"].get("brave_search", "")
        if brave_key:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    r = await client.get(
                        "https://api.search.brave.com/res/v1/web/search",
                        params={"q": query, "count": 5},
                        headers={"Accept": "application/json", "X-Subscription-Token": brave_key},
                    )
                    r.raise_for_status()
                    results = r.json().get("web", {}).get("results", [])
                    if results:
                        lines = []
                        for i, res in enumerate(results[:5], 1):
                            lines.append(str(i) + ". " + res["title"] + " - " + res["url"])
                            if res.get("description"):
                                lines.append("   " + res["description"][:200])
                        return "Search results for: " + query + "\n" + "\n".join(lines)
            except Exception as e:
                logger.warning("Brave Search failed: " + str(e) + ". Trying DuckDuckGo.")
        # DuckDuckGo fallback (no API key required)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    "https://api.duckduckgo.com/",
                    params={"q": query, "format": "json", "no_html": "1"},
                )
                data = r.json()
                abstract = data.get("AbstractText", "")
                if abstract:
                    return "DuckDuckGo: " + abstract[:500]
                return "No results found for: " + query
        except Exception as e:
            return "Web search failed: " + str(e)

    async def fetch_page(self, url: str) -> str:
        # TODO: Phase 2 - implement full Playwright page fetch
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                r = await client.get(url, headers={"User-Agent": "ATHU/0.1"})
                r.raise_for_status()
                # Basic text extraction (Playwright integration in Phase 2)
                text = r.text[:3000]
                return "Page content from " + url + ":\n" + text
        except Exception as e:
            return "Failed to fetch " + url + ": " + str(e)
