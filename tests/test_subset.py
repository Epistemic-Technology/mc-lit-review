"""Stage 0 rules on an in-memory corpus."""
import json
import sqlite3
from types import SimpleNamespace

from mcreview import db, subset


class FakeCtx:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(db.SCHEMA)
        self.run_id = db.start_run(self.conn, "test", "h", None, {})
        self.counts = {}
        self.settings = SimpleNamespace(
            analysis={"subset": {"languages": ["en"], "min_date": "2024-01-01", "body_status": ["ok"], "min_body_chars": 10}},
            exclusions={"hosts": [{"host": "spam.com", "reason": "test"}]},
        )

    def commit(self):
        self.conn.commit()


def _post(c, pub, slug, **f):
    fields = {"metadata_source": "stub", "entry_round": 0, "post_date": "2025-01-01", "language": "en", "body_status": "ok", "body_text": "x" * 50}
    fields.update(f)
    body = {k: fields.pop(k) for k in ("body_status", "body_text")}   # set by the body stage, not the metadata upsert
    pid = db.upsert_post(c, pub, slug, None, fields)
    c.execute("UPDATE posts SET body_status=?, body_text=?, entry_round=? WHERE id=?", (body["body_status"], body["body_text"], fields.get("entry_round"), pid))
    return pid


def test_rules_and_counts():
    ctx = FakeCtx()
    c = ctx.conn
    ok = db.upsert_publication(c, "good.substack.com", None, confirmed=True)
    bad = db.upsert_publication(c, "www.spam.com", None, confirmed=True)
    keep = _post(c, ok, "a")
    _post(c, ok, "old", post_date="2023-06-01")
    _post(c, ok, "fr", language="fr")
    _post(c, ok, "paid", body_status="paywalled")
    _post(c, ok, "short", body_text="tiny")
    flagged = _post(c, ok, "pod", type="podcast", audience="only_paid")
    _post(c, bad, "spam")
    _post(c, ok, "ctx", entry_round=None)
    counts = subset.build(ctx)
    assert counts == {"corpus": 7, "after_date": 6, "after_language": 5, "after_body": 4, "after_min_chars": 3, "after_exclusions": 2}
    rows = {r["post_id"]: json.loads(r["flags"]) for r in c.execute("SELECT * FROM analysis_subset")}
    assert set(rows) == {keep, flagged}
    assert rows[flagged] == ["paywalled", "podcast"]
