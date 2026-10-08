"""Stage 5a: document embeddings and the topic map (docs/plan.md).

Embeddings: an open sentence-transformer run locally. Essays exceed the model's context, so each body is
split into character chunks, every chunk is embedded, and the chunk vectors are mean-pooled and L2
normalised. The model name and chunking are recorded with every vector.

Topics: UMAP (10-D) -> HDBSCAN for clusters, UMAP (2-D) for the map, c-TF-IDF top terms and centroid
exemplars per cluster so a reader (or a model) can label them.
"""
from __future__ import annotations

import json
import logging
import math
import re
from collections import Counter

import numpy as np

from . import db
from .context import Ctx

log = logging.getLogger(__name__)

RELEVANT_POSTS_SQL = """
    SELECT entity_id FROM code_final WHERE entity_type='post' AND construct='relevance' AND value IN ('central','substantial')
"""


def population_ids(ctx: Ctx, which: str) -> list[int]:
    if which == "relevant":
        return [int(r[0]) for r in ctx.conn.execute(RELEVANT_POSTS_SQL + " ORDER BY entity_id")]
    return [int(r[0]) for r in ctx.conn.execute("SELECT post_id FROM analysis_subset ORDER BY post_id")]


def chunks_for(title: str, subtitle: str, body: str, chunk_chars: int, max_chunks: int) -> list[str]:
    head = " ".join(s for s in (title, subtitle) if s).strip()
    text = (head + "\n\n" + (body or "")).strip()
    out = []
    for i in range(0, len(text), chunk_chars):
        out.append(text[i : i + chunk_chars])
        if len(out) >= max_chunks:
            break
    return out or [head or "(empty)"]


def embed(ctx: Ctx, limit: int | None = None) -> None:
    from sentence_transformers import SentenceTransformer

    cfg = ctx.settings.analysis["embeddings"]
    model_name = cfg["model"]
    ids = population_ids(ctx, cfg.get("population", "relevant"))
    done = {int(r[0]) for r in ctx.conn.execute("SELECT post_id FROM embeddings WHERE model=?", (model_name,))}
    todo = [i for i in ids if i not in done]
    todo = todo[:limit] if limit else todo
    log.info("embedding %d posts with %s (%d already done)", len(todo), model_name, len(done))
    if not todo:
        return
    model = SentenceTransformer(model_name, device="cpu")
    bs = int(cfg.get("batch_size", 32))
    cc, mc = int(cfg["chunk_chars"]), int(cfg["max_chunks"])
    for start in range(0, len(todo), 64):
        batch_ids = todo[start : start + 64]
        rows = ctx.conn.execute(
            f"SELECT id, title, subtitle, body_text FROM posts WHERE id IN ({','.join('?'*len(batch_ids))})", batch_ids).fetchall()
        texts, owners = [], []
        for r in rows:
            ch = chunks_for(r["title"] or "", r["subtitle"] or "", r["body_text"] or "", cc, mc)
            texts += ch
            owners += [int(r["id"])] * len(ch)
        vecs = model.encode(texts, batch_size=bs, normalize_embeddings=True, show_progress_bar=False)
        by_post: dict[int, list[np.ndarray]] = {}
        for pid, v in zip(owners, vecs):
            by_post.setdefault(pid, []).append(v)
        now = db.now()
        for pid, vs in by_post.items():
            m = np.mean(np.stack(vs), axis=0)
            m = m / (np.linalg.norm(m) or 1.0)
            ctx.conn.execute(
                "INSERT OR REPLACE INTO embeddings(post_id, model, dim, n_chunks, vector, created_at) VALUES (?,?,?,?,?,?)",
                (pid, model_name, int(m.shape[0]), len(vs), m.astype(np.float32).tobytes(), now))
            ctx.bump("embedded")
        ctx.commit()
        if (start // 64) % 5 == 0:
            log.info("embedded %d / %d", min(start + 64, len(todo)), len(todo))


def load_vectors(ctx: Ctx, model_name: str, ids: list[int] | None = None) -> tuple[list[int], np.ndarray]:
    sql = "SELECT post_id, dim, vector FROM embeddings WHERE model=?"
    rows = ctx.conn.execute(sql + " ORDER BY post_id", (model_name,)).fetchall()
    if ids is not None:
        keep = set(ids)
        rows = [r for r in rows if int(r["post_id"]) in keep]
    pids = [int(r["post_id"]) for r in rows]
    X = np.stack([np.frombuffer(r["vector"], dtype=np.float32) for r in rows]) if rows else np.zeros((0, 1))
    return pids, X


WORD_RE = re.compile(r"[a-z][a-z\-']{2,}")
STOP = set("""the and for that with this are from was were have has had not but you your they their them our its
what which who whom when where why how all any can could would should will just like than then there here also into
about over under more most some such very been being because while after before between through during without within
one two three new like get got make made say said says see seen use used using way ways thing things even still much
many well back only own other others same each those these every both few less least lot lots yes per via upon onto
does did doing done may might must shall let lets really quite rather though although whether either neither nor
his her she him he it its we us me my mine ours yours theirs himself herself itself themselves ourselves yourself
ai llm llms model models post posts substack""".split())


def _tokens(text: str) -> list[str]:
    return [t for t in WORD_RE.findall(text.lower()) if t not in STOP]


def topics(ctx: Ctx) -> None:
    import hdbscan
    import umap

    cfg = ctx.settings.analysis["topics"]
    model_name = ctx.settings.analysis["embeddings"]["model"]
    ids = population_ids(ctx, ctx.settings.analysis["embeddings"].get("population", "relevant"))
    pids, X = load_vectors(ctx, model_name, ids)
    if len(pids) < 50:
        raise RuntimeError(f"only {len(pids)} embeddings; run `mcreview embed` first")
    u = cfg["umap"]
    seed = int(u.get("seed", 0))
    log.info("UMAP on %d x %d", *X.shape)
    Xc = umap.UMAP(n_neighbors=int(u["n_neighbors"]), min_dist=0.0, n_components=int(u["n_components_cluster"]), metric="cosine", random_state=seed).fit_transform(X)
    X2 = umap.UMAP(n_neighbors=int(u["n_neighbors"]), min_dist=float(u["min_dist"]), n_components=2, metric="cosine", random_state=seed).fit_transform(X)
    h = cfg["hdbscan"]
    cl = hdbscan.HDBSCAN(min_cluster_size=int(h["min_cluster_size"]), min_samples=int(h.get("min_samples") or 1), metric="euclidean",
                         cluster_selection_method=h.get("cluster_selection_method", "eom"),
                         cluster_selection_epsilon=float(h.get("cluster_selection_epsilon", 0.0)), prediction_data=True).fit(Xc)
    core_labels = cl.labels_.copy()
    labels = cl.labels_.copy()
    probs = cl.probabilities_.copy()
    n_clusters = int(labels.max()) + 1 if len(labels) else 0
    n_noise = int((labels == -1).sum())
    log.info("HDBSCAN: %d clusters, %d noise of %d", n_clusters, n_noise, len(labels))
    # Leaf selection leaves many peripheral points unassigned. For a complete map, attach each noise point to
    # the nearest cluster centroid in the clustering space and mark it peripheral (cluster_prob = 0); the
    # core membership is kept in topics.core_size and in cluster_prob > 0.
    if n_noise and n_clusters:
        cents = np.stack([Xc[core_labels == k].mean(axis=0) for k in range(n_clusters)])
        noise_idx = np.where(labels == -1)[0]
        d = ((Xc[noise_idx, None, :] - cents[None, :, :]) ** 2).sum(axis=2)
        labels[noise_idx] = d.argmin(axis=1)
        probs[noise_idx] = 0.0

    # c-TF-IDF over titles + first chunk of body per cluster
    docs = {int(r["id"]): ((r["title"] or "") + " " + (r["subtitle"] or "") + " " + (r["body_text"] or "")[:4000])
            for r in ctx.conn.execute(f"SELECT id, title, subtitle, body_text FROM posts WHERE id IN ({','.join('?'*len(pids))})", pids)}
    cluster_tf: dict[int, Counter] = {}
    df: Counter = Counter()
    for pid, lab in zip(pids, labels):
        toks = _tokens(docs.get(pid, ""))
        cluster_tf.setdefault(int(lab), Counter()).update(toks)
        df.update(set(toks))
    n_docs = len(pids)
    top_k = int(cfg.get("top_terms", 12))
    centroids = {}
    for lab in set(int(x) for x in labels):
        mask = labels == lab
        centroids[lab] = X[mask].mean(axis=0)
    rows_topics = []
    for lab, tf in cluster_tf.items():
        total = sum(tf.values()) or 1
        scored = {t: (c / total) * math.log(1 + n_docs / (df[t] or 1)) for t, c in tf.items() if c >= 2}
        top = [t for t, _ in sorted(scored.items(), key=lambda kv: kv[1], reverse=True)[:top_k]]
        mask = labels == lab
        idx = np.where(mask)[0]
        sims = X[idx] @ centroids[lab]
        ex = [pids[i] for i in idx[np.argsort(-sims)[: int(cfg.get("exemplars", 8))]]]
        rows_topics.append((ctx.run_id, int(lab), int(mask.sum()), int((core_labels == lab).sum()), json.dumps(top), json.dumps(ex)))
    ctx.conn.execute("DELETE FROM topics")
    ctx.conn.executemany("INSERT INTO topics(run_id, cluster, size, core_size, top_terms, exemplar_post_ids) VALUES (?,?,?,?,?,?)", rows_topics)
    ctx.conn.execute("DELETE FROM post_layout")
    ctx.conn.executemany("INSERT INTO post_layout(post_id, x, y, cluster, cluster_prob, run_id) VALUES (?,?,?,?,?,?)",
                         [(pid, float(X2[i, 0]), float(X2[i, 1]), int(labels[i]), float(probs[i]), ctx.run_id) for i, pid in enumerate(pids)])
    ctx.commit()
    ctx.counts["clusters"] = n_clusters
    ctx.counts["peripheral_assigned"] = n_noise
    ctx.counts["posts_laid_out"] = len(pids)


def export_topic_labels(ctx: Ctx, path) -> None:
    """Editable CSV: one row per cluster with the suggested label, description, terms and central titles.
    Edit the `label` and `description` columns, then `mcreview topics-import`."""
    import csv
    from pathlib import Path

    rows = ctx.conn.execute("SELECT cluster, size, core_size, label, description, top_terms, exemplar_post_ids FROM topics WHERE cluster>=0 ORDER BY size DESC").fetchall()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["cluster", "size", "core_size", "label", "description", "top_terms", "central_titles"])
        for r in rows:
            ex = json.loads(r["exemplar_post_ids"] or "[]")[:5]
            titles = [t[0] for t in ctx.conn.execute(f"SELECT title FROM posts WHERE id IN ({','.join('?'*len(ex))})", ex)] if ex else []
            w.writerow([r["cluster"], r["size"], r["core_size"], r["label"] or "", r["description"] or "", "; ".join(json.loads(r["top_terms"] or "[]")), " | ".join(titles)])
    log.info("wrote %d topic rows to %s", len(rows), path)


def import_topic_labels(ctx: Ctx, path) -> int:
    import csv
    from pathlib import Path

    n = 0
    with Path(path).open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ctx.conn.execute("UPDATE topics SET label=?, description=? WHERE cluster=?", (row["label"].strip(), (row.get("description") or "").strip(), int(row["cluster"])))
            n += 1
    ctx.conn.commit()
    ctx.counts["topic_labels_imported"] = n
    return n


def label_topics(ctx: Ctx, model: str = "claude-opus-5-5", only_missing: bool = True) -> None:
    """Ask Claude (via the Claude Code CLI, subscription) for a short label and one-line description per
    cluster from its top terms and exemplar titles. Labels are suggestions to be hand-checked."""
    import os
    import subprocess

    rows = ctx.conn.execute("SELECT cluster, size, top_terms, exemplar_post_ids, label FROM topics WHERE cluster>=0 ORDER BY size DESC").fetchall()
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}
    schema = json.dumps({"type": "object", "properties": {"label": {"type": "string", "description": "2-5 words, noun phrase"}, "description": {"type": "string", "description": "one short sentence, under 20 words, no lists of examples"}},
                         "required": ["label", "description"], "additionalProperties": False})
    system = ("You name topic clusters for a study of Substack writing about machine consciousness, cognition and moral status. "
              "Given a cluster's distinctive terms and the titles and subtitles of its most central posts, return a short label (2-5 words, a noun phrase, "
              "specific to what distinguishes this cluster from the rest of the corpus) and a one-sentence description. Do not use the words 'AI' or 'cluster' in the label unless unavoidable.")
    for r in rows:
        if only_missing and r["label"]:
            continue
        ex_ids = json.loads(r["exemplar_post_ids"] or "[]")
        titles = [f"- {t[0]}" + (f": {t[1]}" if t[1] else "") for t in ctx.conn.execute(
            f"SELECT title, subtitle FROM posts WHERE id IN ({','.join('?'*len(ex_ids))})", ex_ids)] if ex_ids else []
        prompt = f"Cluster of {r['size']} posts.\nDistinctive terms: {', '.join(json.loads(r['top_terms'] or '[]'))}\nCentral posts:\n" + "\n".join(titles)
        proc = subprocess.run(["claude", "-p", "--no-session-persistence", "--model", model, "--effort", "low", "--tools", "", "--output-format", "json",
                               "--json-schema", schema, "--system-prompt", system], input=prompt, capture_output=True, text=True, env=env, timeout=300)
        try:
            d = json.loads(proc.stdout)
            out = d.get("structured_output") or json.loads(d.get("result") or "{}")
        except json.JSONDecodeError:
            log.warning("cluster %s: unparseable label response", r["cluster"])
            continue
        if d.get("is_error") or not out.get("label"):
            log.warning("cluster %s: %s", r["cluster"], str(d.get("result"))[:120])
            continue
        ctx.conn.execute("UPDATE topics SET label=?, description=? WHERE cluster=?", (out["label"].strip(), out.get("description", "").strip(), r["cluster"]))
        ctx.conn.commit()
        ctx.bump("labelled")
        log.info("cluster %d (%d): %s", r["cluster"], r["size"], out["label"])
