"""Command-line entry point. Each subcommand is one idempotent pipeline stage and records a run."""
from __future__ import annotations

import json
import logging

import typer

from . import bodies as bodies_mod
from . import citations
from . import discover as disc
from . import harvest as harvest_mod
from .context import Ctx

app = typer.Typer(help="Substack machine-cognition/consciousness corpus builder (lexical search + citation expansion)", no_args_is_help=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("urllib3").setLevel(logging.WARNING)
log = logging.getLogger("mcreview")


def _run(stage: str, fn, **kwargs):
    ctx = Ctx(stage, kwargs)
    log.info("run %d: %s %s", ctx.run_id, stage, kwargs)
    try:
        result = fn(ctx, **kwargs)
    except KeyboardInterrupt:
        ctx.finish("interrupted")
        raise typer.Exit(130)
    except Exception:
        ctx.finish("error")
        raise
    log.info("run %d done: %s", ctx.run_id, ctx.counts)
    ctx.finish()
    return result


@app.command()
def init() -> None:
    """Create the database and raw store; show credential status."""
    ctx = Ctx("init")
    typer.echo(f"db: {ctx.settings.path('db')}\nraw: {ctx.settings.path('raw')}\nconfig hash: {ctx.settings.config_hash()}")
    creds = ctx.creds
    typer.echo("; ".join(f"{k}: {'set' if creds.get(k) else 'missing'}" for k in creds))
    ctx.finish()


def _discover(brave: bool = True, substack_posts: bool = True, substack_pubs: bool = True, max_queries: int | None = None, refresh: bool = False) -> None:
    def fn(ctx: Ctx, **_):
        if brave:
            disc.brave(ctx, max_queries, refresh)
        if substack_posts:
            disc.substack_posts(ctx, max_queries, refresh)
        if substack_pubs:
            disc.substack_pubs(ctx, max_queries, refresh)

    _run("discover", fn, brave=brave, substack_posts=substack_posts, substack_pubs=substack_pubs, max_queries=max_queries, refresh=refresh)


def _resolve(limit: int | None = None) -> None:
    _run("resolve", lambda ctx, limit=None: disc.resolve(ctx, limit), limit=limit)


def _fetch_bodies(limit: int | None = None) -> None:
    _run("fetch_bodies", lambda ctx, limit=None: bodies_mod.fetch_bodies(ctx, limit), limit=limit)


def _cite_round(round_no: int | None = None) -> int:
    def fn(ctx: Ctx, **_):
        r = round_no if round_no is not None else citations.next_round_number(ctx)
        ctx.conn.execute("UPDATE runs SET args_json=? WHERE id=?", (json.dumps({"round": r}), ctx.run_id))
        max_rounds = int(ctx.settings["citation"]["max_rounds"])
        if round_no is None and r > max_rounds:
            # max_rounds is a property of the corpus, not of one run-all invocation: a resumed run-all
            # must not start round max_rounds+1 just because its own loop has iterations left.
            log.info("round %d exceeds citation.max_rounds=%d; not started", r, max_rounds)
            ctx.conn.execute("UPDATE runs SET status='skipped' WHERE id=?", (ctx.run_id,))
            return 0
        added = citations.run_round(ctx, r)
        log.info("round %d added %d posts", r, added)
        return added

    return _run("cite_round", fn)


@app.command()
def discover(
    brave: bool = typer.Option(True, help="Brave web search"),
    substack_posts: bool = typer.Option(True, help="Substack post search (anonymous)"),
    substack_pubs: bool = typer.Option(True, help="Substack publication search (needs cookie; context only)"),
    max_queries: int | None = typer.Option(None, help="Cap on query terms per channel (for smoke tests)"),
    refresh: bool = typer.Option(False, help="Re-run queries that already have results"),
) -> None:
    """Phase 1: lexical search. Posts found here enter the corpus at round 0. Queries already run are skipped unless --refresh."""
    _discover(brave, substack_posts, substack_pubs, max_queries, refresh)


@app.command()
def resolve(limit: int | None = None) -> None:
    """Confirm unresolved hosts (from web search results) are Substack publications; canonicalise; fill metadata."""
    _resolve(limit)


@app.command("fetch-bodies")
def fetch_bodies(limit: int | None = None) -> None:
    """Fetch free post bodies for corpus posts; refresh metadata; extract text."""
    _fetch_bodies(limit)


@app.command("cite-round")
def cite_round(round_no: int | None = typer.Option(None, "--round", help="Round number (default: next)")) -> None:
    """Phase 2, one round: extract references, backward chase cited posts, coupling search on shared references."""
    _cite_round(round_no)


@app.command("archive-meta")
def archive_meta(min_posts: int | None = None, limit: int | None = None,
                 relevant_only: bool = typer.Option(False, help="Publications with a relevant post in code_final, regardless of min_posts")) -> None:
    """Optional context: archive metadata (no bodies) for publications with >= min_posts corpus posts."""
    _run("archive_meta", lambda ctx, **_: harvest_mod.archive_meta(ctx, min_posts, limit, relevant_only), min_posts=min_posts, limit=limit, relevant_only=relevant_only)


@app.command("enrich-pubs")
def enrich_pubs(limit: int | None = None, profiles: bool = typer.Option(True, help="Also fetch author public profiles for bios")) -> None:
    """Fill name, tagline, author and bio for publications with relevant posts (homepage preloads + public profiles)."""
    from . import enrich as enrich_mod

    _run("enrich_pubs", lambda ctx, **_: enrich_mod.enrich_publications(ctx, limit, profiles), limit=limit, profiles=profiles)


@app.command()
def retext() -> None:
    """Recompute body_text from stored raw bodies (after changing the HTML-to-text rules)."""
    _run("retext", lambda ctx: bodies_mod.rederive_text(ctx))


@app.command("run-all")
def run_all(max_queries: int | None = typer.Option(None, help="Cap on query terms per channel (for smoke tests)")) -> None:
    """discover -> resolve -> fetch-bodies -> (cite-round -> resolve -> fetch-bodies) x max_rounds, stopping when a round adds nothing.
    Safe to re-run after an interruption: completed queries, bodies and references are skipped."""
    from .config import Settings

    max_rounds = int(Settings()["citation"]["max_rounds"])
    _discover(max_queries=max_queries)
    _resolve()
    _fetch_bodies()
    for _ in range(max_rounds):
        added = _cite_round()
        if not added:
            log.info("no new posts; stopping citation rounds")
            break
        _resolve()
        _fetch_bodies()
    # one final reference extraction so the refs table covers the last round's bodies
    _run("cite_refs_final", lambda ctx: (citations.extract_references(ctx), citations.link_substack_targets(ctx), citations.update_eligibility(ctx)))


@app.command("check-validation")
def check_validation() -> None:
    """Did the pipeline find the publications in config/validation.yaml on its own? (They play no role in discovery.)"""
    ctx = Ctx("check_validation")
    c = ctx.conn
    found = 0
    for v in ctx.settings.validation.get("publications") or []:
        host = v["host"].lower()
        sub = host[: -len(".substack.com")] if host.endswith(".substack.com") else None
        row = c.execute(
            "SELECT id, host FROM publications WHERE host=? OR alias_hosts LIKE ? OR (? IS NOT NULL AND subdomain=?)",
            (host, f'%"{host}"%', sub, sub),
        ).fetchone()
        if row is None:
            typer.echo(f"MISSING  {host:<40} {v.get('note','')}")
            continue
        n = c.execute("SELECT COUNT(*) FROM posts WHERE publication_id=? AND entry_round IS NOT NULL", (row["id"],)).fetchone()[0]
        srcs = [f"{s}:{k}" for s, k in c.execute(
            "SELECT source, COUNT(*) FROM discovery WHERE entity_type='post' AND entity_id IN (SELECT id FROM posts WHERE publication_id=?) GROUP BY source", (row["id"],))]
        status = "found" if n else "pub-only"
        found += bool(n)
        typer.echo(f"{status:<8} {host:<40} corpus posts={n:<4} via {', '.join(srcs) or 'publication search only'}")
    typer.echo(f"{found} of {len(ctx.settings.validation.get('publications') or [])} validation publications have corpus posts")
    ctx.finish()


@app.command()
def report() -> None:
    """Unique-yield report: what each channel and each query term contributed that nothing else did."""
    ctx = Ctx("report")
    c = ctx.conn
    typer.echo("posts by entry round:")
    for r, n in c.execute("SELECT entry_round, COUNT(*) FROM posts WHERE entry_round IS NOT NULL GROUP BY 1 ORDER BY 1"):
        typer.echo(f"  round {r}: {n}")
    typer.echo("\nchannel yield (corpus posts): total / unique to channel")
    for src, tot, uniq in c.execute("""
        WITH per AS (SELECT entity_id post_id, source FROM discovery WHERE entity_type='post' GROUP BY entity_id, source),
             nsrc AS (SELECT post_id, COUNT(*) k FROM per GROUP BY post_id)
        SELECT per.source, COUNT(*), SUM(CASE WHEN nsrc.k=1 THEN 1 ELSE 0 END) FROM per JOIN nsrc USING(post_id) GROUP BY per.source ORDER BY 2 DESC"""):
        typer.echo(f"  {src:<16} {tot:>7} {uniq:>7}")
    typer.echo("\nquery-term yield (phase 1, corpus posts): total / unique to term, top 40 and bottom 15")
    rows = c.execute("""
        WITH per AS (SELECT d.entity_id post_id, q.term FROM discovery d JOIN queries q ON q.id=d.query_id
                     WHERE d.entity_type='post' AND q.facet<>'citation' GROUP BY d.entity_id, q.term),
             nterm AS (SELECT post_id, COUNT(*) k FROM per GROUP BY post_id)
        SELECT per.term, COUNT(*) tot, SUM(CASE WHEN nterm.k=1 THEN 1 ELSE 0 END) uniq FROM per JOIN nterm USING(post_id) GROUP BY per.term ORDER BY tot DESC""").fetchall()
    shown = rows if len(rows) <= 55 else rows[:40] + [("...", "", "")] + rows[-15:]
    for row in shown:
        typer.echo(f"  {str(row[0])[:50]:<50} {row[1]:>6} {row[2]:>6}")
    typer.echo("\ntop coupling references (citing posts / citing publications):")
    for row in c.execute("SELECT citing_posts, citing_pubs, kind, COALESCE(title, url_norm), searched_round FROM refs WHERE eligible=1 ORDER BY citing_pubs DESC, citing_posts DESC LIMIT 25"):
        typer.echo(f"  {row[0]:>4} {row[1]:>4} {row[2]:<14} {str(row[3])[:80]:<80} {'searched r'+str(row[4]) if row[4] else ''}")
    typer.echo("\nineligible reference reasons:")
    for row in c.execute("SELECT block_reason, COUNT(*) FROM refs WHERE eligible=0 GROUP BY 1 ORDER BY 2 DESC LIMIT 12"):
        typer.echo(f"  {str(row[0]):<40} {row[1]:>6}")
    ctx.finish()


# ---------------------------------------------------------------- analysis stages (docs/plan.md)


@app.command()
def subset() -> None:
    """Stage 0: rebuild the analysis population from config/analysis.yaml rules; record counts per rule."""
    from . import subset as subset_mod

    _run("subset", lambda ctx: subset_mod.build(ctx))


@app.command("codebook")
def codebook_cmd(render: bool = typer.Option(True, help="Write docs/codebook.md from config/codebook.yaml")) -> None:
    """Show the codebook version and constructs; render the Markdown document."""
    from .codebook import Codebook
    from .config import PROJECT_ROOT

    cb = Codebook()
    typer.echo(f"codebook v{cb.version}: {len(cb.constructs)} post constructs "
               f"({', '.join(f'{g}={len(cb.by_group(g))}' for g in ('relevance','structure','stance','argument'))}), "
               f"{len(cb.publication_constructs)} publication constructs")
    if render:
        out = PROJECT_ROOT / "docs" / "codebook.md"
        out.write_text(cb.render_markdown())
        typer.echo(f"wrote {out}")


@app.command()
def code(
    engine: str = typer.Argument(..., help="jev | claude"),
    target: str = typer.Option("posts", help="posts | publications"),
    limit: int | None = typer.Option(None, help="Cap on items (smoke tests)"),
    repeats: int | None = typer.Option(None, help="Jev: identical requests with permuted option order (default from config)"),
    only_relevant: bool = typer.Option(False, help="Posts: only those Jev rates central/substantial above coding.claude.relevance_min_prob"),
    final_relevant: bool = typer.Option(False, help="Posts: only those whose code_final relevance is central/substantial (re-coding stance on the relevant set)"),
    post_id: list[int] = typer.Option(None, help="Specific post ids"),
    batch: bool = typer.Option(False, help="Claude: submit as a Message Batch (half price; collect with code-collect)"),
    construct: list[str] = typer.Option(None, help="Restrict to these constructs"),
    dry_run: bool = typer.Option(False, help="Count items and estimate cost; no API calls"),
) -> None:
    """Stage 3/4: code posts or publications with an engine. Idempotent per (engine, model, codebook version, repeat)."""
    from . import code as code_mod

    if target == "posts":
        _run("code", lambda ctx, **_: code_mod.code_posts(ctx, engine, limit, repeats, dry_run, only_relevant, post_id or None, batch, construct or None, final_relevant),
             engine=engine, target=target, limit=limit, repeats=repeats, only_relevant=only_relevant, final_relevant=final_relevant, batch=batch, dry_run=dry_run, constructs=construct or None)
    elif target == "publications":
        _run("code", lambda ctx, **_: code_mod.code_publications(ctx, engine, limit, dry_run), engine=engine, target=target, limit=limit, dry_run=dry_run)
    else:
        raise typer.BadParameter("target must be posts or publications")


@app.command("code-collect")
def code_collect(code_run_id: int = typer.Argument(..., help="code_runs.id of a submitted batch")) -> None:
    """Fetch and store the results of a Claude Message Batch submitted with `code claude --batch`."""
    from . import code as code_mod

    _run("code_collect", lambda ctx, **_: code_mod.collect(ctx, code_run_id), code_run_id=code_run_id)


@app.command("code-final")
def code_final() -> None:
    """Materialise code_final: human > Claude > Jev (above construct threshold) > Jev low-confidence."""
    from . import code as code_mod

    _run("code_final", lambda ctx: code_mod.materialise(ctx))


@app.command()
def agreement(entity_type: str = typer.Option("post")) -> None:
    """Jev vs Claude agreement per construct, with agreement/coverage above confidence cut-offs; plus engine vs human where gold codes exist."""
    from . import code as code_mod
    from . import gold as gold_mod

    ctx = Ctx("agreement")
    rows = code_mod.agreement(ctx, entity_type)
    if rows:
        keys = [k for k in rows[0] if k not in ("construct",)]
        typer.echo("jev vs claude:  " + " ".join(f"{k:>10}" for k in keys))
        for r in rows:
            typer.echo(f"{r['construct']:<28}" + " ".join(f"{r[k]:>10.3f}" if isinstance(r[k], float) else f"{r[k]:>10}" for k in keys))
    else:
        typer.echo("no items coded by both engines yet")
    h = gold_mod.human_agreement(ctx)
    if h:
        typer.echo("\nengine vs human:")
        for r in h:
            typer.echo(f"  {r['construct']:<28} {r['source']:<8} n={r['n']:<4} agree={r['agree']:.3f}")
    ctx.finish()


@app.command("gold-sample")
def gold_sample(name: str = typer.Argument(..., help="relevance | stance | publications")) -> None:
    """Stage 2: draw (once) and freeze a stratified random sample for human verification."""
    from . import gold as gold_mod

    _run("gold_sample", lambda ctx, **_: gold_mod.sample(ctx, name), name=name)


@app.command("gold-export")
def gold_export(name: str = typer.Argument(...), out: str = typer.Option(None, help="Output JSON (default analysis/coder/data/<name>.json)")) -> None:
    """Export a sample with engine codes and evidence for the coder tool."""
    from pathlib import Path

    from . import gold as gold_mod
    from .config import PROJECT_ROOT

    ctx = Ctx("gold_export", {"name": name})
    gold_mod.export(ctx, name, Path(out) if out else PROJECT_ROOT / "analysis" / "coder" / "data" / f"{name}.json")
    ctx.finish()


@app.command("gold-import")
def gold_import(path: str = typer.Argument(..., help="Coder tool output JSON")) -> None:
    """Import human decisions into gold_codes."""
    from pathlib import Path

    from . import gold as gold_mod

    _run("gold_import", lambda ctx, **_: gold_mod.import_codes(ctx, Path(path)), path=path)


@app.command()
def embed(limit: int | None = typer.Option(None, help="Cap on posts (smoke tests)")) -> None:
    """Stage 5a: embed the relevant posts with the configured open model (local CPU); idempotent per model."""
    from . import embeddings as emb

    _run("embed", lambda ctx, **_: emb.embed(ctx, limit), limit=limit)


@app.command()
def topics() -> None:
    """Stage 5a: UMAP + HDBSCAN over the embeddings; writes topics and post_layout."""
    from . import embeddings as emb

    _run("topics", lambda ctx: emb.topics(ctx))


@app.command("topics-label")
def topics_label(all_: bool = typer.Option(False, "--all", help="Re-label clusters that already have a label")) -> None:
    """Stage 5a: suggest a label and description per cluster with Claude (via Claude Code); hand-check afterwards."""
    from . import embeddings as emb

    _run("topics_label", lambda ctx, **_: emb.label_topics(ctx, only_missing=not all_), all=all_)


@app.command("topics-export")
def topics_export(path: str = typer.Option("analysis/topic_labels.csv")) -> None:
    """Write the clusters with suggested labels, terms and central titles to an editable CSV."""
    from . import embeddings as emb

    ctx = Ctx("topics_export", {"path": path})
    emb.export_topic_labels(ctx, path)
    ctx.finish()


@app.command("topics-import")
def topics_import(path: str = typer.Option("analysis/topic_labels.csv")) -> None:
    """Read edited labels and descriptions back into the topics table."""
    from . import embeddings as emb

    _run("topics_import", lambda ctx, **_: emb.import_topic_labels(ctx, path), path=path)


@app.command()
def export(out: str | None = typer.Option(None, help="Output directory (default site/src/data)")) -> None:
    """Stage 7: write every aggregate and the post/publication tables the figures and site read (no bodies)."""
    from pathlib import Path

    from . import export as export_mod

    _run("export", lambda ctx, **_: export_mod.export(ctx, Path(out) if out else None), out=out)


@app.command()
def network() -> None:
    """Stage 5b: citation network over corpus posts (metrics, Leiden communities, layout) and the publication-level backbone."""
    from . import network as net

    _run("network", lambda ctx: net.build(ctx))


@app.command()
def status() -> None:
    """Counts by stage."""
    ctx = Ctx("status")
    c = ctx.conn
    q = lambda sql, *a: c.execute(sql, a).fetchone()[0]  # noqa: E731
    typer.echo(f"publications: {q('SELECT COUNT(*) FROM publications')} "
               f"(with corpus posts {q('SELECT COUNT(DISTINCT publication_id) FROM posts WHERE entry_round IS NOT NULL')}, "
               f"unresolved-with-posts {q('SELECT COUNT(*) FROM publications WHERE is_substack IS NULL AND id IN (SELECT publication_id FROM posts WHERE entry_round IS NOT NULL)')}, "
               f"not-substack {q('SELECT COUNT(*) FROM publications WHERE is_substack=0')})")
    typer.echo(f"corpus posts: {q('SELECT COUNT(*) FROM posts WHERE entry_round IS NOT NULL')} "
               f"(bodies ok {q("SELECT COUNT(*) FROM posts WHERE body_status='ok'")}, "
               f"paywalled {q("SELECT COUNT(*) FROM posts WHERE body_status='paywalled'")}, "
               f"pre-cutoff {q("SELECT COUNT(*) FROM posts WHERE body_status='pre_cutoff'")}, "
               f"pending {q('SELECT COUNT(*) FROM posts p JOIN publications pub ON pub.id=p.publication_id WHERE p.body_status IS NULL AND pub.is_substack=1 AND p.entry_round IS NOT NULL AND (p.post_date IS NULL OR p.post_date >= ?)', ctx.cutoff)})")
    typer.echo(f"context-only posts (archive-meta): {q('SELECT COUNT(*) FROM posts WHERE entry_round IS NULL')}")
    typer.echo(f"references: {q('SELECT COUNT(*) FROM refs')} "
               f"(cited by >=2 posts {q('SELECT COUNT(*) FROM refs WHERE citing_posts>=2')}, by >=2 publications {q('SELECT COUNT(*) FROM refs WHERE citing_pubs>=2')}, eligible targets {q('SELECT COUNT(*) FROM refs WHERE eligible=1')}, "
               f"searched {q('SELECT COUNT(*) FROM refs WHERE searched_round IS NOT NULL')}, backward-chased {q('SELECT COUNT(*) FROM refs WHERE backward_round IS NOT NULL')})")
    typer.echo("discovery by source:")
    for row in c.execute("SELECT source, entity_type, COUNT(*) n, COUNT(DISTINCT entity_id) d FROM discovery GROUP BY 1,2 ORDER BY n DESC"):
        typer.echo(f"  {row['source']:>18} {row['entity_type']:>12} {row['n']:>7} rows {row['d']:>7} distinct")
    typer.echo(f"citation sources: eligible {q('SELECT COUNT(*) FROM posts WHERE source_eligible=1')}, gated out {q('SELECT COUNT(*) FROM posts WHERE source_eligible=0')}")
    typer.echo(f"authors: {q('SELECT COUNT(*) FROM authors')}, fetches: {q('SELECT COUNT(*) FROM fetch_log')}, "
               f"brave calls made: {q("SELECT COUNT(*) FROM fetch_log WHERE url LIKE 'https://api.search.brave.com/%'")}, cached: {q('SELECT COUNT(*) FROM http_cache')}")
    ctx.finish()


if __name__ == "__main__":
    app()
