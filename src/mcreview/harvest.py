"""Optional context stage: archive metadata (no bodies) for publications with several corpus posts.

Not part of inclusion. Posts added here have entry_round NULL and a discovery source of
'archive_context'; they exist so that per-publication output shares can be computed.
"""
from __future__ import annotations

import logging

from . import db, substack
from .context import Ctx
from .discover import ingest_post_extras

log = logging.getLogger(__name__)


def archive_meta(ctx: Ctx, min_posts: int | None = None, limit: int | None = None, relevant_only: bool = False) -> None:
    """`relevant_only` restricts to publications with at least one post coded relevant (central/substantial)
    in code_final, regardless of min_posts: these are the publications that get typed and charted."""
    min_posts = int(min_posts if min_posts is not None else ctx.settings["archive_meta"]["min_corpus_posts"])
    if relevant_only:
        sql = """
        SELECT pub.id, pub.host, COUNT(p.id) n FROM publications pub JOIN posts p ON p.publication_id=pub.id
        WHERE pub.is_substack=1 AND pub.harvested_at IS NULL AND pub.id IN (
            SELECT DISTINCT p2.publication_id FROM code_final f JOIN posts p2 ON p2.id=f.entity_id
            WHERE f.entity_type='post' AND f.construct='relevance' AND f.value IN ('central','substantial'))
        GROUP BY pub.id ORDER BY n DESC"""
        args: tuple = ()
    else:
        sql = """
        SELECT pub.id, pub.host, COUNT(p.id) n FROM publications pub JOIN posts p ON p.publication_id=pub.id
        WHERE pub.is_substack=1 AND pub.harvested_at IS NULL AND p.entry_round IS NOT NULL AND p.post_date >= ?
        GROUP BY pub.id HAVING n >= ? ORDER BY n DESC"""
        args = (ctx.cutoff, min_posts)
    rows = ctx.conn.execute(sql + (f" LIMIT {int(limit)}" if limit else ""), args).fetchall()
    log.info("archive metadata for %d publications", len(rows))
    for row in rows:
        pid, host = int(row["id"]), row["host"]
        pages = in_window = 0
        error = None
        for r, posts in substack.iter_archive(ctx.client, host, ctx.cutoff):
            ctx.bump("archive_requests")
            if not r.ok:
                error = f"http_{r.status}"
                break
            pages += 1
            raw_ref = ctx.store_raw(r)
            for p in posts:
                if not p.get("slug") or (p.get("post_date") or "") < ctx.cutoff:
                    continue
                existed = ctx.conn.execute("SELECT id FROM posts WHERE publication_id=? AND slug=?", (pid, p["slug"])).fetchone()
                post_id = db.upsert_post(ctx.conn, pid, p["slug"], ctx.run_id, substack.post_fields(p, "archive", db.now(), raw_ref))
                ingest_post_extras(ctx, post_id, p)
                if not existed:
                    db.add_discovery(ctx.conn, "post", post_id, "archive_context", ctx.run_id, parent=("publication", pid))
                in_window += 1
            ctx.commit()
        ctx.conn.execute(
            "UPDATE publications SET harvested_at=?, harvest_pages=?, harvest_posts_in_window=?, harvest_error=? WHERE id=?",
            (db.now(), pages, in_window, error, pid),
        )
        ctx.bump("archive_publications")
        ctx.commit()
