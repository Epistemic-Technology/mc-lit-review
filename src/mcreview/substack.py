"""Thin wrappers over Substack's public JSON endpoints and page-embedded data.

All endpoints below were verified anonymously on 2026-09-26 (see PLAN.md §2). Nothing here
authenticates except where a cookie is explicitly passed, and no paywall is ever bypassed.
"""
from __future__ import annotations

import json
import re
from typing import Any, Iterator
from urllib.parse import urlsplit

from .http import Client, Response

SUBSTACK_SUFFIX = ".substack.com"
PRELOADS_RE = re.compile(r'window\._preloads\s*=\s*JSON\.parse\("(.*?)"\)\s*(?:</script>|;)', re.S)
POST_PATH_RE = re.compile(r"^/p/([^/?#]+)")
OPEN_PUB_RE = re.compile(r"^/pub/([^/?#]+)(?:/p/([^/?#]+))?")


# ------------------------------------------------------------------ helpers

def normalize_host(host: str) -> str:
    return host.lower().strip().rstrip(".")


def host_for(subdomain: str | None, custom_domain: str | None) -> str | None:
    if custom_domain:
        return normalize_host(custom_domain)
    if subdomain:
        return normalize_host(subdomain) + SUBSTACK_SUFFIX
    return None


def pub_fields(pub: dict[str, Any]) -> dict[str, Any]:
    """Map a Substack publication object (from any endpoint) onto our publications columns."""
    return {
        "substack_id": pub.get("id"),
        "subdomain": pub.get("subdomain"),
        "custom_domain": pub.get("custom_domain"),
        "name": pub.get("name"),
        "hero_text": pub.get("hero_text"),
        "author_name": pub.get("author_name") or (pub.get("author") or {}).get("name"),
        "author_handle": pub.get("author_handle") or (pub.get("author") or {}).get("handle"),
        "author_id": pub.get("author_id") or pub.get("primary_user_id"),
        "language": pub.get("language"),
        "type": pub.get("type"),
        "created_at_substack": pub.get("created_at"),
        "first_post_date": pub.get("first_post_date"),
        "free_subscriber_magnitude": pub.get("freeSubscriberCountOrderOfMagnitude"),
    }


def post_fields(p: dict[str, Any], source: str, fetched_at: str, raw_ref: str | None) -> dict[str, Any]:
    audience = p.get("audience")
    return {
        "substack_post_id": p.get("id"),
        "canonical_url": p.get("canonical_url"),
        "title": p.get("title"),
        "subtitle": p.get("subtitle"),
        "description": p.get("description"),
        "post_date": p.get("post_date"),
        "type": p.get("type"),
        "audience": audience,
        "is_paywalled": None if audience is None else int(audience in ("only_paid", "founding")),
        "wordcount": p.get("wordcount"),
        "language": p.get("language"),
        "section_name": p.get("section_name"),
        "reaction_count": p.get("reaction_count"),
        "comment_count": p.get("comment_count"),
        "restack_count": p.get("restacks"),
        "cover_image": p.get("cover_image"),
        "is_ai_generated_text": (None if p.get("is_ai_generated_text") is None else int(bool(p["is_ai_generated_text"]))),
        "truncated_body_text": p.get("truncated_body_text"),
        "metadata_source": source,
        "metadata_fetched_at": fetched_at,
        "raw_meta_ref": raw_ref,
    }


def parse_preloads(html: str) -> dict[str, Any] | None:
    m = PRELOADS_RE.search(html)
    if not m:
        return None
    try:
        return json.loads(json.loads('"' + m.group(1) + '"'))
    except json.JSONDecodeError:
        return None


def classify_url(url: str) -> tuple[str | None, str | None, str | None]:
    """Return (kind, host_or_subdomain, slug) for a URL.

    kind: 'post' (host, slug), 'pub_page' (host, None), 'open_pub' (subdomain, slug|None), or None.
    'open_pub' means an open.substack.com/pub/<subdomain>/... link, common in cross-references.
    """
    try:
        u = urlsplit(url)
    except ValueError:
        return None, None, None
    host = normalize_host(u.hostname or "")
    if not host:
        return None, None, None
    if host in ("open.substack.com", "substack.com", "www.substack.com"):
        m = OPEN_PUB_RE.match(u.path)
        if m:
            return "open_pub", m.group(1).lower(), m.group(2)
        return None, None, None
    m = POST_PATH_RE.match(u.path)
    if m:
        return "post", host, m.group(1)
    return "pub_page", host, None


# ------------------------------------------------------------------ endpoints

def fetch_homepage_pub(client: Client, host: str) -> tuple[Response, dict[str, Any] | None]:
    """Fetch https://<host>/ and return the embedded `pub` object, or None if not a Substack site."""
    r = client.get(f"https://{host}/")
    if not r.ok:
        return r, None
    pre = parse_preloads(r.text())
    pub = (pre or {}).get("pub")
    if not isinstance(pub, dict) or "subdomain" not in pub:
        return r, None
    return r, pub


def archive_page(client: Client, host: str, offset: int, limit: int = 20) -> Response:
    return client.get(f"https://{host}/api/v1/archive?sort=new&search=&offset={offset}&limit={limit}")


def iter_archive(client: Client, host: str, cutoff: str, max_pages: int = 1000) -> Iterator[tuple[Response, list[dict]]]:
    """Yield (response, posts) per page, newest first, stopping after the first page whose posts
    all predate `cutoff` (ISO date string). Pinned posts can appear out of order, so the stop rule
    is 'every post on the page is older', not 'the last one is'."""
    offset = 0
    seen: set[int] = set()
    for _ in range(max_pages):
        r = archive_page(client, host, offset)
        if not r.ok:
            yield r, []
            return
        try:
            posts = r.json()
        except ValueError:
            yield r, []
            return
        if not isinstance(posts, list) or not posts:
            return
        ids = {p.get("id") for p in posts}
        if ids <= seen:  # endpoint looping back on itself
            return
        seen |= ids
        yield r, posts
        if all((p.get("post_date") or "") < cutoff for p in posts):
            return
        offset += len(posts)


def fetch_post(client: Client, host: str, slug: str) -> Response:
    return client.get(f"https://{host}/api/v1/posts/{slug}")


def search_posts(client: Client, query: str, page: int, cookie: str | None = None) -> Response:
    from urllib.parse import quote_plus

    url = (
        "https://substack.com/api/v1/post/search?query="
        f"{quote_plus(query)}&includePlatformResults=true&filter=all&page={page}"
    )
    return client.get(url, headers={"Cookie": cookie} if cookie else None)


def search_publications(client: Client, query: str, page: int, cookie: str) -> Response:
    from urllib.parse import quote_plus

    return client.get(
        f"https://substack.com/api/v1/publication/search?query={quote_plus(query)}&page={page}",
        headers={"Cookie": cookie},
    )


def categories(client: Client) -> Response:
    return client.get("https://substack.com/api/v1/categories")


def category_page(client: Client, category_id: int | str, page: int) -> Response:
    return client.get(f"https://substack.com/api/v1/category/public/{category_id}/all?page={page}")


def recommendations(client: Client, host: str) -> tuple[Response, list[dict[str, Any]]]:
    """Publications this publication recommends, from the /recommendations page's embedded data."""
    r = client.get(f"https://{host}/recommendations")
    if not r.ok:
        return r, []
    pre = parse_preloads(r.text()) or {}
    out = []
    for item in pre.get("recommendations") or []:
        rp = item.get("recommendedPublication") if isinstance(item, dict) else None
        if isinstance(rp, dict) and rp.get("subdomain"):
            out.append(rp)
    return r, out


def public_profile(client: Client, handle: str) -> tuple[Response, dict[str, Any] | None, list[dict[str, Any]]]:
    """Author profile plus the publications they write for (any role)."""
    r = client.get(f"https://substack.com/api/v1/user/{handle}/public_profile")
    if not r.ok:
        return r, None, []
    try:
        prof = r.json()
    except ValueError:
        return r, None, []
    pubs: list[dict[str, Any]] = []
    for pu in prof.get("publicationUsers") or []:
        pub = pu.get("publication") if isinstance(pu, dict) else None
        if isinstance(pub, dict) and pub.get("subdomain"):
            pub = dict(pub)
            pub["_role"] = pu.get("role")
            pubs.append(pub)
    return r, prof, pubs
