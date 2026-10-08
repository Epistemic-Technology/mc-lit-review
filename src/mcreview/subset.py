"""Stage 0: the analysis population (docs/plan.md §2, stage 0).

Applies the rules in config/analysis.yaml `subset` in order, records the count surviving each rule
(for the PRISMA figure) in the run's counts, and rebuilds `analysis_subset`.
"""
from __future__ import annotations

import json
import logging

from .context import Ctx

log = logging.getLogger(__name__)


def build(ctx: Ctx) -> dict[str, int]:
    s = ctx.settings.analysis["subset"]
    excluded = {e["host"].lower() for e in (ctx.settings.exclusions.get("hosts") or [])}
    c = ctx.conn
    counts: dict[str, int] = {}
    q = lambda sql, *a: int(c.execute(sql, a).fetchone()[0])  # noqa: E731

    counts["corpus"] = q("SELECT COUNT(*) FROM posts WHERE entry_round IS NOT NULL")
    where = ["p.entry_round IS NOT NULL"]
    args: list = []

    where.append("p.post_date >= ?")
    args.append(s["min_date"])
    counts["after_date"] = q(f"SELECT COUNT(*) FROM posts p WHERE {' AND '.join(where)}", *args)

    langs = list(s["languages"])
    where.append(f"(p.language IS NULL OR p.language IN ({','.join('?'*len(langs))}))")
    args += langs
    counts["after_language"] = q(f"SELECT COUNT(*) FROM posts p WHERE {' AND '.join(where)}", *args)

    statuses = list(s["body_status"])
    where.append(f"p.body_status IN ({','.join('?'*len(statuses))})")
    args += statuses
    counts["after_body"] = q(f"SELECT COUNT(*) FROM posts p WHERE {' AND '.join(where)}", *args)

    where.append("LENGTH(p.body_text) >= ?")
    args.append(int(s["min_body_chars"]))
    counts["after_min_chars"] = q(f"SELECT COUNT(*) FROM posts p WHERE {' AND '.join(where)}", *args)

    rows = c.execute(
        f"""SELECT p.id, p.type, p.audience, pub.host FROM posts p JOIN publications pub ON pub.id=p.publication_id
            WHERE {' AND '.join(where)} ORDER BY p.id""", args).fetchall()
    kept = []
    for r in rows:
        host = (r["host"] or "").lower()
        if host in excluded or any(host.endswith("." + h) for h in excluded):
            continue
        flags = []
        if r["audience"] == "only_paid":
            flags.append("paywalled")
        if r["type"] in ("podcast", "video"):
            flags.append(r["type"])
        kept.append((r["id"], ctx.run_id, json.dumps(flags)))
    counts["after_exclusions"] = len(kept)

    c.execute("DELETE FROM analysis_subset")
    c.executemany("INSERT INTO analysis_subset(post_id, run_id, flags) VALUES (?,?,?)", kept)
    ctx.commit()
    for k, v in counts.items():
        ctx.counts[k] = v
    log.info("analysis subset: %s", counts)
    return counts
