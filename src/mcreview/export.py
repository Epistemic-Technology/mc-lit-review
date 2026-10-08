"""Stage 7: the analysis export (docs/plan.md).

Everything the post figures and the companion site show is produced here from the SQLite file and written
as JSON to one directory (default `site/src/data/`). No post bodies are exported: titles, links, dates,
metadata and codes only. Every aggregate is computed on `relevant` posts (code_final relevance in
central/substantial), and time series use only the channels without recency bias (see `UNBIASED`).
"""
from __future__ import annotations

import json
import logging
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

from .codebook import Codebook
from .config import CONFIG_DIR, PROJECT_ROOT, load_yaml
from .context import Ctx

log = logging.getLogger(__name__)

RELEVANT = ("central", "substantial")
UNBIASED = {"brave", "cited_by", "coupling"}   # substack_posts is recency-skewed (all 2026); see PLAN.md §2
GROUPS = {"academic_philosophy": "academic", "academic_science": "academic", "ai_industry": "ai_field", "rationalist_ea": "ai_field",
          "culture_general": "general", "other": "general", "business_finance": "general", "journalism_politics": "journalism",
          "religion_spirituality": "religion"}
GROUP_LABELS = {"academic": "Academic", "ai_field": "AI field", "general": "General and culture", "journalism": "Journalism and politics", "religion": "Religion and spirituality"}


def quarter(date: str | None) -> str | None:
    if not date or len(date) < 7:
        return None
    return f"{date[:4]}Q{(int(date[5:7]) + 2) // 3}"


# ---------------------------------------------------------------- loading

def _final(ctx: Ctx, entity_type: str) -> dict[int, dict[str, str]]:
    out: dict[int, dict[str, str]] = defaultdict(dict)
    for eid, con, val in ctx.conn.execute("SELECT entity_id, construct, value FROM code_final WHERE entity_type=?", (entity_type,)):
        out[int(eid)][con] = val
    return out


def relevant_ids(ctx: Ctx) -> list[int]:
    return [int(r[0]) for r in ctx.conn.execute(
        "SELECT entity_id FROM code_final WHERE entity_type='post' AND construct='relevance' AND value IN ('central','substantial') ORDER BY entity_id")]


def load_posts(ctx: Ctx, cb: Codebook) -> list[dict]:
    ids = relevant_ids(ctx)
    codes = _final(ctx, "post")
    pub_codes = _final(ctx, "publication")
    stance_items = [c.name for c in cb.by_group("stance")]
    arg_items = [c.name for c in cb.by_group("argument")]
    q = ",".join("?" * len(ids))
    channels: dict[int, set[str]] = defaultdict(set)
    for pid, src in ctx.conn.execute(f"SELECT entity_id, source FROM discovery WHERE entity_type='post' AND entity_id IN ({q})", ids):
        channels[int(pid)].add(src)
    # publication baselines over every known post in the window (corpus + archive context)
    base = {int(r[0]): (r[1], r[2], r[3]) for r in ctx.conn.execute(
        "SELECT publication_id, AVG(reaction_count), COUNT(*), AVG(restack_count) FROM posts WHERE post_date >= ? AND title IS NOT NULL GROUP BY publication_id", (ctx.cutoff,))}
    layout = {int(r[0]): r for r in ctx.conn.execute(f"SELECT post_id, x, y, cluster, cluster_prob FROM post_layout WHERE post_id IN ({q})", ids)}
    net = {int(r[0]): r for r in ctx.conn.execute(f"SELECT post_id, in_pubs, in_posts, pagerank, community FROM network_nodes WHERE post_id IN ({q})", ids)}
    labels = {int(r[0]): r[1] for r in ctx.conn.execute("SELECT cluster, label FROM topics")}
    rows = ctx.conn.execute(
        f"""SELECT p.id, p.title, p.subtitle, p.canonical_url, p.post_date, p.wordcount, p.reaction_count, p.comment_count, p.restack_count,
                   p.is_ai_generated_text, p.audience, p.type, p.publication_id, u.host, u.name pub_name, u.free_subscriber_magnitude subs, u.author_name
            FROM posts p JOIN publications u ON u.id=p.publication_id WHERE p.id IN ({q}) ORDER BY p.id""", ids).fetchall()
    out = []
    for r in rows:
        pid = int(r["id"])
        c = codes.get(pid, {})
        pc = pub_codes.get(int(r["publication_id"]), {})
        community = pc.get("community")
        b = base.get(int(r["publication_id"]))
        baseline = b[0] if b else None
        lay = layout.get(pid)
        n = net.get(pid)
        out.append({
            "id": pid, "title": r["title"], "subtitle": r["subtitle"], "url": r["canonical_url"], "date": (r["post_date"] or "")[:10],
            "quarter": quarter(r["post_date"]), "words": r["wordcount"],
            "publication_id": int(r["publication_id"]), "host": r["host"], "publication": r["pub_name"], "author": r["author_name"], "subscribers": r["subs"],
            "community": community, "group": GROUPS.get(community or "", "general"),
            "relevance": c.get("relevance"), "genre": c.get("genre"), "claim_object": c.get("claim_object"), "reports_lab_view": c.get("reports_lab_view"),
            "stance": {k: c.get(k) for k in stance_items},
            "arguments": [k for k in arg_items if c.get(k) == "true"],
            "reactions": r["reaction_count"], "comments": r["comment_count"], "restacks": r["restack_count"],
            "baseline_reactions": round(baseline, 2) if baseline is not None else None,
            "over_performance": round((r["reaction_count"] or 0) / baseline, 2) if baseline else None,
            "pub_posts_in_window": b[1] if b else None,
            "ai_flag": r["is_ai_generated_text"], "paywalled": 1 if r["audience"] == "only_paid" else 0, "post_type": r["type"],
            "channels": sorted(channels.get(pid, ())), "unbiased": bool(channels.get(pid, set()) & UNBIASED),
            "cluster": int(lay["cluster"]) if lay else None, "cluster_label": labels.get(int(lay["cluster"])) if lay else None,
            "cluster_core": bool(lay and (lay["cluster_prob"] or 0) > 0), "x": round(lay["x"], 3) if lay else None, "y": round(lay["y"], 3) if lay else None,
            "in_pubs": int(n["in_pubs"]) if n else 0, "in_posts": int(n["in_posts"]) if n else 0, "pagerank": round(n["pagerank"], 6) if n else None,
        })
    return out


# ---------------------------------------------------------------- aggregates

def _count(items, key) -> dict:
    return dict(Counter(key(i) for i in items if key(i) is not None))


def stance_tables(posts: list[dict], cb: Codebook) -> dict:
    items = [{"name": c.name, "claim": c.claim} for c in cb.by_group("stance")]
    options = list(cb.stance_options)
    def table(subset):
        return {it["name"]: {o: sum(1 for p in subset if p["stance"].get(it["name"]) == o) for o in options} for it in items}
    by_group = {g: table([p for p in posts if p["group"] == g]) for g in GROUP_LABELS}
    by_genre = {g: table([p for p in posts if p["genre"] == g]) for g in sorted({p["genre"] for p in posts if p["genre"]})}
    by_object = {g: table([p for p in posts if p["claim_object"] == g]) for g in sorted({p["claim_object"] for p in posts if p["claim_object"]})}
    unbiased = [p for p in posts if p["unbiased"] and p["quarter"]]
    by_quarter = {qq: table([p for p in unbiased if p["quarter"] == qq]) for qq in sorted({p["quarter"] for p in unbiased})}
    return {"items": items, "options": options, "n": len(posts), "overall": table(posts), "by_group": by_group, "by_genre": by_genre,
            "by_claim_object": by_object, "by_quarter_unbiased": by_quarter, "n_unbiased": len(unbiased),
            "group_labels": GROUP_LABELS}


def argument_tables(posts: list[dict], cb: Codebook) -> list[dict]:
    out = []
    n = len(posts) or 1
    for c in cb.by_group("argument"):
        with_arg = [p for p in posts if c.name in p["arguments"]]
        react = [p["reactions"] or 0 for p in with_arg]
        over = [p["over_performance"] for p in with_arg if p["over_performance"] is not None]
        cited = [p["in_pubs"] for p in with_arg]
        out.append({
            "name": c.name, "instructions": c.instructions, "n": len(with_arg), "share": round(len(with_arg) / n, 4),
            "by_group": {g: sum(1 for p in with_arg if p["group"] == g) for g in GROUP_LABELS},
            "group_share": {g: round(sum(1 for p in with_arg if p["group"] == g) / (sum(1 for p in posts if p["group"] == g) or 1), 4) for g in GROUP_LABELS},
            "median_reactions": statistics.median(react) if react else 0,
            "median_over_performance": round(statistics.median(over), 2) if over else None,
            "mean_in_pubs": round(sum(cited) / len(cited), 3) if cited else 0,
            "share_cited": round(sum(1 for x in cited if x > 0) / (len(cited) or 1), 4),
            "stance_current_conscious": _count(with_arg, lambda p: p["stance"].get("current_conscious")),
        })
    return out


def topic_tables(ctx: Ctx, posts: list[dict]) -> list[dict]:
    by_cluster: dict[int, list[dict]] = defaultdict(list)
    for p in posts:
        if p["cluster"] is not None:
            by_cluster[p["cluster"]].append(p)
    out = []
    for r in ctx.conn.execute("SELECT cluster, label, description, size, core_size, top_terms, exemplar_post_ids FROM topics WHERE cluster>=0 ORDER BY size DESC"):
        ps = by_cluster.get(int(r["cluster"]), [])
        ex = json.loads(r["exemplar_post_ids"] or "[]")[:5]
        ex_titles = [{"id": int(t[0]), "title": t[1], "url": t[2]} for t in ctx.conn.execute(f"SELECT id, title, canonical_url FROM posts WHERE id IN ({','.join('?'*len(ex))})", ex)] if ex else []
        out.append({
            "cluster": int(r["cluster"]), "label": r["label"], "description": r["description"], "size": int(r["size"]), "core_size": r["core_size"],
            "terms": json.loads(r["top_terms"] or "[]"), "exemplars": ex_titles,
            "groups": _count(ps, lambda p: p["group"]), "genres": _count(ps, lambda p: p["genre"]),
            "stance_current_conscious": _count(ps, lambda p: p["stance"].get("current_conscious")),
            "stance_moral_worth_current": _count(ps, lambda p: p["stance"].get("moral_worth_current")),
            "median_reactions": statistics.median([p["reactions"] or 0 for p in ps]) if ps else 0,
            "centroid": [round(statistics.mean(p["x"] for p in ps if p["x"] is not None), 3), round(statistics.mean(p["y"] for p in ps if p["y"] is not None), 3)] if ps else None,
        })
    return out


def network_tables(ctx: Ctx, posts: list[dict]) -> dict:
    pub_codes = _final(ctx, "publication")
    pub_rows = ctx.conn.execute(
        """SELECT n.publication_id, u.host, u.name, n.community, n.in_pubs, n.out_pubs, n.in_posts, n.pagerank, n.betweenness, n.x, n.y
           FROM pub_network n JOIN publications u ON u.id=n.publication_id""").fetchall()
    rel_pubs = Counter(p["publication_id"] for p in posts)
    # Per-publication stance counts on every item (asserts, denies, agnostic, discusses) for colouring nodes.
    stance_items = [c.name for c in Codebook().by_group("stance")]
    pub_stance: dict[int, dict[str, list[int]]] = defaultdict(lambda: {it: [0, 0, 0, 0] for it in stance_items})
    for p in posts:
        for it in stance_items:
            v = p["stance"].get(it)
            if v in ("asserts", "denies", "agnostic", "discusses"):
                pub_stance[p["publication_id"]][it][("asserts", "denies", "agnostic", "discusses").index(v)] += 1
    nodes = [{"id": int(r["publication_id"]), "host": r["host"], "name": r["name"], "community": r["community"],
              "stance": pub_stance.get(int(r["publication_id"])),
              "group": GROUPS.get((pub_codes.get(int(r["publication_id"])) or {}).get("community", ""), None),
              "relevant_posts": rel_pubs.get(int(r["publication_id"]), 0),
              "in_pubs": r["in_pubs"], "out_pubs": r["out_pubs"], "in_posts": r["in_posts"], "pagerank": round(r["pagerank"], 6), "betweenness": round(r["betweenness"], 2),
              "x": round(r["x"], 3) if r["x"] is not None else None, "y": round(r["y"], 3) if r["y"] is not None else None} for r in pub_rows]
    edges = [{"source": int(r[0]), "target": int(r[1]), "weight": int(r[2]), "backbone": int(r[3])} for r in ctx.conn.execute("SELECT * FROM pub_edges")]
    post_ids = {p["id"] for p in posts}
    post_edges = [{"source": int(r[0]), "target": int(r[1])} for r in ctx.conn.execute("SELECT src_post_id, dst_post_id FROM network_edges") if int(r[0]) in post_ids and int(r[1]) in post_ids]
    # cross-camp citation: stance of citing vs cited post on current consciousness
    st = {p["id"]: p["stance"].get("current_conscious") for p in posts}
    camp = Counter((st.get(e["source"]), st.get(e["target"])) for e in post_edges)
    return {"pub_nodes": nodes, "pub_edges": edges, "post_edges": post_edges,
            "cross_camp": [{"citing": k[0], "cited": k[1], "n": v} for k, v in camp.items()]}


def _tier_lookup(tiers_cfg: dict):
    domain_tier = {d.lower(): t for t, ds in (tiers_cfg.get("tiers") or {}).items() for d in ds}
    ignore = {d.lower() for d in (tiers_cfg.get("ignore") or [])}
    suffix_rules = tiers_cfg.get("suffix_rules") or []

    def tier_for(kind: str, domain: str | None) -> str | None:
        if kind in ("arxiv", "doi"):
            return "academic"
        if kind == "book":
            return "book"
        if kind == "wikipedia":
            return "encyclopedia"
        d = (domain or "").lower()
        parts = d.split(".") if d else []
        cands = [".".join(parts[i:]) for i in range(max(0, len(parts) - 1))]
        reg = cands[-1] if cands else d
        # image hosts, shorteners, platform chrome: never a cited work. "substack.com" in the ignore list means
        # the platform's own pages, not publications' homepages (x.substack.com), which are substack-tier works.
        if d in ignore or (reg in ignore and reg != "substack.com"):
            return None
        if kind in ("substack_post", "maybe_substack_post"):
            return "substack"
        if kind == "homepage":
            if not d or d.endswith(".substack.com"):
                return "substack"
            return domain_tier.get(next((c for c in cands if c in domain_tier), ""), "web")
        if not d:
            return None
        for cand in cands:
            if cand in domain_tier:
                return domain_tier[cand]
        for rule in suffix_rules:
            if d.endswith(rule["suffix"]):
                return rule["tier"]
        return "web"
    return tier_for


def source_tables(ctx: Ctx, posts: list[dict]) -> dict:
    tiers_cfg = load_yaml("domain_tiers.yaml")
    tier_for = _tier_lookup(tiers_cfg)
    ids = [p["id"] for p in posts]
    group_of = {p["id"]: p["group"] for p in posts}
    q = ",".join("?" * len(ids))
    works: dict[int, dict] = {}
    tier_posts: dict[str, set[int]] = defaultdict(set)
    tier_group: dict[str, Counter] = defaultdict(Counter)
    for r in ctx.conn.execute(
        f"""SELECT pr.post_id, r.id, r.kind, r.domain, r.title, r.url_norm, r.identifier, r.target_post_id FROM post_refs pr JOIN refs r ON r.id=pr.ref_id WHERE pr.post_id IN ({q})""", ids):
        t = tier_for(r["kind"], r["domain"])
        if t is None:
            continue
        w = works.setdefault(int(r["id"]), {"id": int(r["id"]), "kind": r["kind"], "tier": t, "domain": r["domain"], "title": r["title"], "url": r["url_norm"], "identifier": r["identifier"], "citing_posts": set(), "citing_pubs": set()})
        w["citing_posts"].add(int(r["post_id"]))
        tier_posts[t].add(int(r["post_id"]))
        tier_group[t][group_of[int(r["post_id"])]] += 1
    pub_of = {p["id"]: p["publication_id"] for p in posts}
    for w in works.values():
        w["citing_pubs"] = {pub_of[p] for p in w["citing_posts"]}
    top = sorted(works.values(), key=lambda w: (len(w["citing_pubs"]), len(w["citing_posts"])), reverse=True)
    def ser(w):
        return {k: (len(v) if isinstance(v, set) else v) for k, v in w.items()}
    by_tier = {t: [ser(w) for w in top if w["tier"] == t][:25] for t in sorted(tier_posts)}
    # named people
    names = load_yaml("names.yaml")["people"]
    compiled = [(n["name"], n["group"], [re.compile(p) for p in n["patterns"]]) for n in names]
    mention_posts: dict[str, set[int]] = defaultdict(set)
    mention_group: dict[str, Counter] = defaultdict(Counter)
    for pid, body in ctx.conn.execute(f"SELECT id, body_text FROM posts WHERE id IN ({q})", ids):
        text = body or ""
        for name, _g, pats in compiled:
            if any(p.search(text) for p in pats):
                mention_posts[name].add(int(pid))
                mention_group[name][group_of[int(pid)]] += 1
    people = sorted([{"name": n, "group": g, "posts": len(mention_posts[n]), "share": round(len(mention_posts[n]) / (len(posts) or 1), 4), "by_group": dict(mention_group[n])}
                     for n, g, _ in compiled], key=lambda d: d["posts"], reverse=True)
    return {"tiers": {t: {"posts_citing": len(ps), "works": sum(1 for w in works.values() if w["tier"] == t), "by_group": dict(tier_group[t])} for t, ps in tier_posts.items()},
            "top_works_by_tier": by_tier, "top_works": [ser(w) for w in top[:60]], "people": people, "n_posts": len(posts)}


def publication_tables(ctx: Ctx, posts: list[dict]) -> list[dict]:
    pub_codes = _final(ctx, "publication")
    by_pub: dict[int, list[dict]] = defaultdict(list)
    for p in posts:
        by_pub[p["publication_id"]].append(p)
    net = {int(r[0]): r for r in ctx.conn.execute("SELECT publication_id, in_pubs, out_pubs, pagerank, betweenness, community FROM pub_network")}
    out = []
    for pid, ps in by_pub.items():
        u = ctx.conn.execute("SELECT host, name, author_name, free_subscriber_magnitude, hero_text, harvest_posts_in_window FROM publications WHERE id=?", (pid,)).fetchone()
        n = net.get(pid)
        community = (pub_codes.get(pid) or {}).get("community")
        out.append({
            "id": pid, "host": u["host"], "name": u["name"], "author": u["author_name"], "subscribers": u["free_subscriber_magnitude"], "tagline": u["hero_text"],
            "community": community, "group": GROUPS.get(community or "", "general"),
            "relevant_posts": len(ps), "posts_in_window": u["harvest_posts_in_window"],
            "relevant_share": round(len(ps) / u["harvest_posts_in_window"], 4) if u["harvest_posts_in_window"] else None,
            "median_reactions": statistics.median([p["reactions"] or 0 for p in ps]), "baseline_reactions": ps[0]["baseline_reactions"],
            "in_pubs": int(n["in_pubs"]) if n else 0, "out_pubs": int(n["out_pubs"]) if n else 0, "pagerank": round(n["pagerank"], 6) if n else None,
            "betweenness": round(n["betweenness"], 2) if n else None, "network_community": int(n["community"]) if n else None,
            "stance_current_conscious": _count(ps, lambda p: p["stance"].get("current_conscious")),
            "top_cluster": Counter(p["cluster_label"] for p in ps if p["cluster_label"]).most_common(1)[0][0] if any(p["cluster_label"] for p in ps) else None,
            "post_ids": [p["id"] for p in ps],
        })
    return sorted(out, key=lambda d: d["relevant_posts"], reverse=True)


def summary(ctx: Ctx, posts: list[dict], cb: Codebook) -> dict:
    c = ctx.conn
    q = lambda sql, *a: c.execute(sql, a).fetchone()[0]  # noqa: E731
    subset_run = c.execute("SELECT counts_json, finished_at FROM runs WHERE stage='subset' AND status='ok' ORDER BY id DESC LIMIT 1").fetchone()
    gate = q("SELECT COUNT(DISTINCT entity_id) FROM codes c JOIN code_runs r ON r.id=c.code_run_id WHERE r.engine='claude' AND c.entity_type='post' AND c.construct='relevance'")
    claude_rel = dict(c.execute("SELECT value, COUNT(*) FROM code_final WHERE entity_type='post' AND construct='relevance' GROUP BY 1").fetchall())
    engines = [dict(r) for r in c.execute("SELECT engine, model, target, codebook_version, n_items, ROUND(cost_usd,2) cost_usd, started_at, finished_at FROM code_runs WHERE n_items>0 ORDER BY id")]
    return {
        "generated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "codebook_version": cb.version, "publication_version": cb.publication_version,
        "prisma": {**(json.loads(subset_run["counts_json"]) if subset_run else {}), "jev_coded": q("SELECT COUNT(*) FROM analysis_subset"), "claude_coded": gate,
                   "relevance": claude_rel, "relevant": len(posts)},
        "posts_relevant": len(posts), "publications_relevant": len({p["publication_id"] for p in posts}),
        "date_range": [min(p["date"] for p in posts if p["date"]), max(p["date"] for p in posts if p["date"])],
        "by_quarter_all": _count(posts, lambda p: p["quarter"]), "by_quarter_unbiased": _count([p for p in posts if p["unbiased"]], lambda p: p["quarter"]),
        "by_channel": dict(Counter(ch for p in posts for ch in p["channels"])), "unbiased_posts": sum(1 for p in posts if p["unbiased"]),
        "by_group": _count(posts, lambda p: p["group"]), "by_genre": _count(posts, lambda p: p["genre"]), "by_claim_object": _count(posts, lambda p: p["claim_object"]),
        "ai_flag": _count(posts, lambda p: p["ai_flag"]), "paywalled": sum(p["paywalled"] for p in posts),
        "engines": engines,
    }


def methods(ctx: Ctx) -> dict:
    from .code import agreement
    from .gold import human_agreement

    return {"jev_vs_claude_posts": agreement(ctx, "post"), "jev_vs_claude_publications": agreement(ctx, "publication"), "engine_vs_human": human_agreement(ctx),
            "gold_samples": [dict(r) for r in ctx.conn.execute("SELECT sample_name, entity_type, COUNT(*) n, MIN(sampled_at) sampled_at FROM gold_samples GROUP BY 1,2")],
            "human_decisions": [dict(r) for r in ctx.conn.execute("SELECT s.sample_name, g.decision, COUNT(*) n FROM gold_codes g JOIN gold_samples s ON s.id=g.sample_id GROUP BY 1,2")]}


# ---------------------------------------------------------------- entry point

def export(ctx: Ctx, out_dir: Path | None = None) -> Path:
    out = Path(out_dir) if out_dir else PROJECT_ROOT / "site" / "src" / "data"
    out.mkdir(parents=True, exist_ok=True)
    cb = Codebook()
    posts = load_posts(ctx, cb)
    files = {
        "posts.json": posts,
        "summary.json": summary(ctx, posts, cb),
        "stance.json": stance_tables(posts, cb),
        "arguments.json": argument_tables(posts, cb),
        "topics.json": topic_tables(ctx, posts),
        "network.json": network_tables(ctx, posts),
        "sources.json": source_tables(ctx, posts),
        "publications.json": publication_tables(ctx, posts),
        "methods.json": methods(ctx),
        "codebook.json": {"version": cb.version, "domain": cb.domain, "stance_options": cb.stance_options,
                          "constructs": [{"name": c.name, "group": c.group, "primitive": c.primitive, "instructions": c.instructions, "claim": c.claim, "options": list(c.options)} for c in cb.constructs],
                          "publication_constructs": [{"name": c.name, "options": list(c.options)} for c in cb.publication_constructs]},
    }
    for name, data in files.items():
        (out / name).write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str))
        ctx.counts[name] = len(data) if isinstance(data, list) else 1
    # Per-publication slices so a publication page loads a few kilobytes, not the whole corpus.
    pub_dir = out / "pub"
    pub_dir.mkdir(exist_ok=True)
    for old in pub_dir.glob("*.json"):
        old.unlink()
    net = files["network.json"]
    names = {n["id"]: (n["name"] or n["host"]) for n in net["pub_nodes"]}
    edges_in: dict[int, list] = defaultdict(list)
    edges_out: dict[int, list] = defaultdict(list)
    for e in net["pub_edges"]:
        edges_in[e["target"]].append({"id": e["source"], "name": names.get(e["source"]), "weight": e["weight"]})
        edges_out[e["source"]].append({"id": e["target"], "name": names.get(e["target"]), "weight": e["weight"]})
    node_by_id = {n["id"]: n for n in net["pub_nodes"]}
    posts_by_pub: dict[int, list] = defaultdict(list)
    for p in posts:
        posts_by_pub[p["publication_id"]].append(p)
    for pub in files["publications.json"]:
        slice_ = {"publication": pub, "node": node_by_id.get(pub["id"]), "posts": posts_by_pub.get(pub["id"], []),
                  "cited_by": sorted(edges_in.get(pub["id"], []), key=lambda e: -e["weight"]), "cites": sorted(edges_out.get(pub["id"], []), key=lambda e: -e["weight"])}
        (pub_dir / f"{pub['id']}.json").write_text(json.dumps(slice_, ensure_ascii=False, separators=(",", ":"), default=str))
    ctx.counts["pub_slices"] = len(files["publications.json"])
    log.info("exported %d files and %d publication slices to %s", len(files), len(files["publications.json"]), out)
    return out
