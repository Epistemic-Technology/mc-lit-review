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
from urllib.parse import quote, urlsplit

from .axes import AXES, LEVELS, axes_for
from .codebook import Codebook
from .config import CONFIG_DIR, PROJECT_ROOT, load_yaml
from .context import Ctx
from . import refs as refs_mod

log = logging.getLogger(__name__)

RELEVANT = ("central", "substantial")
UNBIASED = {"brave", "cited_by", "coupling"}   # substack_posts is recency-skewed (all 2026); see PLAN.md §2
GROUPS = {"academic_philosophy": "academic", "academic_science": "academic", "ai_industry": "ai_field", "rationalist_ea": "ai_field",
          "culture_general": "general", "other": "general", "business_finance": "general", "journalism_politics": "journalism",
          "religion_spirituality": "religion"}
# Features of AI systems pointed to (codebook 0.4.0, group `feature`): display labels and the families the
# site and figures group them into. Direction options: for / against / both_or_neutral; not_cited is the abstain.
FEATURE_LABELS = {
    "feat_prediction_objective": "Next-token prediction objective", "feat_architecture": "Architecture (transformer, no recurrence)",
    "feat_training_data": "Trained on human text", "feat_post_training": "Post-training shapes what it says",
    "feat_memory_continuity": "Memory and continuity", "feat_embodiment": "Body, senses, world contact",
    "feat_instances": "Many instances, copyable", "feat_self_report": "What it says about itself",
    "feat_internals": "Interpretability findings", "feat_eval_behaviour": "Behaviour under evaluation",
    "feat_agentic_action": "Agentic action in the world", "feat_capability_success": "What it succeeds at",
    "feat_capability_failure": "What it fails at", "feat_scale": "Scale and brain comparison",
}
FEATURE_FAMILIES = {
    "built": {"label": "How it is built", "features": ["feat_prediction_objective", "feat_architecture", "feat_training_data", "feat_post_training", "feat_scale"]},
    "lacks": {"label": "What it lacks", "features": ["feat_memory_continuity", "feat_embodiment", "feat_instances"]},
    "inside": {"label": "What it says and what is inside", "features": ["feat_self_report", "feat_internals"]},
    "does": {"label": "What it does", "features": ["feat_capability_success", "feat_capability_failure", "feat_eval_behaviour", "feat_agentic_action"]},
}
FEATURE_DIRECTIONS = ("for", "against", "both_or_neutral")
GROUP_LABELS = {"academic": "Academic", "ai_field": "AI field", "general": "General and culture", "journalism": "Journalism and politics", "religion": "Religion and spirituality"}

# Engagement norms. A post is compared with the other newsletter and podcast posts of its publication in the window
# (archive-meta crawl, stage 6). Restacked Notes are excluded: they carry the original's reaction count and would
# inflate the norm of any publication that restacks a lot. A ratio needs at least MIN_NORM_POSTS other posts.
NORM_TYPES = ("newsletter", "podcast")
NORM_METRICS = {"reactions": "reaction_count", "comments": "comment_count", "restacks": "restack_count"}
MIN_NORM_POSTS = 10


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


def _evidence(ctx: Ctx, construct: str, entity_type: str = "post") -> dict[int, str]:
    """Claude's latest evidence quote per item for one construct (the quote behind the coder-of-record value;
    a human decision changes the value in code_final, not the quote)."""
    out: dict[int, str] = {}
    for eid, ev in ctx.conn.execute(
        """SELECT c.entity_id, c.evidence FROM codes c JOIN code_runs r ON r.id=c.code_run_id
           WHERE r.engine='claude' AND c.entity_type=? AND c.construct=? AND c.evidence IS NOT NULL AND c.evidence!='' ORDER BY c.coded_at""",
        (entity_type, construct)):
        out[int(eid)] = ev
    return out


def stance_item_names(cb: Codebook) -> list[str]:
    """The fourteen 0.1.0 stance items: retired from 0.2.0 but still exported as the raw view behind the axes."""
    return [c.name for c in cb.by_group("stance", retired=True)] or [c.name for c in cb.by_group("stance")]


def relevant_ids(ctx: Ctx) -> list[int]:
    return [int(r[0]) for r in ctx.conn.execute(
        "SELECT entity_id FROM code_final WHERE entity_type='post' AND construct='relevance' AND value IN ('central','substantial') ORDER BY entity_id")]


def post_norm(own: dict[str, int], others: list[dict[str, int]]) -> dict:
    """How one post compares with the other posts of its publication: for each metric the leave-one-out mean
    (`baseline`), the post's rank among all of them (1 = highest, ties share the better rank) and the ratio of
    the post to the baseline (None when there are fewer than MIN_NORM_POSTS other posts or the baseline is 0)."""
    n = len(others)
    out: dict = {"n": n}
    for m in NORM_METRICS:
        v = own.get(m) or 0
        vals = [o.get(m) or 0 for o in others]
        base = sum(vals) / n if n else None
        rank = 1 + sum(1 for x in vals if x > v)
        ratio = round(v / base, 2) if base and n >= MIN_NORM_POSTS else None
        out[m] = {"baseline": round(base, 2) if base is not None else None, "rank": rank, "ratio": ratio}
    return out


def load_norms(ctx: Ctx, ids: list[int]) -> tuple[dict[int, dict], dict[int, dict]]:
    """Per-post norms for `ids` and per-publication means over all of the publication's NORM_TYPES posts in the window."""
    by_pub: dict[int, list[dict]] = defaultdict(list)
    q = ",".join("?" * len(NORM_TYPES))
    for r in ctx.conn.execute(
            f"SELECT id, publication_id, reaction_count, comment_count, restack_count FROM posts WHERE post_date >= ? AND title IS NOT NULL AND type IN ({q})",
            (ctx.cutoff, *NORM_TYPES)):
        by_pub[int(r["publication_id"])].append({"id": int(r["id"]), **{m: r[col] for m, col in NORM_METRICS.items()}})
    wanted = set(ids)
    pub_of = {int(r[0]): int(r[1]) for r in ctx.conn.execute(f"SELECT id, publication_id FROM posts WHERE id IN ({','.join('?' * len(ids))})", ids)}
    norms: dict[int, dict] = {}
    for pid in ids:
        rows = by_pub.get(pub_of[pid], [])
        own = next((r for r in rows if r["id"] == pid), None)
        if own is None:   # the post is not a newsletter/podcast or has no title: compare with all of them, rank unknown
            norms[pid] = post_norm({}, rows)
            norms[pid]["n"] = len(rows)
            continue
        norms[pid] = post_norm(own, [r for r in rows if r["id"] != pid])
    pubs: dict[int, dict] = {}
    for pub, rows in by_pub.items():
        pubs[pub] = {"n": len(rows), **{m: round(sum((r[m] or 0) for r in rows) / len(rows), 2) for m in NORM_METRICS}}
    return norms, pubs


def load_posts(ctx: Ctx, cb: Codebook) -> list[dict]:
    ids = relevant_ids(ctx)
    codes = _final(ctx, "post")
    pub_codes = _final(ctx, "publication")
    stance_items = stance_item_names(cb)
    arg_items = [c.name for c in cb.by_group("argument")]
    feat_items = [c.name for c in cb.by_group("feature")]
    q = ",".join("?" * len(ids))
    channels: dict[int, set[str]] = defaultdict(set)
    for pid, src in ctx.conn.execute(f"SELECT entity_id, source FROM discovery WHERE entity_type='post' AND entity_id IN ({q})", ids):
        channels[int(pid)].add(src)
    norms, _ = load_norms(ctx, ids)
    revision_quotes = _evidence(ctx, "view_revised")
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
        norm = norms[pid]
        lay = layout.get(pid)
        n = net.get(pid)
        out.append({
            "id": pid, "title": r["title"], "subtitle": r["subtitle"], "url": r["canonical_url"], "date": (r["post_date"] or "")[:10],
            "quarter": quarter(r["post_date"]), "words": r["wordcount"],
            "publication_id": int(r["publication_id"]), "host": r["host"], "publication": r["pub_name"], "author": r["author_name"], "subscribers": r["subs"],
            "community": community, "group": GROUPS.get(community or "", "general"),
            "relevance": c.get("relevance"), "genre": c.get("genre"), "claim_object": c.get("claim_object"), "reports_lab_view": c.get("reports_lab_view"),
            "view_revised": c.get("view_revised"),
            "view_revised_quote": revision_quotes.get(pid) if c.get("view_revised") not in (None, "none") else None,
            "stance": {k: c.get(k) for k in stance_items},
            "axes": axes_for(c, {k: c.get(k) for k in stance_items})[0],
            "axes_source": axes_for(c, {k: c.get(k) for k in stance_items})[1],
            "arguments": [k for k in arg_items if c.get(k) == "true"],
            # feature -> direction for the features the post points to; `features_coded` separates a post with no
            # features (all not_cited) from one the feature pass has not reached
            "features": {k: c[k] for k in feat_items if c.get(k) not in (None, "not_cited")},
            "features_coded": any(c.get(k) is not None for k in feat_items),
            "reactions": r["reaction_count"], "comments": r["comment_count"], "restacks": r["restack_count"],
            "norm": norm,
            "baseline_reactions": norm["reactions"]["baseline"], "over_performance": norm["reactions"]["ratio"], "pub_rank": norm["reactions"]["rank"],
            "pub_posts_in_window": norm["n"] + 1,
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
    items = [{"name": c.name, "claim": c.claim} for c in (cb.by_group("stance", retired=True) or cb.by_group("stance"))]
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


def axis_tables(posts: list[dict]) -> dict:
    """The five derived axes (mcreview.axes), tabulated like stance_tables, plus the joint distribution of the
    two 'now' axes: the experience x cognition profile is where 'thinks but is not conscious' shows up."""
    def table(subset):
        return {a: {lv: sum(1 for p in subset if p["axes"][a] == lv) for lv in LEVELS} for a in AXES}
    by_group = {g: table([p for p in posts if p["group"] == g]) for g in GROUP_LABELS}
    by_genre = {g: table([p for p in posts if p["genre"] == g]) for g in sorted({p["genre"] for p in posts if p["genre"]})}
    by_object = {g: table([p for p in posts if p["claim_object"] == g]) for g in sorted({p["claim_object"] for p in posts if p["claim_object"]})}
    unbiased = [p for p in posts if p["unbiased"] and p["quarter"]]
    by_quarter = {qq: table([p for p in unbiased if p["quarter"] == qq]) for qq in sorted({p["quarter"] for p in unbiased})}
    profile = Counter((p["axes"]["experience_now"], p["axes"]["cognition_now"]) for p in posts)
    profile_ag = Counter((p["axes"]["experience_now"], p["axes"]["agency_now"]) for p in posts)
    committed = Counter(sum(1 for a in AXES if p["axes"][a] not in ("not_addressed", "discussed")) for p in posts)
    source = Counter(p["axes_source"] for p in posts)
    return {"axes": [{"name": a, **{k: v for k, v in d.items() if k != "items"}, "items": d["items"]} for a, d in AXES.items()],
            "levels": list(LEVELS), "n": len(posts), "overall": table(posts), "by_group": by_group, "by_genre": by_genre,
            "by_claim_object": by_object, "by_quarter_unbiased": by_quarter, "n_unbiased": len(unbiased),
            "profile_experience_cognition": [{"experience_now": k[0], "cognition_now": k[1], "n": v} for k, v in profile.items()],
            "profile_experience_agency": [{"experience_now": k[0], "agency_now": k[1], "n": v} for k, v in profile_ag.items()],
            "axes_committed_per_post": {str(k): v for k, v in sorted(committed.items())}, "axes_source": dict(source), "group_labels": GROUP_LABELS}


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
            "axes_experience_now": _count(with_arg, lambda p: p["axes"]["experience_now"]),
        })
    return out


def feature_tables(ctx: Ctx, posts: list[dict], cb: Codebook) -> dict:
    """The thirteen `feat_*` questions: how often each feature of the systems is pointed to, in which direction,
    by publication type, and by quarter on the recency-unbiased channels. Shares are of posts the feature pass has
    coded, so a partial pass reports shares rather than undercounts. Example quotes are Claude's evidence for the
    highest-reaction posts in each direction."""
    coded = [p for p in posts if p["features_coded"]]
    n = len(coded) or 1
    unbiased = [p for p in coded if p["unbiased"] and p["quarter"]]
    quarters = sorted({p["quarter"] for p in unbiased})
    group_n = {g: sum(1 for p in coded if p["group"] == g) for g in GROUP_LABELS}
    quarter_n = {qq: sum(1 for p in unbiased if p["quarter"] == qq) for qq in quarters}
    family_of = {f: fam for fam, d in FEATURE_FAMILIES.items() for f in d["features"]}
    out = []
    for c in cb.by_group("feature"):
        with_f = [p for p in coded if c.name in p["features"]]
        over = [p["over_performance"] for p in with_f if p["over_performance"] is not None]
        ev = _evidence(ctx, c.name)
        examples = {}
        for d in FEATURE_DIRECTIONS:
            top = sorted((p for p in with_f if p["features"][c.name] == d and ev.get(p["id"])), key=lambda p: -(p["reactions"] or 0))[:4]
            examples[d] = [{"id": p["id"], "title": p["title"], "publication": p["publication"] or p["host"], "url": p["url"], "date": p["date"], "quote": ev[p["id"]]} for p in top]
        out.append({
            "name": c.name, "label": FEATURE_LABELS.get(c.name, c.name), "family": family_of.get(c.name), "instructions": c.instructions,
            "n": len(with_f), "share": round(len(with_f) / n, 4),
            "direction": {d: sum(1 for p in with_f if p["features"][c.name] == d) for d in FEATURE_DIRECTIONS},
            "by_group": {g: {d: sum(1 for p in with_f if p["group"] == g and p["features"][c.name] == d) for d in FEATURE_DIRECTIONS} for g in GROUP_LABELS},
            "by_quarter_unbiased": {qq: {d: sum(1 for p in with_f if p["unbiased"] and p["quarter"] == qq and p["features"][c.name] == d) for d in FEATURE_DIRECTIONS} for qq in quarters},
            "median_over_performance": round(statistics.median(over), 2) if over else None,
            "examples": examples,
        })
    per_post = Counter(len(p["features"]) for p in coded)
    # Co-citation: how often two features are pointed to in the same post (upper triangle, by name order).
    names = [c.name for c in cb.by_group("feature")]
    pairs = Counter()
    for p in coded:
        fs = sorted(p["features"])
        for i, a in enumerate(fs):
            for b in fs[i + 1:]:
                pairs[(a, b)] += 1
    # By side. A post affirms if it answers yes (or a qualified yes) on at least one of the six questions and no on
    # none; it denies if the reverse. For each side: the features cited in the side's own direction, counted over
    # the side's posts that cite at least one such feature, and how many such features each of those posts cites.
    def side(p: dict) -> str | None:
        ys = sum(1 for a in AXES if p["axes"][a] in ("yes", "yes_qualified"))
        ns = sum(1 for a in AXES if p["axes"][a] == "no")
        return "affirm" if ys and not ns else "deny" if ns and not ys else None
    sides = {}
    for s, d in (("affirm", "for"), ("deny", "against")):
        ps = [p for p in coded if side(p) == s]
        citing = [p for p in ps if any(v == d for v in p["features"].values())]
        sides[s] = {"direction": d, "n": len(ps), "citing": len(citing),
                    "features": {f: sum(1 for p in citing if p["features"].get(f) == d) for f in names},
                    "per_post": {str(k): v for k, v in sorted(Counter(sum(1 for v in p["features"].values() if v == d) for p in citing).items())}}
    return {"features": out, "directions": list(FEATURE_DIRECTIONS), "families": [{"key": k, **v} for k, v in FEATURE_FAMILIES.items()],
            "labels": FEATURE_LABELS, "group_labels": GROUP_LABELS, "sides": sides,
            "n_posts": len(posts), "n_coded": len(coded), "n_unbiased": len(unbiased), "group_n": group_n, "quarter_n_unbiased": quarter_n,
            "features_per_post": {str(k): v for k, v in sorted(per_post.items())},
            "any_feature": sum(1 for p in coded if p["features"]),
            "co_citation": [{"a": a, "b": b, "n": v} for (a, b), v in pairs.items()], "names": names}


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
            "axes_experience_now": _count(ps, lambda p: p["axes"]["experience_now"]),
            "axes_cognition_now": _count(ps, lambda p: p["axes"]["cognition_now"]),
            "axes_agency_now": _count(ps, lambda p: p["axes"]["agency_now"]),
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
    # Per-publication stance counts on every item (asserts, denies, agnostic, discusses) for colouring nodes,
    # and the same on the derived axes (yes, yes_qualified, unsure, discussed, no).
    stance_items = stance_item_names(Codebook())
    pub_stance: dict[int, dict[str, list[int]]] = defaultdict(lambda: {it: [0, 0, 0, 0] for it in stance_items})
    axis_levels = ("yes", "yes_qualified", "unsure", "discussed", "no")
    pub_axes: dict[int, dict[str, list[int]]] = defaultdict(lambda: {a: [0] * len(axis_levels) for a in AXES})
    for p in posts:
        for it in stance_items:
            v = p["stance"].get(it)
            if v in ("asserts", "denies", "agnostic", "discusses"):
                pub_stance[p["publication_id"]][it][("asserts", "denies", "agnostic", "discusses").index(v)] += 1
        for a in AXES:
            v = p["axes"][a]
            if v in axis_levels:
                pub_axes[p["publication_id"]][a][axis_levels.index(v)] += 1
    nodes = [{"id": int(r["publication_id"]), "host": r["host"], "name": r["name"], "community": r["community"],
              "stance": pub_stance.get(int(r["publication_id"])), "axes": pub_axes.get(int(r["publication_id"])),
              "group": GROUPS.get((pub_codes.get(int(r["publication_id"])) or {}).get("community", ""), None),
              "relevant_posts": rel_pubs.get(int(r["publication_id"]), 0),
              "in_pubs": r["in_pubs"], "out_pubs": r["out_pubs"], "in_posts": r["in_posts"], "pagerank": round(r["pagerank"], 6), "betweenness": round(r["betweenness"], 2),
              "x": round(r["x"], 3) if r["x"] is not None else None, "y": round(r["y"], 3) if r["y"] is not None else None} for r in pub_rows]
    edges = [{"source": int(r[0]), "target": int(r[1]), "weight": int(r[2]), "backbone": int(r[3])} for r in ctx.conn.execute("SELECT * FROM pub_edges")]
    post_ids = {p["id"] for p in posts}
    post_edges = [{"source": int(r[0]), "target": int(r[1])} for r in ctx.conn.execute("SELECT src_post_id, dst_post_id FROM network_edges") if int(r[0]) in post_ids and int(r[1]) in post_ids]
    # cross-camp citation: position of citing vs cited post on current consciousness (raw item) and on the
    # derived experience axis
    st = {p["id"]: p["stance"].get("current_conscious") for p in posts}
    camp = Counter((st.get(e["source"]), st.get(e["target"])) for e in post_edges)
    ax = {p["id"]: p["axes"]["experience_now"] for p in posts}
    camp_ax = Counter((ax.get(e["source"]), ax.get(e["target"])) for e in post_edges)
    return {"pub_nodes": nodes, "pub_edges": edges, "post_edges": post_edges,
            "cross_camp": [{"citing": k[0], "cited": k[1], "n": v} for k, v in camp.items()],
            "cross_camp_axes": [{"citing": k[0], "cited": k[1], "n": v} for k, v in camp_ax.items()]}


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


KIND_RANK = {"doi": 0, "arxiv": 1, "substack_post": 2, "wikipedia": 3, "book": 4, "web": 5, "homepage": 6, "maybe_substack_post": 7}
TITLE_RANK = {"post": 0, "doi_csl": 1, "crossref": 1, "arxiv_page": 1, "wikipedia": 1, "openlibrary": 2, "page": 3, "pdf": 3, "oembed": 3, "brave": 4, "anchor": 5}


def merge_works(works: list[dict]) -> list[dict]:
    """Collapse references that are one cited work. Each work dict carries id, kind, identifier, url, domain,
    title, title_source, target_post_id and the sets citing_posts/citing_pubs. Two passes: by work key
    (DOI, arXiv id, ASIN, Wikipedia title, corpus post, or the URL after re-normalisation, so a publisher
    page, its PDF and its doi.org link merge), then by title (preprint and journal version, lab blog and
    paper, mirrors of a PDF). The surviving entry keeps the most canonical kind and the best-sourced title;
    `aliases` lists the merged URLs."""
    def better(a: dict, b: dict) -> dict:
        return min((a, b), key=lambda w: (KIND_RANK.get(w["kind"], 9), -len(w["citing_posts"]), w["id"]))

    def absorb(keep: dict, other: dict) -> dict:
        prim = better(keep, other)
        sec = other if prim is keep else keep
        ta, tb = (prim.get("title"), prim.get("title_source")), (sec.get("title"), sec.get("title_source"))
        title, source = min((ta, tb), key=lambda x: (x[0] is None, TITLE_RANK.get(x[1] or "", 8)))
        merged = {**prim, "title": title, "title_source": source,
                  "citing_posts": prim["citing_posts"] | sec["citing_posts"], "citing_pubs": prim["citing_pubs"] | sec["citing_pubs"],
                  "aliases": sorted(set(prim.get("aliases", [])) | set(sec.get("aliases", [])) | {sec["url"]} - {prim["url"]})}
        return merged

    by_key: dict[str, dict] = {}
    for w in works:
        if w["kind"] in ("web", "doi", "arxiv", "book", "homepage"):   # current normalisation rules (e.g. arXiv DOIs -> arXiv) decide the canonical form
            r = refs_mod.normalize(w["url"])
            if r is not None and r.kind in ("web", "doi", "arxiv", "book", "homepage") and r.url_norm != w["url"]:
                w = {**w, "url": r.url_norm, "kind": r.kind, "domain": r.domain, "aliases": [w["url"]]}
        k = refs_mod.work_key(w["kind"], w.get("identifier"), w["url"], w.get("target_post_id"))
        by_key[k] = absorb(by_key[k], w) if k in by_key else {**w, "aliases": w.get("aliases", [])}
    by_title: dict[str, dict] = {}
    out: list[dict] = []

    def profile(w: dict) -> bool:
        """Homepages and social profiles carry an organisation's or person's name, not a work's."""
        path = w["url"].split("//", 1)[-1].split("/", 1)[1] if "/" in w["url"].split("//", 1)[-1] else ""
        return w["kind"] == "homepage" or (w.get("tier") == "social" and ("/status/" not in path and "watch" not in path and "/comments/" not in path
                                                                           and "/episode/" not in path and "/video/" not in path and path.count("/") < 2))

    for w in by_key.values():
        tk = refs_mod.title_key(w.get("title")) if w["kind"] != "wikipedia" and w.get("title_source") != "slug" and not profile(w) else None
        if tk is None:
            out.append(w)
        elif tk in by_title:
            by_title[tk] = absorb(by_title[tk], w)
        else:
            by_title[tk] = w
    return out + list(by_title.values())


def source_tables(ctx: Ctx, posts: list[dict]) -> dict:
    tiers_cfg = load_yaml("domain_tiers.yaml")
    tier_for = _tier_lookup(tiers_cfg)
    ids = [p["id"] for p in posts]
    group_of = {p["id"]: p["group"] for p in posts}
    q = ",".join("?" * len(ids))
    raw: dict[int, dict] = {}
    for r in ctx.conn.execute(
        f"""SELECT pr.post_id, r.id, r.kind, r.domain, r.title, r.title_source, r.url_norm, r.identifier, r.target_post_id FROM post_refs pr JOIN refs r ON r.id=pr.ref_id WHERE pr.post_id IN ({q})""", ids):
        if tier_for(r["kind"], r["domain"]) is None:
            continue
        w = raw.setdefault(int(r["id"]), {"id": int(r["id"]), "kind": r["kind"], "domain": r["domain"], "title": r["title"], "title_source": r["title_source"],
                                           "url": r["url_norm"], "identifier": r["identifier"], "target_post_id": r["target_post_id"], "citing_posts": set(), "citing_pubs": set()})
        w["citing_posts"].add(int(r["post_id"]))
    pub_of = {p["id"]: p["publication_id"] for p in posts}
    for w in raw.values():
        w["citing_pubs"] = {pub_of[p] for p in w["citing_posts"]}
    works = {}
    tier_posts: dict[str, set[int]] = defaultdict(set)
    tier_group: dict[str, Counter] = defaultdict(Counter)
    for w in raw.values():
        w["tier"] = tier_for(w["kind"], w["domain"])
    for w in merge_works(list(raw.values())):
        w["tier"] = tier_for(w["kind"], w["domain"])
        if not w.get("title"):   # display-only fallback from the URL; never stored
            st = refs_mod.slug_title(w["url"])
            if st:
                w["title"], w["title_source"] = st, "slug"
        works[w["id"]] = w
        for pid in w["citing_posts"]:
            tier_posts[w["tier"]].add(pid)
            tier_group[w["tier"]][group_of[pid]] += 1
    top = sorted(works.values(), key=lambda w: (len(w["citing_pubs"]), len(w["citing_posts"])), reverse=True)
    def ser(w):
        return {k: (len(v) if isinstance(v, set) else v) for k, v in w.items() if k not in ("target_post_id", "identifier")}
    by_tier = {t: [ser(w) for w in top if w["tier"] == t][:25] for t in sorted(tier_posts)}
    # named people
    names = load_yaml("names.yaml")["people"]
    compiled = [(n["name"], n["group"], [re.compile(p) for p in n["patterns"]]) for n in names]
    wikipedia = {n["name"]: "https://en.wikipedia.org/wiki/" + quote(n["wikipedia"].replace(" ", "_")) for n in names if n.get("wikipedia")}
    mention_posts: dict[str, set[int]] = defaultdict(set)
    mention_group: dict[str, Counter] = defaultdict(Counter)
    for pid, body in ctx.conn.execute(f"SELECT id, body_text FROM posts WHERE id IN ({q})", ids):
        text = body or ""
        for name, _g, pats in compiled:
            if any(p.search(text) for p in pats):
                mention_posts[name].add(int(pid))
                mention_group[name][group_of[int(pid)]] += 1
    people = sorted([{"name": n, "group": g, "posts": len(mention_posts[n]), "share": round(len(mention_posts[n]) / (len(posts) or 1), 4), "by_group": dict(mention_group[n]),
                      "url": wikipedia.get(n)}
                     for n, g, _ in compiled], key=lambda d: d["posts"], reverse=True)
    return {"tiers": {t: {"posts_citing": len(ps), "works": sum(1 for w in works.values() if w["tier"] == t), "by_group": dict(tier_group[t])} for t, ps in tier_posts.items()},
            "top_works_by_tier": by_tier, "top_works": [ser(w) for w in top[:60]], "people": people, "n_posts": len(posts),
            "references_raw": len(raw), "works_merged": len(raw) - len(works)}


def publication_tables(ctx: Ctx, posts: list[dict]) -> list[dict]:
    pub_codes = _final(ctx, "publication")
    by_pub: dict[int, list[dict]] = defaultdict(list)
    for p in posts:
        by_pub[p["publication_id"]].append(p)
    net = {int(r[0]): r for r in ctx.conn.execute("SELECT publication_id, in_pubs, out_pubs, pagerank, betweenness, community FROM pub_network")}
    _, pub_norms = load_norms(ctx, [p["id"] for p in posts])
    out = []
    for pid, ps in by_pub.items():
        pn = pub_norms.get(pid)
        u = ctx.conn.execute("SELECT host, name, author_name, free_subscriber_magnitude, hero_text, harvest_posts_in_window FROM publications WHERE id=?", (pid,)).fetchone()
        n = net.get(pid)
        community = (pub_codes.get(pid) or {}).get("community")
        out.append({
            "id": pid, "host": u["host"], "name": u["name"], "author": u["author_name"], "subscribers": u["free_subscriber_magnitude"], "tagline": u["hero_text"],
            "community": community, "group": GROUPS.get(community or "", "general"),
            "relevant_posts": len(ps), "posts_in_window": u["harvest_posts_in_window"],
            "relevant_share": round(len(ps) / u["harvest_posts_in_window"], 4) if u["harvest_posts_in_window"] else None,
            "median_reactions": statistics.median([p["reactions"] or 0 for p in ps]),
            "baseline_reactions": pn["reactions"] if pn else None, "norm_posts": pn["n"] if pn else 0,
            "in_pubs": int(n["in_pubs"]) if n else 0, "out_pubs": int(n["out_pubs"]) if n else 0, "pagerank": round(n["pagerank"], 6) if n else None,
            "betweenness": round(n["betweenness"], 2) if n else None, "network_community": int(n["community"]) if n else None,
            "stance_current_conscious": _count(ps, lambda p: p["stance"].get("current_conscious")),
            "axes_experience_now": _count(ps, lambda p: p["axes"]["experience_now"]),
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


def axes_derived_vs_coded(ctx: Ctx, cb: Codebook) -> dict | None:
    """Codebook 0.2.0 check: the six axes derived from the 0.1.0 stance items (mcreview.axes.derive) against the
    same axes coded directly by Claude at 0.2.0, post by post over the relevant set. Reads the engines' own
    0.2.0 codes and the coder-of-record rows for the retired items (materialise carries them forward under the
    current version, since they were only ever coded at 0.1.0). reports_only counts as not_addressed on both sides."""
    from .axes import derive

    items = set(stance_item_names(cb))
    old: dict[int, dict] = defaultdict(dict)
    q = ",".join("?" * len(items))
    for eid, con, val in ctx.conn.execute(f"SELECT entity_id, construct, value FROM code_final WHERE entity_type='post' AND construct IN ({q})", list(items)):
        old[int(eid)][con] = val
    new: dict[int, dict] = defaultdict(dict)
    for eid, con, val in ctx.conn.execute(
        """SELECT c.entity_id, c.construct, c.value FROM codes c JOIN code_runs r ON r.id=c.code_run_id
           WHERE r.engine='claude' AND r.codebook_version='0.2.0' AND c.entity_type='post' ORDER BY c.coded_at"""):
        if con in AXES:
            new[int(eid)][con] = val
    posts = [p for p in new if len(new[p]) == len(AXES) and p in old]
    if not posts:
        return None
    norm = lambda v: "not_addressed" if v == "reports_only" else v  # noqa: E731
    polarity = {"yes": "pro", "yes_qualified": "pro", "no": "con", "unsure": "neutral", "discussed": "neutral", "not_addressed": "na"}
    out = {"n": len(posts), "levels": list(LEVELS), "axes": []}
    for ax, meta in AXES.items():
        t: Counter = Counter()
        for p in posts:
            t[(derive(old[p])[ax], norm(new[p][ax]))] += 1
        n = len(posts)
        both = {k: v for k, v in t.items() if polarity[k[0]] != "na" and polarity[k[1]] != "na"}
        nb = sum(both.values())
        out["axes"].append({
            "name": ax, "label": meta["label"],
            "exact": round(sum(v for (d, c), v in t.items() if d == c) / n, 3),
            "coarse": round(sum(v for (d, c), v in t.items() if polarity[d] == polarity[c]) / n, 3),
            "n_both": nb, "polarity": round(sum(v for (d, c), v in both.items() if polarity[d] == polarity[c]) / nb, 3) if nb else None,
            "reversals": sum(v for (d, c), v in t.items() if {polarity[d], polarity[c]} == {"pro", "con"}),
            "na_derived": sum(v for (d, _), v in t.items() if d == "not_addressed"), "na_coded": sum(v for (_, c), v in t.items() if c == "not_addressed"),
            "matrix": [{"derived": d, "coded": c, "n": v} for (d, c), v in sorted(t.items())],
        })
    return out


def _hours(a: str | None, b: str | None) -> float | None:
    if not a or not b:
        return None
    from datetime import datetime
    return round((datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds() / 3600, 2)


def costs(ctx: Ctx) -> dict:
    """Usage and cost accounting for the Methods page: every engine run with its transport, tokens, recorded
    cost and wall-clock; search requests by backend; human coding time; pipeline stage durations.
    Claude runs through the Claude Code CLI are on the subscription: the CLI reports a list-price equivalent,
    recorded as `cost_usd` but never charged. The transport is read from the stored raw response of one code
    in the run (the CLI's JSON carries `modelUsage`; the API's carries `stop_reason`)."""
    c = ctx.conn
    cfg = ctx.settings.analysis.get("costs") or {}
    runs = []
    for r in c.execute("SELECT * FROM code_runs WHERE n_items>0 ORDER BY id"):
        ref = c.execute("SELECT raw_ref FROM codes WHERE code_run_id=? LIMIT 1", (r["id"],)).fetchone()
        transport = None
        if ref and ref[0]:
            try:
                d = json.loads(ctx.raw.get(ref[0]))
                transport = "cli" if ("modelUsage" in d or "session_id" in d) else ("api" if ("stop_reason" in d or "content" in d) else None)
            except Exception:  # noqa: BLE001
                transport = None
        if r["engine"] == "jev":
            transport = "api"
        charged = r["engine"] == "jev" or transport == "api"
        runs.append({"id": int(r["id"]), "engine": r["engine"], "model": r["model"], "transport": transport, "target": r["target"], "codebook_version": r["codebook_version"],
                     "n_items": int(r["n_items"]), "input_tokens": int(r["input_tokens"] or 0), "output_tokens": int(r["output_tokens"] or 0),
                     "cost_usd": round(float(r["cost_usd"] or 0), 2), "charged": charged, "started_at": r["started_at"], "finished_at": r["finished_at"],
                     "hours": _hours(r["started_at"], r["finished_at"])})
    totals = {
        "charged_usd": round(sum(x["cost_usd"] for x in runs if x["charged"]), 2),
        "subscription_list_price_usd": round(sum(x["cost_usd"] for x in runs if not x["charged"]), 2),
        "subscription_hours": round(sum(x["hours"] or 0 for x in runs if not x["charged"]), 1),
        "input_tokens": sum(x["input_tokens"] for x in runs), "output_tokens": sum(x["output_tokens"] for x in runs),
        "by_engine": {e: {"items": sum(x["n_items"] for x in runs if x["engine"] == e), "cost_usd": round(sum(x["cost_usd"] for x in runs if x["engine"] == e), 2),
                          "input_tokens": sum(x["input_tokens"] for x in runs if x["engine"] == e)} for e in sorted({x["engine"] for x in runs})},
    }
    search = [dict(r) for r in c.execute(
        """SELECT q.backend, q.variant, COUNT(DISTINCT q.id) queries, COUNT(DISTINCT q.id||':'||COALESCE(s.page,0)) requests, COUNT(*) results
           FROM search_results s JOIN queries q ON q.id=s.query_id GROUP BY 1,2 ORDER BY 1,2""")]
    brave_requests = sum(s["requests"] for s in search if s["backend"] == "brave")
    price = cfg.get("brave_price_per_1000")
    human = [dict(r) for r in c.execute(
        """SELECT s.sample_name, COUNT(*) decisions, COUNT(DISTINCT g.sample_id) items, ROUND(SUM(g.seconds)/60.0, 1) minutes, ROUND(AVG(g.seconds), 1) seconds_per_decision
           FROM gold_codes g JOIN gold_samples s ON s.id=g.sample_id GROUP BY 1 ORDER BY MIN(g.coded_at)""")]
    stages = [dict(r) for r in c.execute(
        """SELECT stage, COUNT(*) runs, ROUND(SUM((julianday(finished_at)-julianday(started_at))*24), 1) hours
           FROM runs WHERE finished_at IS NOT NULL AND status='ok' GROUP BY stage ORDER BY MIN(started_at)""")]
    http = {"fetch_log": c.execute("SELECT COUNT(*) FROM fetch_log").fetchone()[0], "http_cache": c.execute("SELECT COUNT(*) FROM http_cache").fetchone()[0]}
    return {"runs": runs, "totals": totals, "search": search, "brave_requests": brave_requests, "brave_price_per_1000": price,
            "brave_usd": round(brave_requests / 1000 * price, 2) if price else None,
            "human": human, "human_minutes": round(sum(h["minutes"] or 0 for h in human), 1), "stages": stages, "http": http}


def methods(ctx: Ctx) -> dict:
    from .code import agreement
    from .gold import human_agreement

    return {"jev_vs_claude_posts": agreement(ctx, "post"), "jev_vs_claude_publications": agreement(ctx, "publication"), "engine_vs_human": human_agreement(ctx),
            "axes_derived_vs_coded": axes_derived_vs_coded(ctx, Codebook()), "costs": costs(ctx),
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
        "stance_axes.json": axis_tables(posts),
        "arguments.json": argument_tables(posts, cb),
        "features.json": feature_tables(ctx, posts, cb),
        "topics.json": topic_tables(ctx, posts),
        "network.json": network_tables(ctx, posts),
        "sources.json": source_tables(ctx, posts),
        "publications.json": publication_tables(ctx, posts),
        "methods.json": methods(ctx),
        "codebook.json": {"version": cb.version, "domain": cb.domain, "stance_options": cb.stance_options,
                          "axes": [{"name": a, **d} for a, d in AXES.items()], "axis_levels": list(LEVELS),
                          "constructs": [{"name": c.name, "group": c.group, "primitive": c.primitive, "instructions": c.instructions, "claim": c.claim, "options": list(c.options), "since": c.since} for c in cb.constructs],
                          "retired_constructs": [{"name": c.name, "group": c.group, "primitive": c.primitive, "claim": c.claim, "options": list(c.options), "since": c.since, "retired_in": c.retired_in} for c in cb.retired],
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
