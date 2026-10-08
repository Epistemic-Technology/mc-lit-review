"""Stage 5 pure logic: chunking for embeddings, token filtering, edge construction rules."""
import sqlite3
from types import SimpleNamespace

from mcreview import db
from mcreview.embeddings import _tokens, chunks_for
from mcreview.network import _edges


def test_chunks_prepend_title_and_cap_count():
    ch = chunks_for("Title", "Sub", "x" * 5000, chunk_chars=2000, max_chunks=2)
    assert len(ch) == 2 and ch[0].startswith("Title Sub")
    assert chunks_for("", "", "", 2000, 3) == ["(empty)"]


def test_tokens_drop_stopwords_and_short():
    toks = _tokens("The Chinese room argument shows that LLMs do not understand; AI is a model.")
    assert "chinese" in toks and "room" in toks and "argument" in toks
    assert "the" not in toks and "llms" not in toks and "ai" not in toks and "do" not in toks


def _ctx_with_edges():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(db.SCHEMA)
    a = db.upsert_publication(conn, "a.substack.com", None, confirmed=True)
    b = db.upsert_publication(conn, "b.substack.com", None, confirmed=True)
    p1 = db.upsert_post(conn, a, "p1", None, {"metadata_source": "stub", "entry_round": 0})
    p2 = db.upsert_post(conn, a, "p2", None, {"metadata_source": "stub", "entry_round": 0})
    p3 = db.upsert_post(conn, b, "p3", None, {"metadata_source": "stub", "entry_round": 1})
    p4 = db.upsert_post(conn, b, "p4", None, {"metadata_source": "stub", "entry_round": 1})
    n = [0]

    def ref(target):   # one refs row per link (url_norm is unique), all pointing at `target`
        n[0] += 1
        cur = conn.execute("INSERT INTO refs(url_norm, kind, target_post_id) VALUES (?,?,?)", (f"https://x/{target}?v={n[0]}", "substack_post", target))
        return cur.lastrowid
    conn.execute("INSERT INTO post_refs(post_id, ref_id) VALUES (?,?)", (p1, ref(p3)))   # cross-publication: kept
    conn.execute("INSERT INTO post_refs(post_id, ref_id) VALUES (?,?)", (p1, ref(p2)))   # same publication: dropped when drop_intra
    conn.execute("INSERT INTO post_refs(post_id, ref_id) VALUES (?,?)", (p3, ref(p1)))   # reciprocal cross: kept
    conn.execute("INSERT INTO post_refs(post_id, ref_id) VALUES (?,?)", (p4, ref(p1)))   # p4 outside the population: dropped
    conn.execute("INSERT INTO post_refs(post_id, ref_id) VALUES (?,?)", (p1, ref(p1)))   # self-link: dropped
    return SimpleNamespace(conn=conn), (p1, p2, p3, p4)


def test_edges_respect_population_intra_and_self_rules():
    ctx, (p1, p2, p3, p4) = _ctx_with_edges()
    assert _edges(ctx, {p1, p2, p3}, drop_intra=True) == sorted([(p1, p3), (p3, p1)])
    assert _edges(ctx, {p1, p2, p3}, drop_intra=False) == sorted([(p1, p2), (p1, p3), (p3, p1)])
    assert (p4, p1) in _edges(ctx, {p1, p2, p3, p4}, drop_intra=True)
