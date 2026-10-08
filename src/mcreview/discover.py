"""Phase 1: lexical search (Brave web search, Substack post search, Substack publication search) and host resolution."""
from __future__ import annotations

import logging
from typing import Any

from . import brave as brave_api
from . import db, substack
from .context import Ctx

log = logging.getLogger(__name__)


# ------------------------------------------------------------------ helpers shared by stages

def ingest_post_extras(ctx: Ctx, post_id: int, p: dict[str, Any]) -> None:
    """Bylines and tags from a Substack post object."""
    for b in p.get("publishedBylines") or []:
        aid = db.upsert_author(ctx.conn, b.get("id"), b.get("handle"), b.get("name"), b.get("bio"))
        if aid:
            ctx.conn.execute("INSERT OR IGNORE INTO post_bylines(post_id, author_id) VALUES (?,?)", (post_id, aid))
    for t in p.get("postTags") or []:
        name = t.get("name") if isinstance(t, dict) else t
        if name:
            ctx.conn.execute("INSERT OR IGNORE INTO post_tags(post_id, tag) VALUES (?,?)", (post_id, str(name)))


def ingest_search_post(ctx: Ctx, p: dict[str, Any], pubs_by_id: dict[int, dict], raw_ref: str, source: str) -> tuple[int | None, int | None]:
    """Upsert a post (and its publication) from a search-style post object. Returns (pub_id, post_id)."""
    pub = pubs_by_id.get(p.get("publication_id"))
    host = None
    if pub:
        host = substack.host_for(pub.get("subdomain"), pub.get("custom_domain"))
    if not host and p.get("canonical_url"):
        kind, h, _ = substack.classify_url(p["canonical_url"])
        host = h if kind in ("post", "pub_page") else None
    if not host or not p.get("slug"):
        ctx.bump("posts_skipped_no_host")
        return None, None
    fields = substack.pub_fields(pub) if pub else {}
    pub_id = db.upsert_publication(ctx.conn, host, ctx.run_id, fields, confirmed=True)
    post_fields = substack.post_fields(p, source, db.now(), raw_ref)
    post_fields["entry_round"] = 0
    post_id = db.upsert_post(ctx.conn, pub_id, p["slug"], ctx.run_id, post_fields)
    ingest_post_extras(ctx, post_id, p)
    return pub_id, post_id


def _already_run(ctx: Ctx, qid: int) -> bool:
    return ctx.conn.execute("SELECT 1 FROM search_results WHERE query_id=? LIMIT 1", (qid,)).fetchone() is not None


# ------------------------------------------------------------------ Brave web search

def _accept_brave_result(kind: str | None, host: str | None, variant: str, title: str, desc: str) -> bool:
    if kind is None or not host:
        return False
    if host.endswith(substack.SUBSTACK_SUFFIX) or kind == "open_pub":
        return True
    if not variant.startswith("open"):
        return False
    # Unfiltered query hit a non-substack.com host: accept only if it looks like a Substack page.
    return kind == "post" or "substack" in (title + " " + desc).lower()


def brave(ctx: Ctx, max_queries: int | None = None, refresh: bool = False) -> None:
    key = ctx.brave_key
    if not key:
        log.warning("BRAVE_API_KEY not set; skipping Brave discovery")
        ctx.bump("brave_skipped_no_key")
        return
    cfg = ctx.settings["phase1"]["brave"]
    variants = cfg["variants"]
    unfiltered_facets = set(cfg.get("unfiltered_facets") or [])
    pages = int(cfg["pages_per_query"])
    n_queries = 0
    for facet, term in ctx.settings.all_terms():
        for variant in variants:
            if variant.startswith("open") and facet not in unfiltered_facets:
                continue
            q = brave_api.build_query(term, variant)
            if q is None:
                continue
            if max_queries is not None and n_queries >= max_queries:
                ctx.commit()
                return
            n_queries += 1
            qid = db.get_or_create_query(ctx.conn, "brave", variant, facet, term, q)
            if not refresh and _already_run(ctx, qid):
                ctx.bump("brave_queries_skipped")
                continue
            for page in range(pages):
                r, cached = brave_api.cached_search(ctx, q, offset=page, refresh=refresh)
                ctx.bump("brave_cache_hits" if cached else "brave_requests")
                if not r.ok:
                    log.warning("brave %s page %d -> HTTP %d", q, page, r.status)
                    ctx.bump("brave_errors")
                    break
                raw_ref = ctx.store_raw(r)
                results, more = brave_api.parse_results(r.json())
                for rank, res in enumerate(results):
                    url = res.get("url") or ""
                    title, desc = res.get("title") or "", res.get("description") or ""
                    kind, host, slug = substack.classify_url(url)
                    pub_id = post_id = None
                    if _accept_brave_result(kind, host, variant, title, desc):
                        if kind == "open_pub":
                            host = host + substack.SUBSTACK_SUFFIX
                        pub_id = db.upsert_publication(ctx.conn, host, ctx.run_id, confirmed=host.endswith(substack.SUBSTACK_SUFFIX))
                        if slug:
                            post_id = db.upsert_post(
                                ctx.conn, pub_id, slug, ctx.run_id,
                                {"canonical_url": url if kind == "post" else None, "title": title, "metadata_source": "stub", "entry_round": 0},
                            )
                            db.add_discovery(ctx.conn, "post", post_id, "brave", ctx.run_id, qid, rank, page, 0)
                            ctx.bump("brave_posts")
                        else:
                            db.add_discovery(ctx.conn, "publication", pub_id, "brave", ctx.run_id, qid, rank, page, 0)
                            ctx.bump("brave_pub_pages")
                    else:
                        ctx.bump("brave_rejected")
                    ctx.conn.execute(
                        "INSERT INTO search_results(query_id, run_id, page, rank, url, title, snippet, publication_id, post_id, raw_ref) VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (qid, ctx.run_id, page, rank, url, title, desc, pub_id, post_id, raw_ref),
                    )
                ctx.commit()
                if not more or not results:
                    break
    ctx.commit()


# ------------------------------------------------------------------ Substack post search

def substack_posts(ctx: Ctx, max_queries: int | None = None, refresh: bool = False) -> None:
    cfg = ctx.settings["phase1"]["substack_search"]
    max_pages = int(cfg["max_pages_per_query"])
    cookie = ctx.cookie  # optional: adds is_ai_generated_text to results
    for i, (facet, term) in enumerate(ctx.settings.all_terms()):
        if max_queries is not None and i >= max_queries:
            break
        qid = db.get_or_create_query(ctx.conn, "substack", "substack_posts", facet, term, term)
        if not refresh and _already_run(ctx, qid):
            ctx.bump("substack_search_queries_skipped")
            continue
        seen: set[int] = set()
        for page in range(max_pages):
            r = substack.search_posts(ctx.client, term, page, cookie)
            ctx.bump("substack_search_requests")
            if not r.ok:
                log.warning("substack post search %r page %d -> HTTP %d", term, page, r.status)
                ctx.bump("substack_search_errors")
                break
            d = r.json()
            raw_ref = ctx.store_raw(r)
            pubs_by_id = {p["id"]: p for p in d.get("publications") or [] if isinstance(p, dict) and "id" in p}
            results = d.get("results") or []
            new = 0
            for rank, p in enumerate(results):
                if p.get("id") in seen:
                    continue
                seen.add(p.get("id"))
                new += 1
                pub_id, post_id = ingest_search_post(ctx, p, pubs_by_id, raw_ref, "search")
                if post_id:
                    db.add_discovery(ctx.conn, "post", post_id, "substack_posts", ctx.run_id, qid, rank, page, 0)
                    ctx.bump("substack_search_posts")
                ctx.conn.execute(
                    "INSERT INTO search_results(query_id, run_id, page, rank, url, title, snippet, publication_id, post_id, raw_ref) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (qid, ctx.run_id, page, rank, p.get("canonical_url"), p.get("title"), p.get("description"), pub_id, post_id, raw_ref),
                )
            ctx.commit()
            if not d.get("more") or not results or new == 0:
                break
    ctx.commit()


# ------------------------------------------------------------------ Substack publication search (cookie)

def substack_pubs(ctx: Ctx, max_queries: int | None = None, refresh: bool = False) -> None:
    if not ctx.cookie:
        log.warning("COOKIES_STRING not set; skipping Substack publication search")
        ctx.bump("substack_pubs_skipped_no_cookie")
        return
    cfg = ctx.settings["phase1"]["publication_search"]
    max_pages = int(cfg["max_pages_per_query"])
    for i, (facet, term) in enumerate(ctx.settings.all_terms()):
        if max_queries is not None and i >= max_queries:
            break
        qid = db.get_or_create_query(ctx.conn, "substack", "substack_pubs", facet, term, term)
        if not refresh and _already_run(ctx, qid):
            ctx.bump("substack_pubsearch_queries_skipped")
            continue
        for page in range(max_pages):
            r = substack.search_publications(ctx.client, term, page, ctx.cookie)
            ctx.bump("substack_pubsearch_requests")
            if not r.ok:
                log.warning("substack pub search %r page %d -> HTTP %d", term, page, r.status)
                break
            d = r.json()
            raw_ref = ctx.store_raw(r)
            results = d.get("results") or []
            for rank, pub in enumerate(results):
                host = substack.host_for(pub.get("subdomain"), pub.get("custom_domain"))
                if not host:
                    continue
                pid = db.upsert_publication(ctx.conn, host, ctx.run_id, substack.pub_fields(pub), confirmed=True)
                db.add_discovery(ctx.conn, "publication", pid, "substack_pubs", ctx.run_id, qid, rank, page, 0)
                ctx.conn.execute(
                    "INSERT INTO search_results(query_id, run_id, page, rank, url, title, snippet, publication_id, raw_ref) VALUES (?,?,?,?,?,?,?,?,?)",
                    (qid, ctx.run_id, page, rank, f"https://{host}/", pub.get("name"), pub.get("hero_text"), pid, raw_ref),
                )
                ctx.bump("substack_pubsearch_pubs")
            ctx.commit()
            if not d.get("more") or not results:
                break
    ctx.commit()


# ------------------------------------------------------------------ resolve hosts -> publications

def resolve(ctx: Ctx, limit: int | None = None) -> None:
    """Fetch each unresolved host's homepage; confirm it is a Substack publication, canonicalise host, fill metadata."""
    import json

    # Only hosts that carry corpus posts need resolving; publications from Substack's own API are already confirmed.
    rows = ctx.conn.execute(
        "SELECT id, host, alias_hosts FROM publications WHERE is_substack IS NULL "
        "AND id IN (SELECT publication_id FROM posts WHERE entry_round IS NOT NULL) ORDER BY id" + (f" LIMIT {int(limit)}" if limit else "")
    ).fetchall()
    for row in rows:
        pid, host = int(row["id"]), row["host"]
        r, pub = substack.fetch_homepage_pub(ctx.client, host)
        ctx.bump("resolve_requests")
        if pub is None:
            status = "not_substack" if r.ok else f"http_{r.status}" + (f" {r.error}" if r.error else "")
            ctx.conn.execute(
                "UPDATE publications SET is_substack=0, resolved_at=?, resolve_error=? WHERE id=?", (db.now(), status, pid)
            )
            # Stub posts under a non-Substack host are not corpus members; their references become plain web links.
            ctx.conn.execute("UPDATE posts SET entry_round=NULL, body_status='not_substack' WHERE publication_id=? AND body_status IS NULL", (pid,))
            ctx.conn.execute("UPDATE refs SET kind='web', target_post_id=NULL, target_publication_id=NULL, eligible=NULL WHERE kind='maybe_substack_post' AND identifier LIKE ?", (host + "/p/%",))
            ctx.bump("resolve_not_substack")
            ctx.commit()
            continue
        raw_ref = ctx.store_raw(r, "html")
        canonical = substack.host_for(pub.get("subdomain"), pub.get("custom_domain")) or host
        fields = substack.pub_fields(pub)
        # The same publication may already be known under another host (custom domain vs subdomain) or by
        # its Substack id; merge before updating so the unique constraints on host and substack_id hold.
        existing = db.get_publication_by_host(ctx.conn, canonical) if canonical != host else None
        if existing is None and fields.get("substack_id") is not None:
            existing = db.get_publication_by_substack_id(ctx.conn, int(fields["substack_id"]))
        if existing is not None and int(existing["id"]) == pid:
            existing = None
        if canonical != host or existing is not None:
            if existing is not None and int(existing["id"]) != pid:
                aliases = set(json.loads(existing["alias_hosts"] or "[]")) | set(json.loads(row["alias_hosts"] or "[]")) | {host}
                db.merge_publications(ctx.conn, int(existing["id"]), pid)
                pid = int(existing["id"])
                ctx.conn.execute("UPDATE publications SET alias_hosts=? WHERE id=?", (json.dumps(sorted(aliases)), pid))
                ctx.bump("resolve_merged")
            elif canonical != host:
                aliases = set(json.loads(row["alias_hosts"] or "[]")) | {host}
                ctx.conn.execute("UPDATE publications SET host=?, alias_hosts=? WHERE id=?", (canonical, json.dumps(sorted(aliases)), pid))
                ctx.bump("resolve_rehosted")
        sets = ", ".join(f"{k}=COALESCE(?, {k})" for k in fields)
        ctx.conn.execute(
            f"UPDATE publications SET {sets}, is_substack=1, resolved_at=?, resolve_error=NULL, raw_ref=? WHERE id=?",
            [fields[k] for k in fields] + [db.now(), raw_ref, pid],
        )
        if fields.get("author_id") or fields.get("author_handle"):
            aid = db.upsert_author(ctx.conn, fields.get("author_id"), fields.get("author_handle"), fields.get("author_name"), pub.get("author_bio"))
            if aid:
                ctx.conn.execute("INSERT OR IGNORE INTO publication_authors(publication_id, author_id, role) VALUES (?,?,?)", (pid, aid, "owner"))
        for h in {host, canonical}:
            ctx.conn.execute("UPDATE refs SET kind='substack_post', eligible=NULL WHERE kind='maybe_substack_post' AND identifier LIKE ?", (h + "/p/%",))
        ctx.bump("resolve_ok")
        ctx.commit()

