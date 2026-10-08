"""Body fetching for corpus posts (free posts only): metadata refresh, plain text, raw archive."""
from __future__ import annotations

import logging
import re
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from typing import Iterator

from selectolax.parser import HTMLParser

from . import db, substack
from .context import Ctx

log = logging.getLogger(__name__)
WS_RE = re.compile(r"[ \t\r\f\v]+")
NL_RE = re.compile(r"\n{3,}")
BLOCK_END_RE = re.compile(r"</(?:p|div|h[1-6]|li|blockquote|pre|tr|figcaption|figure|ul|ol|table|section|article|header|footer)\s*>", re.I)
BR_RE = re.compile(r"<br\s*/?>", re.I)


def html_to_text(html: str) -> str:
    """Plain text with paragraph breaks at block boundaries only; inline elements (links, emphasis)
    do not break lines. Derived purely from body_html, so it can be regenerated from the raw store."""
    html = BR_RE.sub("\n", BLOCK_END_RE.sub(lambda m: m.group(0) + "\n\n", html))
    tree = HTMLParser(html)
    for sel in ("script", "style", "noscript"):
        for n in tree.css(sel):
            n.decompose()
    text = tree.body.text(separator=" ") if tree.body else tree.text(separator=" ")
    text = WS_RE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return NL_RE.sub("\n\n", text).strip()


def rederive_text(ctx: Ctx) -> None:
    """Recompute body_text for every post with a stored body from the raw store (no network)."""
    import json

    rows = ctx.conn.execute("SELECT id, body_html_ref FROM posts WHERE body_html_ref IS NOT NULL").fetchall()
    for i, row in enumerate(rows, 1):
        d = json.loads(ctx.raw.get(row["body_html_ref"]))
        ctx.conn.execute("UPDATE posts SET body_text=? WHERE id=?", (html_to_text(d.get("body_html") or ""), row["id"]))
        ctx.bump("retext")
        if i % 200 == 0:
            ctx.commit()
    ctx.commit()



def _pending(ctx: Ctx, limit: int | None) -> list:
    return ctx.conn.execute(
        """
        SELECT p.id, p.slug, p.audience, pub.host FROM posts p JOIN publications pub ON pub.id=p.publication_id
        WHERE p.body_status IS NULL AND pub.is_substack=1 AND p.entry_round IS NOT NULL AND (p.post_date IS NULL OR p.post_date >= ?)
        ORDER BY p.id
        """ + (f" LIMIT {int(limit)}" if limit else ""),
        (ctx.cutoff,),
    ).fetchall()



def _reconcile_identity(ctx: Ctx, post_id: int, d: dict) -> int:
    """The post endpoint tells us the Substack ids of the post and its publication. A stub found under a
    subdomain host may be the same post/publication already known under a custom domain (or vice versa);
    merge those rows here so ids stay unique. Returns the surviving post id."""
    cur = ctx.conn.execute("SELECT publication_id FROM posts WHERE id=?", (post_id,)).fetchone()
    if cur is None:
        return post_id
    pub_sid = d.get("publication_id")
    if pub_sid is not None:
        known = db.get_publication_by_substack_id(ctx.conn, int(pub_sid))
        if known is None:
            ctx.conn.execute("UPDATE publications SET substack_id=COALESCE(substack_id, ?) WHERE id=?", (int(pub_sid), cur["publication_id"]))
        elif int(known["id"]) != int(cur["publication_id"]):
            keep, drop = int(known["id"]), int(cur["publication_id"])
            db.merge_publications(ctx.conn, keep, drop)
            ctx.bump("bodies_pub_merged")
            ctx._known_hosts = None  # type: ignore[attr-defined]
            row = ctx.conn.execute("SELECT id FROM posts WHERE id=?", (post_id,)).fetchone()
            if row is None:  # the stub was folded into an existing post during the publication merge
                row = ctx.conn.execute("SELECT id FROM posts WHERE substack_post_id=? OR (publication_id=? AND slug=?)", (d.get("id"), keep, d.get("slug"))).fetchone()
                post_id = int(row["id"]) if row else post_id
    sid = d.get("id")
    if sid is not None:
        other = ctx.conn.execute("SELECT id FROM posts WHERE substack_post_id=? AND id<>?", (int(sid), post_id)).fetchone()
        if other:
            db.merge_posts(ctx.conn, int(other["id"]), post_id)
            ctx.bump("bodies_post_merged")
            post_id = int(other["id"])
    return post_id


def fetch_bodies(ctx: Ctx, limit: int | None = None) -> None:
    rows = _pending(ctx, limit)
    # Paywalled posts: no request; record status and keep the public preview from metadata.
    paid = [r for r in rows if r["audience"] in ("only_paid", "founding")]
    for r in paid:
        ctx.conn.execute("UPDATE posts SET body_status='paywalled', body_fetched_at=? WHERE id=?", (db.now(), r["id"]))
    ctx.bump("bodies_paywalled", len(paid))
    ctx.commit()
    todo = [r for r in rows if r["audience"] not in ("only_paid", "founding")]
    workers = int(ctx.settings["bodies"].get("workers", 4))

    def work(row):
        return row, substack.fetch_post(ctx.client, row["host"], row["slug"])

    def results() -> Iterator:
        """Bounded-lookahead fan-out: only a small window of fetches is in flight, so memory stays flat,
        results are processed as they complete, and Ctrl-C stops within one window instead of after
        every queued task (ThreadPoolExecutor.map would submit everything up front)."""
        window = workers * 4
        ex = ThreadPoolExecutor(max_workers=workers)
        pending: set = set()
        it = iter(todo)
        try:
            while True:
                while len(pending) < window:
                    row = next(it, None)
                    if row is None:
                        break
                    pending.add(ex.submit(work, row))
                if not pending:
                    break
                done, pending = wait(pending, return_when=FIRST_COMPLETED)
                for fut in done:
                    yield fut.result()
        finally:
            ex.shutdown(wait=False, cancel_futures=True)

    n = 0
    for row, resp in results():
        post_id = int(row["id"])
        ctx.bump("bodies_requests")
        if resp.status == 404 or resp.status == 410:
            ctx.conn.execute("UPDATE posts SET body_status='not_found', body_fetched_at=? WHERE id=?", (db.now(), post_id))
            ctx.bump("bodies_not_found")
        elif not resp.ok:
            ctx.conn.execute("UPDATE posts SET body_status='error', body_error=?, body_fetched_at=? WHERE id=?", (f"http_{resp.status} {resp.error or ''}".strip(), db.now(), post_id))
            ctx.bump("bodies_error")
        else:
            try:
                d = resp.json()
            except ValueError:
                d = {}
            html = d.get("body_html") or ""
            post_id = _reconcile_identity(ctx, post_id, d)
            fields = substack.post_fields(d, "post", db.now(), None) if d.get("id") else {}
            fields.pop("raw_meta_ref", None)
            fields.pop("entry_round", None)
            if fields:
                # The post endpoint is authoritative for metadata too; refresh it.
                sets = ", ".join(f"{k}=COALESCE(?, {k})" for k in fields)
                ctx.conn.execute(f"UPDATE posts SET {sets} WHERE id=?", [fields[k] for k in fields] + [post_id])
            if (d.get("post_date") or "9999") < ctx.cutoff:
                # Cited older post: keep as a reference target with metadata, but outside the corpus window.
                ref = ctx.raw.put(resp.content, "json")
                ctx.conn.execute("UPDATE posts SET body_status='pre_cutoff', body_fetched_at=?, body_html_ref=? WHERE id=?", (db.now(), ref, post_id))
                ctx.bump("bodies_pre_cutoff")
            elif not html:
                status = "paywalled" if d.get("audience") in ("only_paid", "founding") else "empty"
                ctx.conn.execute("UPDATE posts SET body_status=?, body_fetched_at=? WHERE id=?", (status, db.now(), post_id))
                ctx.bump(f"bodies_{status}")
            else:
                ref = ctx.raw.put(resp.content, "json")
                text = html_to_text(html)
                ctx.conn.execute(
                    "UPDATE posts SET body_status='ok', body_fetched_at=?, body_html_ref=?, body_text=? WHERE id=?",
                    (db.now(), ref, text, post_id),
                )
                ctx.bump("bodies_ok")
        n += 1
        if n % 25 == 0:
            ctx.commit()
    ctx.commit()
