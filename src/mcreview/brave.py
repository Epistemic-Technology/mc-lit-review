"""Brave Search API wrapper. https://api.search.brave.com/res/v1/web/search"""
from __future__ import annotations

from urllib.parse import urlencode

from .http import Client, Response

ENDPOINT = "https://api.search.brave.com/res/v1/web/search"


def search(client: Client, api_key: str, query: str, offset: int = 0, count: int = 20) -> Response:
    url = ENDPOINT + "?" + urlencode({"q": query, "count": count, "offset": offset, "text_decorations": 0})
    return client.get(url, headers={"X-Subscription-Token": api_key, "Accept": "application/json"})


def cached_search(ctx, query: str, offset: int = 0, refresh: bool = False) -> tuple[Response, bool]:
    """Brave search through the exact-URL cache. Returns (response, from_cache).

    Only successful responses are cached. `ctx` is a Ctx (imported lazily to avoid a cycle)."""
    from . import db

    url = ENDPOINT + "?" + urlencode({"q": query, "count": 20, "offset": offset, "text_decorations": 0})
    use_cache = bool(ctx.settings.get("brave_cache", default=True)) and not refresh
    if use_cache:
        row = ctx.conn.execute("SELECT status, raw_ref FROM http_cache WHERE url=?", (url,)).fetchone()
        if row:
            return Response(url, url, int(row["status"]), ctx.raw.get(row["raw_ref"]), 0, 0), True
    r = ctx.client.get(url, headers={"X-Subscription-Token": ctx.brave_key, "Accept": "application/json"})
    if r.ok and bool(ctx.settings.get("brave_cache", default=True)):
        ref = ctx.raw.put(r.content, "json")
        ctx.conn.execute("INSERT OR REPLACE INTO http_cache(url, status, raw_ref, fetched_at) VALUES (?,?,?,?)", (url, r.status, ref, db.now()))
    return r, False


def query_text_already_run(ctx, text: str) -> bool:
    """True if a query with identical text (any variant/term) already has stored results."""
    return ctx.conn.execute(
        "SELECT 1 FROM queries q JOIN search_results s ON s.query_id=q.id WHERE q.backend='brave' AND q.text=? LIMIT 1", (text,)
    ).fetchone() is not None


def parse_results(payload: dict) -> tuple[list[dict], bool]:
    web = (payload.get("web") or {}).get("results") or []
    more = bool((payload.get("query") or {}).get("more_results_available"))
    return web, more


def build_query(term: str, variant: str) -> str | None:
    """Query text for a term under a named variant; None if the variant does not apply."""
    if variant == "site_quoted":
        return f'site:substack.com "{term}"'
    if variant == "site_plain":
        return f"site:substack.com {term}" if " " in term else None
    if variant == "open_quoted":
        return f'"{term}" substack'
    raise ValueError(variant)
