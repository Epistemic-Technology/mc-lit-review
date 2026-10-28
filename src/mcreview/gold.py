"""Stage 2: frozen random samples for human verification, and the export the coder tool reads.

Samples are drawn once per name with the configured seed and stored in `gold_samples`; re-running
`sample` for an existing name is a no-op. Strata: discovery channel class x year x engagement band,
allocated proportionally, so the human checks reflect the population and not just recent posts.
"""
from __future__ import annotations

import json
import logging
import random
from collections import defaultdict
from pathlib import Path

from . import db
from .codebook import Codebook
from .context import Ctx

log = logging.getLogger(__name__)


def _stratum(ctx: Ctx, post_id: int, channels: dict[str, list[str]], bands: list[int], cache: dict) -> str:
    if post_id in cache:
        return cache[post_id]
    r = ctx.conn.execute("SELECT substr(post_date,1,4) y, reaction_count FROM posts WHERE id=?", (post_id,)).fetchone()
    srcs = {s[0] for s in ctx.conn.execute("SELECT DISTINCT source FROM discovery WHERE entity_type='post' AND entity_id=?", (post_id,))}
    chan = next((name for name, lst in channels.items() if srcs & set(lst)), "other")
    rc = r["reaction_count"] or 0
    band = sum(1 for b in bands if rc >= b)
    cache[post_id] = f"{chan}|{r['y']}|e{band}"
    return cache[post_id]


def _axes_shift_population(ctx: Ctx, cb: Codebook, shift: dict) -> list[int]:
    """Relevant posts where the axis coded at 0.2.0 is in `coded` while the same axis derived from the retired
    0.1.0 items (mcreview.axes.derive) is in `derived`: the cells of the derived-versus-coded matrix on the
    Methods page that a human should look at."""
    from .axes import derive
    from .export import stance_item_names

    items = set(stance_item_names(cb))
    axis = shift["axis"]
    rel = {int(r[0]) for r in ctx.conn.execute(
        "SELECT entity_id FROM code_final WHERE entity_type='post' AND construct='relevance' AND value IN ('central','substantial')")}
    old: dict[int, dict] = defaultdict(dict)
    coded: dict[int, str] = {}
    for eid, con, val in ctx.conn.execute("SELECT entity_id, construct, value FROM code_final WHERE entity_type='post'"):
        if int(eid) not in rel:
            continue
        if con in items:
            old[int(eid)][con] = val
        elif con == axis:
            coded[int(eid)] = "not_addressed" if val == "reports_only" else val
    want_d, want_c = set(shift["derived"]), set(shift["coded"])
    return sorted(pid for pid, c in coded.items() if c in want_c and derive(old.get(pid, {}))[axis] in want_d)


def _coded_population(ctx: Ctx, spec: dict) -> dict[str, list[int]]:
    """Relevant posts whose coder-of-record value on `coded.construct` is one of `coded.values`, keyed by that value
    (the stratum). `body_like`, if given, keeps only posts whose body matches at least one SQL LIKE pattern: used for
    a false-negative check (coded none, but the text has the phrases the construct is about)."""
    c = spec["coded"]
    q = ",".join("?" * len(c["values"]))
    sql = f"""SELECT f.value, f.entity_id FROM code_final f JOIN code_final r ON r.entity_type='post' AND r.entity_id=f.entity_id AND r.construct='relevance'
              JOIN posts p ON p.id=f.entity_id
              WHERE f.entity_type='post' AND f.construct=? AND f.value IN ({q}) AND r.value IN ('central','substantial')"""
    args: list = [c["construct"], *c["values"]]
    likes = spec.get("body_like") or []
    if likes:
        sql += " AND (" + " OR ".join("p.body_text LIKE ?" for _ in likes) + ")"
        args += list(likes)
    out: dict[str, list[int]] = defaultdict(list)
    for val, eid in ctx.conn.execute(sql + " ORDER BY f.entity_id", args):
        out[val].append(int(eid))
    return out


def _allocate(strata: dict[str, list[int]], n: int, fixed: dict[str, int] | None = None) -> dict[str, int]:
    """How many to draw per stratum: the configured counts, capped by availability, else proportional allocation
    with largest-remainder rounding."""
    if fixed:
        return {k: min(int(fixed.get(k, 0)), len(v)) for k, v in strata.items()}
    total = sum(len(v) for v in strata.values())
    alloc = {k: n * len(v) / total for k, v in strata.items()}
    take = {k: int(a) for k, a in alloc.items()}
    for k in sorted(alloc, key=lambda k: alloc[k] - take[k], reverse=True)[: n - sum(take.values())]:
        take[k] += 1
    return take


def sample(ctx: Ctx, name: str) -> int:
    cfg = ctx.settings.analysis["gold"]
    spec = cfg["samples"][name]
    cb = Codebook()
    if ctx.conn.execute("SELECT COUNT(*) FROM gold_samples WHERE sample_name=?", (name,)).fetchone()[0]:
        log.info("sample %s already drawn; frozen", name)
        return 0
    pop = spec["population"]
    if pop == "subset":
        et, ids = "post", [int(r[0]) for r in ctx.conn.execute("SELECT post_id FROM analysis_subset ORDER BY post_id")]
    elif pop == "relevant":
        et, ids = "post", [int(r[0]) for r in ctx.conn.execute(
            "SELECT entity_id FROM code_final WHERE entity_type='post' AND construct='relevance' AND value IN ('central','substantial') ORDER BY entity_id")]
    elif pop == "publications_relevant":
        et, ids = "publication", [int(r[0]) for r in ctx.conn.execute(
            """SELECT DISTINCT p.publication_id FROM code_final f JOIN posts p ON p.id=f.entity_id
               WHERE f.entity_type='post' AND f.construct='relevance' AND f.value IN ('central','substantial') ORDER BY 1""")]
    elif pop == "axes_shift":
        et, ids = "post", _axes_shift_population(ctx, cb, spec["shift"])
    elif pop == "coded":
        coded = _coded_population(ctx, spec)
        et, ids = "post", [pid for v in coded.values() for pid in v]
    else:
        raise ValueError(pop)
    if not ids:
        raise RuntimeError(f"population '{pop}' is empty; run the earlier stages first")
    n = min(int(spec["n"]), len(ids))
    rng = random.Random(f"{cfg['seed']}:{name}")
    rows = []
    if pop == "axes_shift":
        # A targeted check, not a population estimate: simple random draw, stratum records the shift.
        s = spec["shift"]
        rng.shuffle(ids)
        rows = [(pid, f"{s['axis']}:{'/'.join(s['derived'])}>{'/'.join(s['coded'])}") for pid in ids[:n]]
    elif pop == "coded":
        # A targeted check of the codes, not a population estimate: stratum is the coded value, counts per value
        # from `allocation` when given.
        take = _allocate(coded, n, spec.get("allocation"))
        for k, v in coded.items():
            rng.shuffle(v)
            rows += [(pid, f"{spec['coded']['construct']}={k}") for pid in v[: take[k]]]
    elif et == "post":
        cache: dict = {}
        strata: dict[str, list[int]] = defaultdict(list)
        for pid in ids:
            strata[_stratum(ctx, pid, cfg["strata"]["channel"], list(cfg["strata"]["engagement_bands"]), cache)].append(pid)
        take = _allocate(strata, n)
        for k, v in strata.items():
            rng.shuffle(v)
            rows += [(pid, k) for pid in v[: take[k]]]
    else:
        rng.shuffle(ids)
        rows = [(i, None) for i in ids[:n]]
    rng.shuffle(rows)
    now = db.now()
    ctx.conn.executemany(
        "INSERT INTO gold_samples(sample_name, entity_type, entity_id, stratum, position, sampled_at, run_id, codebook_version) VALUES (?,?,?,?,?,?,?,?)",
        [(name, et, eid, st, i, now, ctx.run_id, cb.version) for i, (eid, st) in enumerate(rows)])
    ctx.commit()
    ctx.counts[f"sampled_{name}"] = len(rows)
    log.info("sample %s: %d %ss from %d", name, len(rows), et, len(ids))
    return len(rows)


def export(ctx: Ctx, name: str, out: Path, lead_chars: int = 1500) -> Path:
    """JSON for the coder tool: each sampled item with what the human needs to see and the engine codes to verify."""
    from .code import _jev_mean

    cb = Codebook()
    spec = ctx.settings.analysis["gold"]["samples"][name]
    cons = spec.get("constructs")
    items = []
    first = ctx.conn.execute("SELECT entity_type FROM gold_samples WHERE sample_name=? LIMIT 1", (name,)).fetchone()
    jev_mean = _jev_mean(ctx, cb, first["entity_type"]) if first else {}
    for s in ctx.conn.execute("SELECT * FROM gold_samples WHERE sample_name=? ORDER BY position", (name,)):
        eid = int(s["entity_id"])
        item: dict = {"sample_id": int(s["id"]), "entity_type": s["entity_type"], "entity_id": eid, "stratum": s["stratum"]}
        if s["entity_type"] == "post":
            p = ctx.conn.execute("SELECT title, subtitle, canonical_url, post_date, body_text FROM posts WHERE id=?", (eid,)).fetchone()
            item.update({"title": p["title"], "subtitle": p["subtitle"], "url": p["canonical_url"], "date": p["post_date"],
                         "lead": (p["body_text"] or "")[:lead_chars], "body": p["body_text"] or ""})
            if spec.get("body_like"):   # the phrases that put the post in the sample, for the coder tool to highlight
                body_l = (p["body_text"] or "").lower()
                item["hits"] = [ph for ph in (x.strip("%") for x in spec["body_like"]) if ph.lower() in body_l]
        else:
            from .code import state_for_publication

            item.update(state_for_publication(ctx, eid))
        # Engine codes for the human to verify: Claude where it coded the item, else Jev's averaged code.
        # Read from the engines' own codes, not code_final, where an earlier human decision would replace them.
        codes = {}
        for con, val, ev, ver in ctx.conn.execute(
            """SELECT c.construct, c.value, c.evidence, r.codebook_version FROM codes c JOIN code_runs r ON r.id=c.code_run_id
               WHERE r.engine='claude' AND c.entity_type=? AND c.entity_id=? ORDER BY c.coded_at""",
            (s["entity_type"], eid)):
            if cb.accepts(con, ver, s["entity_type"], val) and (not cons or con in cons):
                codes[con] = {"value": val, "evidence": ev, "source": "claude"}
        if not codes:
            for (e, con), (val, p, conf, _) in jev_mean.items():
                if e == eid and (not cons or con in cons):
                    codes[con] = {"value": val, "evidence": None, "source": "jev"}
        item["codes"] = codes
        existing = {g["construct"]: dict(g) for g in ctx.conn.execute("SELECT * FROM gold_codes WHERE sample_id=?", (s["id"],))}
        item["human"] = existing
        items.append(item)
    all_cons = cb.constructs if items and items[0]["entity_type"] == "post" else cb.publication_constructs
    defs = [{"name": c.name, "group": c.group, "primitive": c.primitive, "instructions": c.instructions, "claim": c.claim,
             "options": {k: v.get("what", "") for k, v in (c.options or c.criteria or {}).items()} or {"true": "", "false": ""}}
            for c in all_cons if not cons or c.name in cons]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"sample": name, "codebook_version": cb.version, "constructs": defs, "items": items}, ensure_ascii=False, indent=1))
    log.info("exported %d items to %s", len(items), out)
    return out


def import_codes(ctx: Ctx, path: Path) -> int:
    """Read the coder tool's output ({sample_id: {construct: {value, decision, note, seconds}}}) into gold_codes."""
    cb = Codebook()
    data = json.loads(Path(path).read_text())
    now = db.now()
    n = 0
    for sid, cons in data.items():
        for con, d in cons.items():
            ctx.conn.execute(
                """INSERT OR REPLACE INTO gold_codes(sample_id, construct, value, decision, shown_value, shown_evidence, note, seconds, coded_at, codebook_version)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (int(sid), con, d.get("value"), d.get("decision"), d.get("shown_value"), d.get("shown_evidence"), d.get("note"), d.get("seconds"), d.get("coded_at") or now, cb.version))
            n += 1
    ctx.commit()
    ctx.counts["gold_codes_imported"] = n
    return n


def human_agreement(ctx: Ctx) -> list[dict]:
    """Engine vs human on the verified items, per construct and per engine, over the random samples only.
    Targeted samples (`targeted: true` in the config, or names starting `shift_`: drawn from specific cells of the
    derived-versus-coded matrix, or from the non-none codes of one construct) are excluded: they are checks on
    those cells, not population estimates. Reads the engines' own codes
    (not code_final, where human decisions replace engine values once materialised)."""
    from .code import _claude_codes, _jev_mean

    cb = Codebook()
    targeted = {n for n, sp in ctx.settings.analysis["gold"]["samples"].items() if sp.get("targeted") or n.startswith("shift_")}
    per: dict[tuple[str, str], list[bool]] = defaultdict(list)
    for et in ("post", "publication"):
        engines = {"jev": {k: v[0] for k, v in _jev_mean(ctx, cb, et).items()}, "claude": {k: v[0] for k, v in _claude_codes(ctx, cb, et).items()}}
        for eid, con, hv, sname in ctx.conn.execute(
            "SELECT s.entity_id, g.construct, g.value, s.sample_name FROM gold_codes g JOIN gold_samples s ON s.id=g.sample_id WHERE s.entity_type=? AND g.value IS NOT NULL", (et,)):
            if sname in targeted:
                continue
            key = (int(eid), con)
            for name, codes in engines.items():
                if key in codes:
                    per[(con, name)].append(codes[key] == hv)
    return [{"construct": k[0], "source": k[1], "n": len(v), "agree": sum(v) / len(v)} for k, v in sorted(per.items())]
