"""Publication enrichment for the publications that matter (those with relevant posts).

Publication typing (stage 4) was starved of information: 349 of the 1,600 relevant publications had no
name or author handle (never resolved through their homepage), bios were linked to posts rather than
publications, and no archive titles had been harvested. This stage fills the gaps from public endpoints:
1. homepage `_preloads` -> name, tagline, author, author bio (publications missing name or handle);
2. author public profile -> bio (owner authors without one);
3. `harvest.archive_meta(relevant_only=True)` is the companion for titles back to the cutoff.
"""
from __future__ import annotations

import logging

from . import db, substack
from .context import Ctx

log = logging.getLogger(__name__)

RELEVANT_PUBS_SQL = """
    SELECT DISTINCT p.publication_id FROM code_final f JOIN posts p ON p.id=f.entity_id
    WHERE f.entity_type='post' AND f.construct='relevance' AND f.value IN ('central','substantial')
"""


def relevant_publication_ids(ctx: Ctx) -> list[int]:
    return [int(r[0]) for r in ctx.conn.execute(RELEVANT_PUBS_SQL)]


def enrich_publications(ctx: Ctx, limit: int | None = None, profiles: bool = True) -> None:
    ids = relevant_publication_ids(ctx)
    c = ctx.conn
    # 1. homepage metadata for publications with no name or no author handle
    rows = c.execute(
        f"SELECT id, host FROM publications WHERE id IN ({','.join('?'*len(ids))}) AND is_substack=1 "
        "AND (name IS NULL OR name='' OR author_handle IS NULL) ORDER BY id" + (f" LIMIT {int(limit)}" if limit else ""), ids).fetchall()
    log.info("homepage metadata for %d publications", len(rows))
    for row in rows:
        pid, host = int(row["id"]), row["host"]
        r, pub = substack.fetch_homepage_pub(ctx.client, host)
        ctx.bump("enrich_homepage_requests")
        if pub is None:
            ctx.bump("enrich_homepage_miss")
            continue
        raw_ref = ctx.store_raw(r, "html")
        fields = substack.pub_fields(pub)
        fields.pop("substack_id", None)  # identity was settled at resolve time; never touch unique keys here
        fields.pop("subdomain", None)
        fields.pop("custom_domain", None)
        sets = ", ".join(f"{k}=COALESCE(?, {k})" for k in fields)
        c.execute(f"UPDATE publications SET {sets}, raw_ref=COALESCE(raw_ref, ?) WHERE id=?", [fields[k] for k in fields] + [raw_ref, pid])
        if fields.get("author_id") or fields.get("author_handle"):
            aid = db.upsert_author(c, fields.get("author_id"), fields.get("author_handle"), fields.get("author_name"), pub.get("author_bio"))
            if aid:
                c.execute("INSERT OR IGNORE INTO publication_authors(publication_id, author_id, role) VALUES (?,?,?)", (pid, aid, "owner"))
        ctx.bump("enrich_homepage_ok")
        ctx.commit()
    # 2. owner link from the publication's own author fields, where the link is missing
    c.execute(
        f"""INSERT OR IGNORE INTO publication_authors(publication_id, author_id, role)
            SELECT u.id, a.id, 'owner' FROM publications u JOIN authors a ON (a.substack_user_id=u.author_id OR a.handle=u.author_handle)
            WHERE u.id IN ({','.join('?'*len(ids))})""", ids)
    ctx.commit()
    if not profiles:
        return
    # 3. public profiles for owner authors without a bio
    rows = c.execute(
        f"""SELECT DISTINCT a.id, a.handle FROM authors a JOIN publication_authors pa ON pa.author_id=a.id
            WHERE pa.publication_id IN ({','.join('?'*len(ids))}) AND a.handle IS NOT NULL AND (a.bio IS NULL OR a.bio='') AND a.profile_fetched_at IS NULL
            ORDER BY a.id""" + (f" LIMIT {int(limit)}" if limit else ""), ids).fetchall()
    log.info("public profiles for %d authors", len(rows))
    for row in rows:
        r, profile, _pubs = substack.public_profile(ctx.client, row["handle"])
        ctx.bump("enrich_profile_requests")
        bio = (profile or {}).get("bio") if isinstance(profile, dict) else None
        raw_ref = ctx.store_raw(r) if r.ok else None
        c.execute("UPDATE authors SET bio=COALESCE(?, bio), profile_fetched_at=?, raw_ref=COALESCE(?, raw_ref) WHERE id=?", (bio or None, db.now(), raw_ref, int(row["id"])))
        ctx.bump("enrich_profile_bio" if bio else "enrich_profile_nobio")
        ctx.commit()
