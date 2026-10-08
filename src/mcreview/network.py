"""Stage 5b: the citation network (docs/plan.md).

Nodes are corpus posts in the chosen population; a directed edge is a link from one post's body to another
corpus post (via refs.target_post_id). Links between posts of the same publication are dropped so self-
promotion does not count as citation. Metrics: in-degree by posts and by distinct citing publications,
PageRank, betweenness, Leiden communities. A publication-level graph is aggregated from the same edges with
a disparity-filter backbone (Serrano et al. 2009) for the static figure.
"""
from __future__ import annotations

import logging
import math
from collections import defaultdict

from . import db
from .context import Ctx
from .embeddings import population_ids

log = logging.getLogger(__name__)


def _edges(ctx: Ctx, node_ids: set[int], drop_intra: bool) -> list[tuple[int, int]]:
    rows = ctx.conn.execute(
        """SELECT pr.post_id src, r.target_post_id dst, ps.publication_id sp, pd.publication_id dp
           FROM post_refs pr JOIN refs r ON r.id=pr.ref_id JOIN posts ps ON ps.id=pr.post_id JOIN posts pd ON pd.id=r.target_post_id
           WHERE r.target_post_id IS NOT NULL AND pr.post_id<>r.target_post_id""").fetchall()
    out = set()
    for r in rows:
        s, d = int(r["src"]), int(r["dst"])
        if s not in node_ids or d not in node_ids:
            continue
        if drop_intra and r["sp"] == r["dp"]:
            continue
        out.add((s, d))
    return sorted(out)


def build(ctx: Ctx) -> None:
    import igraph as ig
    import leidenalg as la

    cfg = ctx.settings.analysis["network"]
    ids = population_ids(ctx, cfg.get("population", "subset"))
    node_set = set(ids)
    edges = _edges(ctx, node_set, bool(cfg.get("drop_intra_publication", True)))
    log.info("network: %d candidate nodes, %d edges", len(ids), len(edges))
    # keep only nodes that touch an edge; isolated posts carry no network information
    touched = sorted({s for s, _ in edges} | {d for _, d in edges})
    index = {pid: i for i, pid in enumerate(touched)}
    g = ig.Graph(n=len(touched), edges=[(index[s], index[d]) for s, d in edges], directed=True)
    pub_of = {int(r[0]): int(r[1]) for r in ctx.conn.execute(f"SELECT id, publication_id FROM posts WHERE id IN ({','.join('?'*len(touched))})", touched)} if touched else {}

    in_pubs: dict[int, set[int]] = defaultdict(set)
    for s, d in edges:
        in_pubs[d].add(pub_of[s])
    pr = g.pagerank(directed=True)
    bt = g.betweenness(directed=True)
    part = la.find_partition(g.as_undirected(mode="collapse"), la.RBConfigurationVertexPartition, resolution_parameter=float(cfg.get("leiden_resolution", 1.0)), seed=20260929)
    comm = part.membership
    layout = g.layout_fruchterman_reingold(niter=500, seed=None) if cfg.get("layout", "fr") == "fr" else g.layout_drl()
    coords = layout.coords
    ctx.conn.execute("DELETE FROM network_nodes")
    ctx.conn.execute("DELETE FROM network_edges")
    ctx.conn.executemany(
        "INSERT INTO network_nodes(post_id, community, in_posts, in_pubs, out_posts, pagerank, betweenness, x, y, run_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
        [(pid, int(comm[i]), int(g.indegree(i)), len(in_pubs.get(pid, ())), int(g.outdegree(i)), float(pr[i]), float(bt[i]), float(coords[i][0]), float(coords[i][1]), ctx.run_id)
         for pid, i in index.items()])
    ctx.conn.executemany("INSERT INTO network_edges(src_post_id, dst_post_id) VALUES (?,?)", edges)
    ctx.commit()
    ctx.counts["nodes"] = len(touched)
    ctx.counts["edges"] = len(edges)
    ctx.counts["communities"] = len(set(comm))
    _publication_graph(ctx, edges, pub_of, float(cfg.get("backbone_alpha", 0.05)))


def _publication_graph(ctx: Ctx, edges: list[tuple[int, int]], pub_of: dict[int, int], alpha: float) -> None:
    import igraph as ig
    import leidenalg as la

    w: dict[tuple[int, int], int] = defaultdict(int)
    for s, d in edges:
        ps, pd = pub_of[s], pub_of[d]
        if ps != pd:
            w[(ps, pd)] += 1
    pubs = sorted({p for e in w for p in e})
    idx = {p: i for i, p in enumerate(pubs)}
    g = ig.Graph(n=len(pubs), edges=[(idx[s], idx[d]) for s, d in w], directed=True)
    g.es["weight"] = [w[e] for e in w]
    # disparity filter on the undirected weighted projection
    strength = defaultdict(float)
    degree = defaultdict(int)
    und: dict[tuple[int, int], float] = defaultdict(float)
    for (s, d), wt in w.items():
        key = (min(s, d), max(s, d))
        und[key] += wt
    for (a, b), wt in und.items():
        strength[a] += wt; strength[b] += wt
        degree[a] += 1; degree[b] += 1
    backbone = set()
    for (a, b), wt in und.items():
        for node in (a, b):
            k = degree[node]
            if k <= 1:
                backbone.add((a, b)); break
            p = wt / strength[node]
            if (1 - p) ** (k - 1) < alpha:
                backbone.add((a, b)); break
    in_pubs: dict[int, set[int]] = defaultdict(set)
    out_pubs: dict[int, set[int]] = defaultdict(set)
    in_posts: dict[int, int] = defaultdict(int)
    for (s, d), wt in w.items():
        in_pubs[d].add(s); out_pubs[s].add(d); in_posts[d] += wt
    pr = g.pagerank(directed=True, weights="weight")
    bt = g.betweenness(directed=True, weights=None)
    part = la.find_partition(g.as_undirected(mode="collapse", combine_edges="sum"), la.RBConfigurationVertexPartition, weights="weight", seed=20260929)
    comm = part.membership
    # Positions are computed on the backbone only (the edges the figure draws); nodes without a backbone
    # edge get no position and are listed but not drawn. Laying out the full graph scatters hundreds of
    # tiny components around one dense core.
    bb_nodes = sorted({p for e in und if e in backbone for p in e})
    bb_idx = {p: i for i, p in enumerate(bb_nodes)}
    bb = ig.Graph(n=len(bb_nodes), edges=[(bb_idx[a], bb_idx[b]) for (a, b) in und if (a, b) in backbone])
    # Raw weights (up to dozens of links between two publications) make weighted Fruchterman-Reingold
    # collapse heavy pairs onto one point; log-damped weights keep the attraction ordering without that.
    bb.es["weight"] = [math.log1p(und[(a, b)]) for (a, b) in und if (a, b) in backbone]
    # grid=False: igraph's grid approximation (default above 1,000 vertices) drops repulsion between nearby
    # nodes, which piled the degree-one leaves of each hub onto a single point.
    bb_coords = bb.layout_fruchterman_reingold(niter=1500, weights="weight", grid=False).coords if bb_nodes else []
    pos = {p: bb_coords[i] for p, i in bb_idx.items()}
    ctx.conn.execute("DELETE FROM pub_network")
    ctx.conn.execute("DELETE FROM pub_edges")
    ctx.conn.executemany(
        "INSERT INTO pub_network(publication_id, community, in_pubs, out_pubs, in_posts, pagerank, betweenness, x, y, run_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
        [(p, int(comm[i]), len(in_pubs.get(p, ())), len(out_pubs.get(p, ())), in_posts.get(p, 0), float(pr[i]), float(bt[i]),
          float(pos[p][0]) if p in pos else None, float(pos[p][1]) if p in pos else None, ctx.run_id) for p, i in idx.items()])
    ctx.conn.executemany("INSERT INTO pub_edges(src_publication_id, dst_publication_id, weight, backbone) VALUES (?,?,?,?)",
                         [(s, d, wt, 1 if (min(s, d), max(s, d)) in backbone else 0) for (s, d), wt in w.items()])
    ctx.commit()
    ctx.counts["pub_nodes"] = len(pubs)
    ctx.counts["pub_edges"] = len(w)
    ctx.counts["pub_backbone_edges"] = sum(1 for e in w if (min(e), max(e)) in backbone)
    ctx.counts["pub_communities"] = len(set(comm))
