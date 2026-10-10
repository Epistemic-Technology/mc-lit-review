"""Phase 2: citation-based expansion.

Round r:
  1. extract_references  - links from newly fetched bodies -> refs / post_refs; recount citing_posts
  2. backward            - cited Substack posts enter the corpus directly (citation chasing)
  3. fill/fetch titles   - for over-threshold references that need one (arXiv API, DOI CSL, page <title>)
  4. update_eligibility  - which references may serve as coupling targets
  5. coupling            - Brave queries per eligible reference; results enter the corpus coupled to it
Then the CLI resolves new publications and fetches new bodies, and the next round begins.
"""
from __future__ import annotations

import json
import logging
import re

from selectolax.parser import HTMLParser

from . import brave as brave_api
from . import db, refs as refs_mod, substack
from .context import Ctx
from .screen import Screen

log = logging.getLogger(__name__)


def _html_title(html: str) -> str | None:
    """citation_title (scholarly pages, arXiv) > og:title > <title>."""
    tree = HTMLParser(html)
    for sel, attr in (('meta[name="citation_title"]', "content"), ('meta[property="og:title"]', "content")):
        n = tree.css_first(sel)
        if n and n.attributes.get(attr):
            return n.attributes[attr]
    t = tree.css_first("title")
    return t.text() if t else None


def _cfg(ctx: Ctx):
    return ctx.settings["citation"]


def _known_hosts(ctx: Ctx) -> tuple[set[str], dict[str, str]]:
    """(confirmed Substack hosts incl. aliases, alias -> canonical host map)."""
    hosts: set[str] = set()
    host_map: dict[str, str] = {}
    for host, aliases, sub in ctx.conn.execute("SELECT host, alias_hosts, subdomain FROM publications WHERE is_substack=1"):
        hosts.add(host)
        for a in json.loads(aliases or "[]"):
            hosts.add(a)
            host_map[a] = host
        if sub:
            s = sub + substack.SUBSTACK_SUFFIX
            hosts.add(s)
            if s != host:
                host_map[s] = host
    return hosts, host_map


# ------------------------------------------------------------------ 1. references

def gate_sources(ctx: Ctx) -> None:
    """Decide which fetched posts may contribute references (settings.citation.source_gating)."""
    gating = bool(_cfg(ctx).get("source_gating", True))
    screen = Screen(ctx.settings.all_terms())
    rows = ctx.conn.execute(
        "SELECT id, entry_round, title, subtitle, body_text FROM posts WHERE body_status='ok' AND source_eligible IS NULL AND entry_round IS NOT NULL"
    ).fetchall()
    for row in rows:
        if not gating or row["entry_round"] == 0:
            ok, why = 1, "phase1" if row["entry_round"] == 0 else "ungated"
        else:
            routes = ctx.conn.execute(
                "SELECT COUNT(DISTINCT source) FROM discovery WHERE entity_type='post' AND entity_id=?", (row["id"],)
            ).fetchone()[0]
            if routes >= 2:
                ok, why = 1, "multi_route"
            else:
                score, _terms = screen.score("\n".join(x or "" for x in (row["title"], row["subtitle"], row["body_text"])))
                ok, why = (1, "keyword") if score else (0, "no_evidence")
        ctx.conn.execute("UPDATE posts SET source_eligible=? WHERE id=?", (ok, row["id"]))
        ctx.bump(f"source_{why}")
    ctx.commit()


def extract_references(ctx: Ctx) -> None:
    gate_sources(ctx)
    known, host_map = _known_hosts(ctx)
    rows = ctx.conn.execute(
        "SELECT id, body_html_ref FROM posts WHERE body_status='ok' AND refs_extracted_at IS NULL AND entry_round IS NOT NULL "
        "AND source_eligible=1 AND post_date >= ?",
        (ctx.cutoff,),
    ).fetchall()
    for i, row in enumerate(rows, 1):
        d = json.loads(ctx.raw.get(row["body_html_ref"]))
        tree = HTMLParser(d.get("body_html") or "")
        for a in tree.css("a[href]"):
            href = (a.attributes.get("href") or "").strip()
            ref = refs_mod.normalize(href, known, host_map)
            if ref is None:
                continue
            anchor = re.sub(r"\s+", " ", a.text() or "").strip()[:300] or None
            ctx.conn.execute(
                "INSERT OR IGNORE INTO refs(url_norm, kind, identifier, domain, title, title_source, first_seen_run) VALUES (?,?,?,?,?,?,?)",
                (ref.url_norm, ref.kind, ref.identifier, ref.domain, ref.title, ref.title_source, ctx.run_id),
            )
            rid = ctx.conn.execute("SELECT id FROM refs WHERE url_norm=?", (ref.url_norm,)).fetchone()[0]
            ctx.conn.execute(
                "INSERT OR IGNORE INTO post_refs(post_id, ref_id, url, anchor_text) VALUES (?,?,?,?)",
                (row["id"], rid, href[:2000], anchor),
            )
            ctx.bump("refs_links")
        ctx.conn.execute("UPDATE posts SET refs_extracted_at=? WHERE id=?", (db.now(), row["id"]))
        ctx.bump("refs_posts")
        if i % 100 == 0:
            ctx.commit()
    recount(ctx)


def recount(ctx: Ctx) -> None:
    ctx.conn.execute("UPDATE refs SET citing_posts=(SELECT COUNT(*) FROM post_refs pr WHERE pr.ref_id=refs.id)")
    ctx.conn.execute(
        "UPDATE refs SET citing_pubs=(SELECT COUNT(DISTINCT p.publication_id) FROM post_refs pr JOIN posts p ON p.id=pr.post_id WHERE pr.ref_id=refs.id)"
    )
    ctx.commit()


def _threshold_clause(ctx: Ctx) -> tuple[str, tuple[int, int]]:
    cfg = _cfg(ctx)
    return "citing_posts >= ? AND citing_pubs >= ?", (int(cfg["min_citing_posts"]), int(cfg.get("min_citing_publications", 1)))


def link_substack_targets(ctx: Ctx) -> None:
    """Point substack_post references at posts/publications already in the database."""
    rows = ctx.conn.execute("SELECT id, identifier FROM refs WHERE kind IN ('substack_post','maybe_substack_post') AND target_post_id IS NULL").fetchall()
    for row in rows:
        host, _, slug = row["identifier"].partition("/p/")
        pub = db.get_publication_by_host(ctx.conn, host)
        if pub is None:
            alias = ctx.conn.execute("SELECT id FROM publications WHERE alias_hosts LIKE ?", (f'%"{host}"%',)).fetchone()
            pub = alias
        if pub is None:
            continue
        post = ctx.conn.execute("SELECT id, title FROM posts WHERE publication_id=? AND slug=?", (pub["id"], slug)).fetchone()
        ctx.conn.execute("UPDATE refs SET target_publication_id=? WHERE id=?", (pub["id"], row["id"]))
        if post:
            ctx.conn.execute(
                "UPDATE refs SET target_post_id=?, title=COALESCE(title, ?), title_source=COALESCE(title_source, CASE WHEN ? IS NULL THEN NULL ELSE 'post' END) WHERE id=?",
                (post["id"], post["title"], post["title"], row["id"]),
            )
    # refresh titles for already-linked targets whose post has since been fetched
    ctx.conn.execute(
        "UPDATE refs SET title=(SELECT title FROM posts WHERE posts.id=refs.target_post_id), title_source='post' "
        "WHERE kind='substack_post' AND title IS NULL AND target_post_id IS NOT NULL AND (SELECT title FROM posts WHERE posts.id=refs.target_post_id) IS NOT NULL"
    )
    ctx.commit()


# ------------------------------------------------------------------ 2. backward citation chasing

def backward(ctx: Ctx, round_no: int) -> int:
    cfg = _cfg(ctx)
    # The cap is per round, not per invocation: a resumed round only takes what is left of its allowance.
    already = ctx.conn.execute("SELECT COUNT(*) FROM refs WHERE backward_round=?", (round_no,)).fetchone()[0]
    remaining = max(0, int(cfg["max_backward_per_round"]) - int(already))
    rows = ctx.conn.execute(
        "SELECT id, identifier, url_norm, citing_posts FROM refs WHERE kind IN ('substack_post','maybe_substack_post') AND target_post_id IS NULL "
        "AND backward_round IS NULL AND citing_posts >= ? ORDER BY citing_posts DESC, id LIMIT ?",
        (int(cfg["backward_min_citing_posts"]), remaining),
    ).fetchall()
    added = 0
    for row in rows:
        host, _, slug = row["identifier"].partition("/p/")
        pub_id = db.upsert_publication(ctx.conn, host, ctx.run_id, confirmed=host.endswith(substack.SUBSTACK_SUFFIX))
        post_id = db.upsert_post(ctx.conn, pub_id, slug, ctx.run_id,
                                 {"canonical_url": row["url_norm"], "metadata_source": "stub", "entry_round": round_no})
        citing = ctx.conn.execute("SELECT post_id FROM post_refs WHERE ref_id=? ORDER BY post_id LIMIT 1", (row["id"],)).fetchone()
        db.add_discovery(ctx.conn, "post", post_id, "cited_by", ctx.run_id, hop_depth=round_no,
                         parent=("post", int(citing[0])) if citing else None, detail=f"ref:{row['id']} citing_posts:{row['citing_posts']}")
        ctx.conn.execute("UPDATE refs SET target_post_id=?, target_publication_id=?, backward_round=? WHERE id=?", (post_id, pub_id, round_no, row["id"]))
        added += 1
    ctx.bump("backward_posts", added)
    ctx.commit()
    return added


# ------------------------------------------------------------------ 3. titles

def fetch_titles(ctx: Ctx) -> None:
    cfg = _cfg(ctx)
    if not cfg.get("fetch_titles", True):
        return
    clause, params = _threshold_clause(ctx)
    cap = int(cfg.get("max_title_fetches_per_round", 1500))
    fast = dict(retries=1, timeout=float(cfg.get("title_fetch_timeout_seconds", 10)))
    rows = ctx.conn.execute(
        f"SELECT id, kind, identifier, url_norm FROM refs WHERE (title IS NULL OR title_source IN ('anchor','brave')) AND title_fetched_at IS NULL AND {clause} "
        "AND kind IN ('arxiv','doi','web','book') AND (eligible IS NULL OR eligible=1 OR block_reason='no_title') "
        "ORDER BY citing_pubs DESC, citing_posts DESC, id LIMIT ?",
        params + (cap,),
    ).fetchall()
    for row in rows:
        title, source, err = None, None, None
        try:
            if row["kind"] == "arxiv":
                # The export API answers 406 to non-browser clients; the abstract page carries citation_title.
                r = ctx.client.get(row["url_norm"], headers={"Accept": "text/html,*/*;q=0.8"}, **fast)
                t = _html_title(r.text()) if r.ok else None
                t = re.sub(r"^\[\d{4}\.\d{4,5}(v\d+)?\]\s*", "", t) if t else None
                title, source, err = (t, "arxiv_page", None) if t else (None, None, f"http_{r.status}")
            elif row["kind"] == "doi":
                r = ctx.client.get(row["url_norm"], headers={"Accept": "application/vnd.citationstyles.csl+json"}, **fast)
                if r.ok:
                    try:
                        title, source = (r.json().get("title") or None), "doi_csl"
                    except ValueError:
                        title = None
                if not title:
                    r = ctx.client.get(row["url_norm"], headers={"Accept": "text/html,*/*;q=0.8"}, **fast)
                    t = _html_title(r.text()) if r.ok else None
                    title, source, err = (t, "doi_page", None) if t else (None, None, f"http_{r.status}")
            else:
                r = ctx.client.get(row["url_norm"], headers={"Accept": "text/html,*/*;q=0.8"}, **fast)
                t = _html_title(r.text()) if r.ok else None
                title, source, err = (t, "page", None) if t else (None, None, f"http_{r.status}" if not r.ok else "no_title")
        except Exception as e:  # noqa: BLE001 - title fetching must never abort a round
            err = f"{type(e).__name__}: {e}"[:200]
        title = refs_mod.clean_title(title)
        ctx.conn.execute(
            "UPDATE refs SET title=?, title_source=?, title_fetched_at=?, title_error=? WHERE id=?",
            (title, source if title else None, db.now(), err, row["id"]),
        )
        ctx.bump("titles_ok" if title else "titles_missing")
        ctx.commit()


# ------------------------------------------------------------------ 4. eligibility

def update_eligibility(ctx: Ctx) -> None:
    cfg = _cfg(ctx)
    kinds = set(cfg["target_kinds"])
    blocked = set(cfg.get("blocked_domains") or [])
    title_pats = [re.compile(p, re.I) for p in (cfg.get("blocked_title_patterns") or [])]
    rows = ctx.conn.execute("SELECT id, kind, domain, title, title_source, identifier FROM refs WHERE eligible IS NULL OR eligible=0 OR searched_round IS NULL").fetchall()
    for row in rows:
        reason = None
        # anchor-text titles (titles.py) name a work for display but are not evidence enough to search by
        title = (refs_mod.clean_title(row["title"]) or "") if row["title_source"] != "anchor" else ""
        if row["kind"] not in kinds:
            reason = f"kind:{row['kind']}"
        elif row["domain"] in blocked and row["kind"] not in ("substack_post", "book"):
            reason = f"blocked_domain:{row['domain']}"
        elif title and any(p.search(title) for p in title_pats):
            reason = "generic_title"
        elif row["kind"] in ("web", "book") and len(title) < 15:
            reason = "no_title"
        ctx.conn.execute("UPDATE refs SET eligible=?, block_reason=? WHERE id=?", (int(reason is None), reason, row["id"]))
    ctx.commit()


# ------------------------------------------------------------------ 5. coupling search

def coupling(ctx: Ctx, round_no: int) -> int:
    cfg = _cfg(ctx)
    key = ctx.brave_key
    if not key:
        log.warning("BRAVE_API_KEY not set; coupling search skipped")
        return 0
    clause, params = _threshold_clause(ctx)
    pages = int(cfg["brave_pages_per_query"])
    already = ctx.conn.execute("SELECT COUNT(*) FROM refs WHERE searched_round=?", (round_no,)).fetchone()[0]
    rows = ctx.conn.execute(
        f"SELECT id, kind, identifier, url_norm, title, citing_posts FROM refs WHERE eligible=1 AND searched_round IS NULL AND {clause} "
        "ORDER BY citing_pubs DESC, citing_posts DESC, id LIMIT ?",
        params + (max(0, int(cfg["max_targets_per_round"]) - int(already)),),
    ).fetchall()
    new_posts = 0
    for row in rows:
        for variant, q in refs_mod.coupling_queries(row["kind"], row["identifier"], row["url_norm"], row["title"]):
            if brave_api.query_text_already_run(ctx, q):
                ctx.bump("coupling_queries_deduped")
                continue
            qid = db.get_or_create_query(ctx.conn, "brave", variant, "citation", row["url_norm"], q)
            for page in range(pages):
                r, cached = brave_api.cached_search(ctx, q, offset=page)
                ctx.bump("coupling_cache_hits" if cached else "coupling_requests")
                if not r.ok:
                    log.warning("brave %s page %d -> HTTP %d", q, page, r.status)
                    ctx.bump("coupling_errors")
                    break
                raw_ref = ctx.store_raw(r)
                results, more = brave_api.parse_results(r.json())
                for rank, res in enumerate(results):
                    url = res.get("url") or ""
                    kind, host, slug = substack.classify_url(url)
                    pub_id = post_id = None
                    if kind == "open_pub" and slug:
                        host, kind = host + substack.SUBSTACK_SUFFIX, "post"
                    if kind == "post" and host and slug and host.endswith(substack.SUBSTACK_SUFFIX):
                        existed = ctx.conn.execute(
                            "SELECT p.id FROM posts p JOIN publications pub ON pub.id=p.publication_id WHERE pub.host=? AND p.slug=?", (host, slug)
                        ).fetchone()
                        pub_id = db.upsert_publication(ctx.conn, host, ctx.run_id, confirmed=True)
                        post_id = db.upsert_post(ctx.conn, pub_id, slug, ctx.run_id,
                                                 {"canonical_url": url, "title": res.get("title"), "metadata_source": "stub", "entry_round": round_no})
                        db.add_discovery(ctx.conn, "post", post_id, "coupling", ctx.run_id, qid, rank, page, round_no, detail=f"ref:{row['id']}")
                        if not existed:
                            new_posts += 1
                        ctx.bump("coupling_hits")
                    ctx.conn.execute(
                        "INSERT INTO search_results(query_id, run_id, page, rank, url, title, snippet, publication_id, post_id, raw_ref) VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (qid, ctx.run_id, page, rank, url, res.get("title"), res.get("description"), pub_id, post_id, raw_ref),
                    )
                if not more or not results:
                    break
        ctx.conn.execute("UPDATE refs SET searched_round=? WHERE id=?", (round_no, row["id"]))
        ctx.bump("coupling_targets")
        ctx.commit()
    ctx.bump("coupling_new_posts", new_posts)
    return new_posts


# ------------------------------------------------------------------ round driver

def next_round_number(ctx: Ctx) -> int:
    """The round to run: an unfinished cite_round run (interrupted/errored) is resumed; otherwise the next one."""
    last = ctx.conn.execute(
        "SELECT status, args_json FROM runs WHERE stage='cite_round' AND id<>? ORDER BY id DESC LIMIT 1", (ctx.run_id,)
    ).fetchone()
    if last is not None:
        try:
            r = int(json.loads(last["args_json"] or "{}").get("round"))
        except (TypeError, ValueError):
            r = None
        if r is not None:
            return r if last["status"] != "ok" else r + 1
    row = ctx.conn.execute("SELECT MAX(entry_round) FROM posts").fetchone()
    return int(row[0] or 0) + 1


def run_round(ctx: Ctx, round_no: int) -> int:
    """One citation round. Returns the number of posts newly added (backward + coupling)."""
    extract_references(ctx)
    link_substack_targets(ctx)
    added = backward(ctx, round_no)
    link_substack_targets(ctx)
    update_eligibility(ctx)
    fetch_titles(ctx)
    update_eligibility(ctx)
    added += coupling(ctx, round_no)
    return added
