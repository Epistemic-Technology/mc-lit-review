"""Incremental update: done-checks across codebook versions, topic assignment without re-clustering,
archive refresh stop rule, Brave freshness window."""
import json
import sqlite3
from types import SimpleNamespace

import numpy as np

from mcreview import brave, code, db, embeddings, harvest
from mcreview.codebook import Codebook


class FakeSettings:
    def __init__(self, analysis):
        self.analysis = analysis

    def __getitem__(self, key):
        return {"archive_meta": {"min_corpus_posts": 3}}[key]


class FakeCtx:
    def __init__(self, analysis=None):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(db.SCHEMA)
        self.run_id = db.start_run(self.conn, "test", "h", None, {})
        self.counts = {}
        self.cutoff = "2024-01-01"
        self.client = None
        self.settings = FakeSettings(analysis or {})

    def commit(self):
        self.conn.commit()

    def bump(self, key, n=1):
        self.counts[key] = self.counts.get(key, 0) + n

    def store_raw(self, r, ext="json"):
        return "raw"


def _run(c, engine, version, model="m"):
    cur = c.execute("INSERT INTO code_runs(engine, model, codebook_version, target, started_at) VALUES (?,?,?,?,?)", (engine, model, version, "posts", db.now()))
    return cur.lastrowid


def _code(c, run, pid, construct, value="x", rep=0):
    c.execute("INSERT INTO codes(code_run_id, entity_type, entity_id, construct, repeat_no, value, coded_at) VALUES (?,?,?,?,?,?,?)",
              (run, "post", pid, construct, rep, value, db.now()))


def test_coded_accepts_earlier_versions_of_unchanged_constructs():
    cb = Codebook()
    ctx = FakeCtx()
    c = ctx.conn
    old = [x.name for x in cb.constructs if x.since == "0.1.0"]
    six = [x.name for x in cb.constructs if x.since == "0.2.0"]
    # One run per codebook version at which a current construct was introduced, so the test follows the codebook.
    runs = {v: _run(c, "claude", v) for v in sorted({x.since for x in cb.constructs})}
    r1 = runs["0.1.0"]
    # post 1: fully coded, each construct at the version that introduced it; post 2: 0.1.0 only (irrelevant, never
    # got the later constructs); post 3: coded on a retired construct only (should not count as coded on anything current)
    for x in cb.constructs:
        _code(c, runs[x.since], 1, x.name)
    for con in old:
        _code(c, r1, 2, con)
    _code(c, r1, 3, cb.retired[0].name)
    done_all = code._coded(ctx, "claude", "m", cb.version, "post", 0, None, cb)
    assert done_all == {1, 2}, "a full-codebook run skips every post the engine has coded before"
    done_six = code._coded(ctx, "claude", "m", cb.version, "post", 0, six, cb)
    assert done_six == {1}, "an explicit --construct run still fills the constructs a post lacks"
    strict = code._coded(ctx, "claude", "m", cb.version, "post", 0, None)
    assert strict == {1}, "without a codebook the exact-version rule is unchanged"
    assert code.constructs_coded_before(ctx, "claude", cb) is None
    rj = _run(c, "jev", "0.1.0")
    for con in old:
        _code(c, rj, 1, con)
    assert sorted(code.constructs_coded_before(ctx, "jev", cb)) == sorted(old)


def test_assign_new_posts_keeps_clusters():
    ctx = FakeCtx(analysis={"embeddings": {"model": "m", "population": "relevant"}})
    c = ctx.conn
    pub = db.upsert_publication(c, "a.substack.com", None, confirmed=True)
    vecs = {}
    rng = np.random.default_rng(0)
    for i in range(1, 41):
        pid = db.upsert_post(c, pub, f"p{i}", None, {"title": f"t{i}", "metadata_source": "stub", "entry_round": 0})
        cluster = 0 if i <= 20 else 1
        v = np.array([1.0, 0.0, 0.0] if cluster == 0 else [0.0, 1.0, 0.0], dtype=np.float32) + rng.normal(0, 0.05, 3).astype(np.float32)
        vecs[pid] = v
        c.execute("INSERT INTO embeddings(post_id, model, dim, n_chunks, vector, created_at) VALUES (?,?,?,?,?,?)", (pid, "m", 3, 1, v.tobytes(), db.now()))
        c.execute("INSERT INTO post_layout(post_id, x, y, cluster, cluster_prob, run_id) VALUES (?,?,?,?,?,?)", (pid, 0.0 if cluster == 0 else 10.0, float(i % 3), cluster, 0.9, None))
        c.execute("INSERT INTO code_final VALUES ('post',?,?,?,?,?,?,?)", (pid, "relevance", "central", None, "claude", "0.3.0", db.now()))
    c.execute("INSERT INTO topics(run_id, cluster, size, core_size, top_terms, exemplar_post_ids, label) VALUES (NULL,0,20,20,'[]','[]','A'), (NULL,1,20,20,'[]','[]','B')")
    # a new relevant post near cluster 1, embedded but not laid out
    new = db.upsert_post(c, pub, "new", None, {"title": "new", "metadata_source": "stub", "entry_round": 0})
    v = np.array([0.05, 0.98, 0.0], dtype=np.float32)
    c.execute("INSERT INTO embeddings(post_id, model, dim, n_chunks, vector, created_at) VALUES (?,?,?,?,?,?)", (new, "m", 3, 1, v.tobytes(), db.now()))
    c.execute("INSERT INTO code_final VALUES ('post',?,?,?,?,?,?,?)", (new, "relevance", "substantial", None, "claude", "0.3.0", db.now()))
    # and one not yet embedded: reported, not placed
    pending = db.upsert_post(c, pub, "pending", None, {"title": "pending", "metadata_source": "stub", "entry_round": 0})
    c.execute("INSERT INTO code_final VALUES ('post',?,?,?,?,?,?,?)", (pending, "relevance", "central", None, "claude", "0.3.0", db.now()))
    n = embeddings.assign_new_posts(ctx, k=5)
    assert n == 1
    row = c.execute("SELECT x, y, cluster, cluster_prob FROM post_layout WHERE post_id=?", (new,)).fetchone()
    assert row["cluster"] == 1 and row["cluster_prob"] == 0.0 and 9.0 < row["x"] < 11.0
    sizes = {r[0]: (r[1], r[2], r[3]) for r in c.execute("SELECT cluster, size, core_size, label FROM topics")}
    assert sizes[1] == (21, 20, "B") and sizes[0] == (20, 20, "A"), "size grows, core size and label untouched"
    assert c.execute("SELECT COUNT(*) FROM post_layout WHERE post_id=?", (pending,)).fetchone()[0] == 0
    assert embeddings.assign_new_posts(ctx, k=5) == 0, "second pass finds nothing new (pending still has no embedding)"


def test_archive_refresh_stops_at_first_known_page(monkeypatch):
    ctx = FakeCtx()
    c = ctx.conn
    pub = db.upsert_publication(c, "a.substack.com", None, confirmed=True)
    c.execute("UPDATE publications SET harvested_at='2026-10-01T00:00:00+00:00', harvest_pages=3, harvest_posts_in_window=40 WHERE id=?", (pub,))
    old_post = db.upsert_post(c, pub, "known-1", None, {"metadata_source": "archive", "entry_round": 0, "post_date": "2026-09-20T00:00:00Z"})
    c.execute("INSERT INTO code_final VALUES ('post',?,?,?,?,?,?,?)", (old_post, "relevance", "central", None, "claude", "0.3.0", db.now()))
    pages = [
        [{"id": 1, "slug": "new-1", "post_date": "2026-10-10T00:00:00Z", "title": "n1"}, {"id": 2, "slug": "new-2", "post_date": "2026-10-05T00:00:00Z", "title": "n2"}],
        [{"id": 3, "slug": "known-1", "post_date": "2026-09-20T00:00:00Z", "title": "k1"}],
        [{"id": 4, "slug": "never-reached", "post_date": "2026-09-01T00:00:00Z", "title": "x"}],
    ]
    served = []

    def fake_iter(client, host, cutoff, max_pages=1000):
        for p in pages:
            served.append(p)
            yield SimpleNamespace(ok=True, status=200, content=b"[]"), p

    monkeypatch.setattr(harvest.substack, "iter_archive", fake_iter)
    monkeypatch.setattr(harvest.substack, "post_fields", lambda p, src, now, ref: {"title": p["title"], "post_date": p["post_date"], "metadata_source": "archive"})
    harvest.archive_meta(ctx, relevant_only=True, refresh=True)
    assert len(served) == 2, "stopped on the page where every post was already known"
    slugs = {r[0] for r in c.execute("SELECT slug FROM posts")}
    assert slugs == {"known-1", "new-1", "new-2"}
    row = c.execute("SELECT harvest_pages, harvest_posts_in_window FROM publications WHERE id=?", (pub,)).fetchone()
    assert (row[0], row[1]) == (5, 42)
    assert c.execute("SELECT COUNT(*) FROM discovery WHERE source='archive_context'").fetchone()[0] == 2
    assert ctx.counts["archive_refresh_new_posts"] == 2


def test_brave_freshness_in_cache_key():
    plain = brave._url("q", 0)
    fresh = brave._url("q", 0, freshness="2026-09-20to2026-10-13")
    assert plain != fresh and "freshness=2026-09-20to2026-10-13" in fresh
    assert brave.freshness_window("2026-09-20", "2026-10-13") == "2026-09-20to2026-10-13"


def test_upsert_publication_merges_host_row_into_id_row():
    ctx = FakeCtx()
    c = ctx.conn
    by_id = db.upsert_publication(c, "a.substack.com", None, {"substack_id": 7}, confirmed=True)
    by_host = db.upsert_publication(c, "www.a.com", None, confirmed=True)
    p1 = db.upsert_post(c, by_host, "x", None, {"title": "x", "metadata_source": "stub", "entry_round": 0})
    # Substack search now reports www.a.com with substack_id 7: same publication as a.substack.com
    pid = db.upsert_publication(c, "www.a.com", None, {"substack_id": 7, "name": "A"}, confirmed=True)
    assert pid == by_id
    assert c.execute("SELECT COUNT(*) FROM publications").fetchone()[0] == 1
    row = c.execute("SELECT host, alias_hosts, name FROM publications WHERE id=?", (pid,)).fetchone()
    assert row["host"] == "a.substack.com" and "www.a.com" in json.loads(row["alias_hosts"]) and row["name"] == "A"
    assert c.execute("SELECT publication_id FROM posts WHERE id=?", (p1,)).fetchone()[0] == pid
