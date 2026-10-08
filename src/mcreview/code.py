"""Stage 3/4: machine coding of posts and publications (docs/plan.md).

Idempotent: an item is coded once per (engine, model, codebook version, repeat). Re-running a command
picks up what is missing. Every engine response is stored raw; parsed answers go to `codes`.
`materialise` builds `code_final` (the coder of record per construct) and `agreement` compares engines.
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import db
from .codebook import Codebook, Construct
from .context import Ctx
from .engines import EngineResult

log = logging.getLogger(__name__)

RELEVANT = ("central", "substantial")


# ---------------------------------------------------------------- state builders

def state_for_post(row, body_max_chars: int) -> dict:
    body = row["body_text"] or ""
    truncated = len(body) > body_max_chars
    if truncated:
        body = body[:body_max_chars] + "\n\n[TRUNCATED]"
    return {"title": row["title"] or "", "subtitle": row["subtitle"] or "", "body": body}


def state_for_publication(ctx: Ctx, pub_id: int, max_titles: int = 30) -> dict:
    """Name, tagline, author bios (owner and byline authors), and recent post titles. Titles include
    archive-context posts (entry_round NULL) when the archive-meta stage has run, so the publication's
    recurring subject is visible, not just the posts that matched our queries."""
    c = ctx.conn
    pub = c.execute("SELECT name, hero_text, author_name, host FROM publications WHERE id=?", (pub_id,)).fetchone()
    bios = [r[0] for r in c.execute(
        """SELECT DISTINCT a.bio FROM authors a
           WHERE a.bio IS NOT NULL AND a.bio<>'' AND a.id IN (
               SELECT author_id FROM publication_authors WHERE publication_id=?
               UNION SELECT b.author_id FROM post_bylines b JOIN posts p ON p.id=b.post_id WHERE p.publication_id=?)
           LIMIT 3""", (pub_id, pub_id))]
    n_posts = c.execute("SELECT COUNT(*) FROM posts WHERE publication_id=? AND title IS NOT NULL", (pub_id,)).fetchone()[0]
    titles = [r[0] for r in c.execute(
        "SELECT title FROM posts WHERE publication_id=? AND title IS NOT NULL ORDER BY post_date DESC LIMIT ?", (pub_id, max_titles))]
    return {"name": pub["name"] or "", "host": pub["host"], "tagline": pub["hero_text"] or "", "author": pub["author_name"] or "",
            "author_bios": bios, "post_titles": titles, "posts_known": int(n_posts)}


# ---------------------------------------------------------------- engines

def make_engine(ctx: Ctx, name: str, cb: Codebook):
    a = ctx.settings.analysis["coding"]
    if name == "jev":
        from .engines.jev import JevEngine

        j = a["jev"]
        return JevEngine(ctx.creds.get("TYPESAFE_API_KEY") or "", cb, j["model"], j["base_url"], j.get("timeout_seconds", 60),
                         j.get("price_per_mtok_input", 0.042), int(j.get("seed", 0)), ctx.settings["http"]["user_agent"])
    if name == "claude":
        k = a["claude"]
        if k.get("transport", "cli") == "cli":
            from .engines.claude_code import ClaudeCodeEngine

            return ClaudeCodeEngine(cb, k["model"], k.get("effort", "medium"), float(k.get("timeout_seconds", 600)), k.get("cli", "claude"),
                                    float(k.get("rate_limit_wait_seconds", 300)), int(k.get("rate_limit_retries", 12)))
        from .engines.claude import ClaudeEngine

        return ClaudeEngine(cb, k["model"], int(k.get("max_tokens", 8000)), k.get("effort", "medium"), bool(k.get("fallbacks", True)),
                            float(k.get("timeout_seconds", 300)), ctx.creds.get("ANTHROPIC_API_KEY"))
    raise ValueError(f"unknown engine {name}")


def engine_model(ctx: Ctx, name: str) -> str:
    return str(ctx.settings.analysis["coding"][name]["model"])


def start_code_run(ctx: Ctx, engine: str, model: str, cb: Codebook, target: str, config: dict) -> int:
    version = cb.pub_code_version if target == "publications" else cb.version
    cur = ctx.conn.execute(
        "INSERT INTO code_runs(run_id, engine, model, codebook_version, target, config_json, started_at) VALUES (?,?,?,?,?,?,?)",
        (ctx.run_id, engine, model, version, target, json.dumps(config, default=str), db.now()))
    ctx.conn.commit()
    return int(cur.lastrowid)


def store_result(ctx: Ctx, code_run_id: int, entity_type: str, entity_id: int, repeat_no: int, res: EngineResult) -> None:
    raw_ref = ctx.raw.put(res.raw, "json")
    now = db.now()
    ctx.conn.executemany(
        """INSERT OR REPLACE INTO codes(code_run_id, entity_type, entity_id, construct, repeat_no, value, probability, confidence, distribution_json, evidence, raw_ref, coded_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        [(code_run_id, entity_type, entity_id, a.construct, repeat_no, a.value, a.probability, a.confidence,
          json.dumps(a.distribution) if a.distribution else None, a.evidence, raw_ref, now) for a in res.answers.values()])
    ctx.conn.execute(
        "UPDATE code_runs SET n_items=n_items+1, input_tokens=input_tokens+?, output_tokens=output_tokens+?, cost_usd=cost_usd+? WHERE id=?",
        (res.input_tokens, res.output_tokens, res.cost_usd, code_run_id))


def finish_code_run(ctx: Ctx, code_run_id: int) -> None:
    ctx.conn.execute("UPDATE code_runs SET finished_at=? WHERE id=?", (db.now(), code_run_id))
    ctx.commit()


# ---------------------------------------------------------------- selection

def _coded(ctx: Ctx, engine: str, model: str, version: str, entity_type: str, repeat_no: int) -> set[int]:
    return {int(r[0]) for r in ctx.conn.execute(
        """SELECT DISTINCT c.entity_id FROM codes c JOIN code_runs r ON r.id=c.code_run_id
           WHERE r.engine=? AND r.model=? AND r.codebook_version=? AND c.entity_type=? AND c.repeat_no=?""",
        (engine, model, version, entity_type, repeat_no))}


def jev_relevance(ctx: Ctx, version: str) -> dict[int, float]:
    """post_id -> mean over repeats of p(central)+p(substantial) from Jev codes at this codebook version."""
    acc: dict[int, list[float]] = defaultdict(list)
    for pid, dist in ctx.conn.execute(
        """SELECT c.entity_id, c.distribution_json FROM codes c JOIN code_runs r ON r.id=c.code_run_id
           WHERE r.engine='jev' AND r.codebook_version=? AND c.entity_type='post' AND c.construct='relevance' AND c.distribution_json IS NOT NULL""", (version,)):
        d = json.loads(dist)
        acc[int(pid)].append(sum(float(d.get(k, 0.0)) for k in RELEVANT))
    return {k: sum(v) / len(v) for k, v in acc.items()}


def select_posts(ctx: Ctx, engine: str, model: str, version: str, repeat_no: int, only_relevant: bool,
                 limit: int | None, post_ids: list[int] | None) -> list:
    done = _coded(ctx, engine, model, version, "post", repeat_no)
    sql = "SELECT p.id, p.title, p.subtitle, p.body_text FROM analysis_subset s JOIN posts p ON p.id=s.post_id"
    args: list = []
    if post_ids:
        sql += f" WHERE p.id IN ({','.join('?'*len(post_ids))})"
        args += post_ids
    sql += " ORDER BY p.id"
    rows = [r for r in ctx.conn.execute(sql, args) if int(r["id"]) not in done]
    if only_relevant:
        rel = jev_relevance(ctx, version)
        thr = float(ctx.settings.analysis["coding"]["claude"].get("relevance_min_prob", 0.25))
        rows = [r for r in rows if rel.get(int(r["id"]), 0.0) >= thr]
    return rows[:limit] if limit else rows


# ---------------------------------------------------------------- coding

def code_posts(ctx: Ctx, engine_name: str, limit: int | None = None, repeats: int | None = None, dry_run: bool = False,
               only_relevant: bool = False, post_ids: list[int] | None = None, batch: bool = False,
               constructs: list[str] | None = None) -> None:
    cb = Codebook()
    cons = [cb.get(n) for n in constructs] if constructs else cb.constructs
    a = ctx.settings.analysis["coding"]
    model = engine_model(ctx, engine_name)
    n_rep = repeats if repeats is not None else (int(a["jev"].get("repeats", 1)) if engine_name == "jev" else 1)
    body_max = int(a["body_max_chars"])
    work: list[tuple[int, int]] = []           # (repeat_no, post_id)
    rows_by_id: dict[int, object] = {}
    for rep in range(n_rep):
        rows = select_posts(ctx, engine_name, model, cb.version, rep, only_relevant, limit, post_ids)
        for r in rows:
            rows_by_id[int(r["id"])] = r
            work.append((rep, int(r["id"])))
    cli = engine_name == "claude" and a["claude"].get("transport", "cli") == "cli"
    if batch and cli:
        raise RuntimeError("--batch needs coding.claude.transport: api; the Claude Code CLI has no batch mode")
    if dry_run:
        chars = sum(min(len(rows_by_id[pid]["body_text"] or ""), body_max) for _, pid in work)
        est_tok = chars / 4 + (14000 if cli else 2500) * len(work)   # + questions/system (and Claude Code's own context) per request
        pi = a["jev"].get("price_per_mtok_input", 0.042) if engine_name == "jev" else {"claude-opus-5-5": 4.0, "claude-sonnet-5-5": 2.0, "claude-haiku-4-5": 1.0}.get(model, 4.0)
        mult = 0.5 if (batch and engine_name == "claude") else 1.0
        note = " via Claude Code subscription (list-price equivalent; no charge, but counts against the usage window)" if cli else (" (batch, output not counted)" if engine_name == "claude" else "")
        log.info("dry run: %s x %d repeats -> %d requests, ~%.1fM input tokens, ~$%.2f input%s", engine_name, n_rep, len(work), est_tok / 1e6, est_tok / 1e6 * pi * mult, note)
        ctx.counts["dry_run_requests"] = len(work)
        return
    if not work:
        log.info("nothing to code for %s", engine_name)
        return
    engine = make_engine(ctx, engine_name, cb)
    code_run_id = start_code_run(ctx, engine_name, model, cb, "posts", {"repeats": n_rep, "only_relevant": only_relevant, "limit": limit, "batch": batch, "constructs": constructs})
    if batch and engine_name == "claude":
        items = [(f"post:{pid}:{rep}", state_for_post(rows_by_id[pid], body_max)) for rep, pid in work]
        bid = engine.submit_batch(items, cons)
        ctx.conn.execute("UPDATE code_runs SET batch_id=? WHERE id=?", (bid, code_run_id))
        ctx.commit()
        log.info("batch %s submitted for code run %d (%d items); collect later with `mcreview code-collect %d`", bid, code_run_id, len(work), code_run_id)
        ctx.counts["batch_submitted"] = len(work)
        return
    conc = int(a[engine_name].get("concurrency", 4))
    _run_pool(ctx, engine, code_run_id, "post", cons, [(rep, pid, state_for_post(rows_by_id[pid], body_max)) for rep, pid in work], conc)
    finish_code_run(ctx, code_run_id)


def code_publications(ctx: Ctx, engine_name: str, limit: int | None = None, dry_run: bool = False, relevant_only: bool = True) -> None:
    cb = Codebook()
    cons = cb.publication_constructs
    model = engine_model(ctx, engine_name)
    done = _coded(ctx, engine_name, model, cb.pub_code_version, "publication", 0)
    if relevant_only:
        sql = """SELECT DISTINCT p.publication_id FROM code_final f JOIN posts p ON p.id=f.entity_id
                 WHERE f.entity_type='post' AND f.construct='relevance' AND f.value IN ('central','substantial')"""
    else:
        sql = "SELECT DISTINCT p.publication_id FROM analysis_subset s JOIN posts p ON p.id=s.post_id"
    ids = [int(r[0]) for r in ctx.conn.execute(sql) if int(r[0]) not in done]
    ids = ids[:limit] if limit else ids
    if dry_run:
        log.info("dry run: %d publications to code with %s", len(ids), engine_name)
        return
    if not ids:
        log.info("no publications to code")
        return
    engine = make_engine(ctx, engine_name, cb)
    code_run_id = start_code_run(ctx, engine_name, model, cb, "publications", {"limit": limit, "relevant_only": relevant_only})
    conc = int(ctx.settings.analysis["coding"][engine_name].get("concurrency", 4))
    _run_pool(ctx, engine, code_run_id, "publication", cons, [(0, pid, state_for_publication(ctx, pid)) for pid in ids], conc)
    finish_code_run(ctx, code_run_id)


def _run_pool(ctx: Ctx, engine, code_run_id: int, entity_type: str, cons: list[Construct], items: list[tuple[int, int, dict]], conc: int) -> None:
    """Engine calls in threads; all DB and raw-store writes on the main thread. Stops on a fatal engine
    error (credentials, billing) or after `max_consecutive_errors` failures in a row; everything stored
    so far is kept and a re-run resumes from there."""
    from .engines import FatalEngineError

    n = 0
    consecutive = 0
    max_consecutive = int(ctx.settings.analysis["coding"].get("max_consecutive_errors", 20))
    with ThreadPoolExecutor(max_workers=max(1, conc)) as pool:
        futs = {pool.submit(engine.code, state, cons, rep, eid): (rep, eid) for rep, eid, state in items}
        try:
            for fut in as_completed(futs):
                rep, eid = futs[fut]
                try:
                    res = fut.result()
                except FatalEngineError as e:
                    log.error("%s: fatal, stopping run: %s", engine.name, e)
                    ctx.counts[f"{engine.name}_fatal"] = str(e)[:200]  # type: ignore[assignment]
                    break
                except Exception as e:  # noqa: BLE001
                    log.warning("%s %s %d rep %d failed: %s", engine.name, entity_type, eid, rep, e)
                    ctx.bump(f"{engine.name}_errors")
                    consecutive += 1
                    if consecutive >= max_consecutive:
                        log.error("%s: %d consecutive errors, stopping run", engine.name, consecutive)
                        break
                    continue
                consecutive = 0
                store_result(ctx, code_run_id, entity_type, eid, rep, res)
                ctx.bump(f"{engine.name}_coded")
                n += 1
                if n % 50 == 0:
                    ctx.commit()
                if n % 500 == 0:
                    log.info("%s: %d of %d coded", engine.name, n, len(items))
        finally:
            for f in futs:
                f.cancel()
    ctx.commit()


def collect(ctx: Ctx, code_run_id: int) -> None:
    """Fetch results of a submitted Claude batch and store them."""
    r = ctx.conn.execute("SELECT * FROM code_runs WHERE id=?", (code_run_id,)).fetchone()
    if r is None or not r["batch_id"]:
        raise RuntimeError(f"code run {code_run_id} has no batch id")
    cb = Codebook()
    cfg = json.loads(r["config_json"] or "{}")
    cons = [cb.get(n) for n in cfg.get("constructs")] if cfg.get("constructs") else cb.constructs
    engine = make_engine(ctx, "claude", cb)
    status, counts = engine.batch_status(r["batch_id"])
    log.info("batch %s: %s %s", r["batch_id"], status, counts)
    if status != "ended":
        ctx.counts["batch_status"] = status  # type: ignore[assignment]
        return
    for cid, res, err in engine.collect_batch(r["batch_id"], cons):
        _, eid, rep = cid.split(":")
        if res is None:
            log.warning("%s: %s", cid, err)
            ctx.bump("batch_errors")
            continue
        store_result(ctx, code_run_id, "post", int(eid), int(rep), res)
        ctx.bump("batch_collected")
    finish_code_run(ctx, code_run_id)


# ---------------------------------------------------------------- final codes and agreement

def _jev_mean(ctx: Ctx, version: str, entity_type: str) -> dict[tuple[int, str], tuple[str, float, float, dict]]:
    """(entity, construct) -> (argmax value, p(value), mean confidence, mean distribution) over repeats."""
    acc: dict[tuple[int, str], list[tuple[dict, float | None]]] = defaultdict(list)
    for eid, con, dist, conf, val, prob in ctx.conn.execute(
        """SELECT c.entity_id, c.construct, c.distribution_json, c.confidence, c.value, c.probability FROM codes c JOIN code_runs r ON r.id=c.code_run_id
           WHERE r.engine='jev' AND r.codebook_version=? AND c.entity_type=?""", (version, entity_type)):
        d = json.loads(dist) if dist else {val: prob or 1.0}
        acc[(int(eid), con)].append((d, conf))
    out = {}
    for key, lst in acc.items():
        keys = set().union(*[d.keys() for d, _ in lst])
        mean = {k: sum(float(d.get(k, 0.0)) for d, _ in lst) / len(lst) for k in keys}
        best = max(mean, key=mean.get)
        confs = [c for _, c in lst if c is not None]
        conf = sum(confs) / len(confs) if confs else (len(mean) * mean[best] - 1) / max(1, len(mean) - 1)
        out[key] = (best, mean[best], conf, mean)
    return out


def _claude_codes(ctx: Ctx, version: str, entity_type: str) -> dict[tuple[int, str], tuple[str, str | None]]:
    out = {}
    for eid, con, val, ev in ctx.conn.execute(
        """SELECT c.entity_id, c.construct, c.value, c.evidence FROM codes c JOIN code_runs r ON r.id=c.code_run_id
           WHERE r.engine='claude' AND r.codebook_version=? AND c.entity_type=? ORDER BY c.coded_at""", (version, entity_type)):
        out[(int(eid), con)] = (val, ev)   # latest wins
    return out


def materialise(ctx: Ctx) -> None:
    """code_final: human gold > Claude (coder of record where present) > Jev above its construct threshold > Jev."""
    cb = Codebook()
    thr: dict[str, float] = ctx.settings.analysis.get("thresholds") or {}
    now = db.now()
    rows = []
    for et in ("post", "publication"):
        ver = cb.code_version(et)
        jev = _jev_mean(ctx, ver, et)
        cl = _claude_codes(ctx, ver, et)
        gold = {}
        # Human decisions are keyed on the base codebook version; a publication rubric revision does not
        # invalidate them (the human judged the publication, not the rubric wording).
        for eid, con, val in ctx.conn.execute(
            "SELECT s.entity_id, g.construct, g.value FROM gold_codes g JOIN gold_samples s ON s.id=g.sample_id WHERE s.entity_type=? AND g.codebook_version=? AND g.value IS NOT NULL", (et, cb.version)):
            gold[(int(eid), con)] = val
        for key in set(jev) | set(cl) | set(gold):
            eid, con = key
            if key in gold:
                rows.append((et, eid, con, gold[key], None, "human", ver, now))
            elif key in cl:
                rows.append((et, eid, con, cl[key][0], None, "claude", ver, now))
            else:
                val, p, conf, _ = jev[key]
                rows.append((et, eid, con, val, p, "jev" if conf >= thr.get(con, 0.0) else "jev_low", ver, now))
    ctx.conn.execute("DELETE FROM code_final WHERE codebook_version IN (?, ?)", (cb.version, cb.pub_code_version))
    ctx.conn.executemany("INSERT OR REPLACE INTO code_final VALUES (?,?,?,?,?,?,?,?)", rows)
    ctx.commit()
    ctx.counts["code_final_rows"] = len(rows)
    for src, n in ctx.conn.execute("SELECT source, COUNT(*) FROM code_final WHERE codebook_version IN (?, ?) GROUP BY 1", (cb.version, cb.pub_code_version)):
        ctx.counts[f"final_{src}"] = int(n)


def agreement(ctx: Ctx, entity_type: str = "post") -> list[dict]:
    """Per construct: Jev vs Claude agreement on items both coded, and agreement/coverage above confidence cut-offs."""
    cb = Codebook()
    jev = _jev_mean(ctx, cb.code_version(entity_type), entity_type)
    cl = _claude_codes(ctx, cb.code_version(entity_type), entity_type)
    cuts = (0.5, 0.7, 0.8, 0.9)
    per: dict[str, list[tuple[bool, float]]] = defaultdict(list)
    for key in set(jev) & set(cl):
        _, con = key
        per[con].append((jev[key][0] == cl[key][0], jev[key][2]))
    out = []
    for con, lst in sorted(per.items()):
        n = len(lst)
        row = {"construct": con, "n": n, "agree": sum(a for a, _ in lst) / n}
        for cut in cuts:
            sub = [a for a, c in lst if c >= cut]
            row[f"cov@{cut}"] = len(sub) / n
            row[f"agree@{cut}"] = (sum(sub) / len(sub)) if sub else float("nan")
        out.append(row)
    return out
