"""Data-access semantics that the provenance analysis depends on."""
import sqlite3

from mcreview import db


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(db.SCHEMA)
    return conn


def test_entry_round_is_first_wins():
    c = _conn()
    pub = db.upsert_publication(c, "x.substack.com", None, confirmed=True)
    pid = db.upsert_post(c, pub, "slug", None, {"metadata_source": "stub", "entry_round": 0, "title": "A"})
    db.upsert_post(c, pub, "slug", None, {"metadata_source": "stub", "entry_round": 2, "title": "B"})
    row = c.execute("SELECT entry_round, title FROM posts WHERE id=?", (pid,)).fetchone()
    assert row["entry_round"] == 0          # earliest route into the corpus is kept
    assert row["title"] == "B"              # other non-null fields refresh


def test_later_round_post_keeps_its_round_when_refreshed_by_post_endpoint():
    c = _conn()
    pub = db.upsert_publication(c, "x.substack.com", None, confirmed=True)
    pid = db.upsert_post(c, pub, "s", None, {"metadata_source": "stub", "entry_round": 1})
    db.upsert_post(c, pub, "s", None, {"metadata_source": "post", "title": "T", "wordcount": 10})
    row = c.execute("SELECT entry_round, title, wordcount FROM posts WHERE id=?", (pid,)).fetchone()
    assert (row["entry_round"], row["title"], row["wordcount"]) == (1, "T", 10)


def test_publication_alias_merges_on_substack_id():
    c = _conn()
    a = db.upsert_publication(c, "sub.substack.com", None, {"substack_id": 7}, confirmed=True)
    b = db.upsert_publication(c, "www.custom.com", None, {"substack_id": 7}, confirmed=True)
    assert a == b
    assert "www.custom.com" in c.execute("SELECT alias_hosts FROM publications WHERE id=?", (a,)).fetchone()[0]


def test_upsert_post_folds_duplicate_substack_post_id():
    c = _conn()
    a = db.upsert_publication(c, "sub.substack.com", None, confirmed=True)
    b = db.upsert_publication(c, "www.custom.com", None, {"substack_id": 9}, confirmed=True)
    full = db.upsert_post(c, b, "slug", None, {"substack_post_id": 42, "metadata_source": "search", "entry_round": 0, "title": "Full"})
    stub = db.upsert_post(c, a, "slug", None, {"metadata_source": "stub", "entry_round": 1})
    db.add_discovery(c, "post", stub, "coupling", None)
    survivor = db.upsert_post(c, a, "slug", None, {"substack_post_id": 42, "metadata_source": "post", "wordcount": 5})
    assert survivor == full
    assert c.execute("SELECT COUNT(*) FROM posts").fetchone()[0] == 1
    assert c.execute("SELECT COUNT(*) FROM discovery WHERE entity_id=?", (full,)).fetchone()[0] == 1
    assert c.execute("SELECT entry_round FROM posts WHERE id=?", (full,)).fetchone()[0] == 0


def test_merge_publications_moves_posts_and_records_alias():
    c = _conn()
    a = db.upsert_publication(c, "sub.substack.com", None, confirmed=True)
    b = db.upsert_publication(c, "www.custom.com", None, {"substack_id": 9}, confirmed=True)
    db.upsert_post(c, a, "only-here", None, {"metadata_source": "stub", "entry_round": 1})
    db.upsert_post(c, a, "both", None, {"metadata_source": "stub", "entry_round": 1})
    db.upsert_post(c, b, "both", None, {"substack_post_id": 1, "metadata_source": "search", "entry_round": 0})
    db.merge_publications(c, b, a)
    assert c.execute("SELECT COUNT(*) FROM publications").fetchone()[0] == 1
    assert c.execute("SELECT COUNT(*) FROM posts WHERE publication_id=?", (b,)).fetchone()[0] == 2
    assert "sub.substack.com" in c.execute("SELECT alias_hosts FROM publications WHERE id=?", (b,)).fetchone()[0]


def test_resolve_merge_path_by_substack_id_only(monkeypatch):
    """A host whose homepage reports a substack_id already held by another row must merge, not crash."""
    import json as _json
    from mcreview import discover, substack

    class FakeCtx:
        def __init__(self):
            self.conn = _conn()
            self.counts = {}
            self.client = None
        def bump(self, k, n=1): self.counts[k] = self.counts.get(k, 0) + n
        def commit(self): self.conn.commit()
        def store_raw(self, r, ext="json"): return "ref"

    ctx = FakeCtx()
    a = db.upsert_publication(ctx.conn, "www.custom.com", None, {"substack_id": 5}, confirmed=True)
    b = db.upsert_publication(ctx.conn, "www.custom.com.", None)  # distinct host string, unresolved, has a post
    db.upsert_post(ctx.conn, b, "s", None, {"metadata_source": "stub", "entry_round": 1})

    class R:  # minimal Response stand-in
        ok = True; status = 200; content = b""; error = None
    pub = {"id": 5, "subdomain": "custom", "custom_domain": "www.custom.com.", "name": "N"}
    monkeypatch.setattr(substack, "fetch_homepage_pub", lambda client, host: (R(), pub))
    discover.resolve(ctx)
    assert ctx.conn.execute("SELECT COUNT(*) FROM publications").fetchone()[0] == 1
    assert ctx.counts.get("resolve_merged") == 1
