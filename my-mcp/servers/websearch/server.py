import os
import time
import asyncio
from typing import Any, Dict, List

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel

try:
    # Use FastMCP, which provides the @tool decorator API
    from mcp.server.fastmcp import FastMCP
except Exception as e:
    raise SystemExit(
        "Pacote 'mcp' não encontrado. Instale com: pip install mcp\n" f"Detalhes: {e}"
    )


class RateLimiter:
    def __init__(self, rate_per_sec: float, burst: int):
        self.capacity = float(burst)
        self.tokens = float(burst)
        self.rate = float(rate_per_sec)
        self.timestamp = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.timestamp
            self.timestamp = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            if self.tokens < 1.0:
                wait_time = (1.0 - self.tokens) / self.rate if self.rate > 0 else 0
                await asyncio.sleep(max(0, wait_time))
                self.tokens = 0.0
            else:
                self.tokens -= 1.0


WEB_RPS = float(os.getenv("WEB_RPS", "1"))
WEB_BURST = int(os.getenv("WEB_BURST", "5"))
_limiter = RateLimiter(WEB_RPS, WEB_BURST)

server = FastMCP(name="mcp-web-search")


class SearchItem(BaseModel):
    title: str | None = None
    link: str
    snippet: str | None = None


class WebSearchResponse(BaseModel):
    results: List[SearchItem]


class FetchUrlResponse(BaseModel):
    url: str
    title: str | None = None
    text: str


async def _google_search(query: str, site: str | None, limit: int) -> List[Dict[str, Any]]:
    api_key = os.getenv("GOOGLE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")
    if not api_key or not cse_id:
        raise RuntimeError("GOOGLE_API_KEY e GOOGLE_CSE_ID são obrigatórios.")

    q = query
    if site:
        q = f"site:{site} {query}"

    params = {
        "key": api_key,
        "cx": cse_id,
        "q": q,
        "num": max(1, min(10, int(limit))),
    }

    timeout = float(os.getenv("WEB_SEARCH_TIMEOUT", "10"))
    async with httpx.AsyncClient(timeout=timeout) as client:
        await _limiter.acquire()
        resp = await client.get("https://www.googleapis.com/customsearch/v1", params=params)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        results = []
        for it in items:
            results.append(
                {
                    "title": it.get("title"),
                    "link": it.get("link"),
                    "snippet": it.get("snippet"),
                }
            )
        return results


async def _fetch_and_clean(url: str, max_chars: int) -> Dict[str, Any]:
    timeout = float(os.getenv("WEB_FETCH_TIMEOUT", "10"))
    headers = {"User-Agent": "mcp-web-search/0.1"}
    async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True) as client:
        await _limiter.acquire()
        resp = await client.get(url)
        resp.raise_for_status()
        html = resp.text

    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    # Remove script/style
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = " ".join(soup.get_text(" ").split())
    if len(text) > max_chars:
        text = text[:max_chars] + "…"
    return {"title": title, "text": text}


@server.tool(
    name="web_search",
    description="Busca na web via Google CSE e retorna resultados.",
)
async def tool_web_search(
    query: str,
    site: str | None = None,
    limit: int | None = None,
) -> WebSearchResponse:
    try:
        default_limit = int(os.getenv("WEB_SEARCH_LIMIT", "5"))
        results = await _google_search(query, site, limit or default_limit)
        items = [
            SearchItem(title=r.get("title"), link=r.get("link", ""), snippet=r.get("snippet"))
            for r in results
            if r.get("link")
        ]
        return WebSearchResponse(results=items)
    except Exception:
        return WebSearchResponse(results=[])


@server.tool(
    name="fetch_url",
    description="Busca conteúdo de uma URL e retorna texto limpo e metadados.",
)
async def tool_fetch_url(url: str, max_chars: int | None = None) -> FetchUrlResponse:
    try:
        maxc = int(os.getenv("WEB_FETCH_MAX_CHARS", "8000")) if max_chars is None else int(max_chars)
        data = await _fetch_and_clean(url, maxc)
        return FetchUrlResponse(url=url, title=data.get("title"), text=data.get("text", ""))
    except Exception as e:
        return FetchUrlResponse(url=url, title=None, text=f"Erro: {e}")


def main_cli() -> None:
    server.run("stdio")


if __name__ == "__main__":
    main_cli()

