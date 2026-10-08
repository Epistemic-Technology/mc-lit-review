"""SQLite schema and small data-access helpers.

Design notes:
- `publications.host` is the natural key (lowercase host of the canonical URL).
  `substack_id` is filled once the publication has been resolved and is also unique.
- `posts` are unique per (publication_id, slug); `substack_post_id` is unique when known.
- `discovery` records every way an entity entered the corpus (provenance). One row per way.
- Raw responses are referenced by `*_ref` columns pointing into the RawStore.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY,
  stage TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  config_hash TEXT NOT NULL,
  git_sha TEXT,
  args_json TEXT,
  counts_json TEXT,
  status TEXT
);

CREATE TABLE IF NOT EXISTS queries (
  id INTEGER PRIMARY KEY,
  facet TEXT NOT NULL,
  term TEXT NOT NULL,
  variant TEXT NOT NULL,        -- site_quoted | site_plain | open_quoted | substack_posts | substack_pubs
  backend TEXT NOT NULL,        -- brave | substack
  text TEXT NOT NULL,           -- the literal query string sent
  UNIQUE(backend, variant, term)
);

CREATE TABLE IF NOT EXISTS publications (
  id INTEGER PRIMARY KEY,
  host TEXT NOT NULL UNIQUE,
  substack_id INTEGER UNIQUE,
  subdomain TEXT,
  custom_domain TEXT,
  name TEXT,
  hero_text TEXT,
  author_name TEXT,
  author_handle TEXT,
  author_id INTEGER,
  language TEXT,
  type TEXT,
  created_at_substack TEXT,
  first_post_date TEXT,
  free_subscriber_magnitude INTEGER,
  alias_hosts TEXT,             -- JSON list of other hosts that resolved to this publication
  is_substack INTEGER,          -- NULL = unresolved, 1 = confirmed (via Substack API or homepage), 0 = not Substack
  resolved_at TEXT,
  resolve_error TEXT,
  harvested_at TEXT,            -- optional archive-metadata context stage
  harvest_pages INTEGER,
  harvest_posts_in_window INTEGER,
  harvest_error TEXT,
  first_seen_run INTEGER REFERENCES runs(id),
  raw_ref TEXT
);

CREATE TABLE IF NOT EXISTS authors (
  id INTEGER PRIMARY KEY,
  substack_user_id INTEGER UNIQUE,
  handle TEXT,
  name TEXT,
  bio TEXT,
  profile_fetched_at TEXT,
  raw_ref TEXT
);
CREATE INDEX IF NOT EXISTS authors_handle ON authors(handle);

CREATE TABLE IF NOT EXISTS publication_authors (
  publication_id INTEGER NOT NULL REFERENCES publications(id),
  author_id INTEGER NOT NULL REFERENCES authors(id),
  role TEXT,
  PRIMARY KEY (publication_id, author_id)
);

CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY,
  publication_id INTEGER NOT NULL REFERENCES publications(id),
  substack_post_id INTEGER UNIQUE,
  slug TEXT NOT NULL,
  canonical_url TEXT,
  title TEXT,
  subtitle TEXT,
  description TEXT,
  post_date TEXT,
  type TEXT,
  audience TEXT,
  is_paywalled INTEGER,
  wordcount INTEGER,
  language TEXT,
  section_name TEXT,
  reaction_count INTEGER,
  comment_count INTEGER,
  restack_count INTEGER,
  cover_image TEXT,
  is_ai_generated_text INTEGER,   -- Substack's own flag; only present in authenticated search results
  truncated_body_text TEXT,
  metadata_source TEXT,           -- archive | search | post | stub
  metadata_fetched_at TEXT,
  raw_meta_ref TEXT,
  entry_round INTEGER,            -- 0 = phase-1 lexical hit, n>=1 = citation round; NULL = context only (not in corpus)
  source_eligible INTEGER,        -- 1 = may contribute references to later rounds (see settings.citation.source_gating)
  refs_extracted_at TEXT,
  body_status TEXT,               -- NULL | ok | paywalled | empty | not_found | error | pre_cutoff
  body_fetched_at TEXT,
  body_html_ref TEXT,
  body_text TEXT,
  body_error TEXT,
  first_seen_run INTEGER REFERENCES runs(id),
  UNIQUE(publication_id, slug)
);
CREATE INDEX IF NOT EXISTS posts_date ON posts(post_date);
CREATE INDEX IF NOT EXISTS posts_body_status ON posts(body_status);

CREATE TABLE IF NOT EXISTS post_bylines (
  post_id INTEGER NOT NULL REFERENCES posts(id),
  author_id INTEGER NOT NULL REFERENCES authors(id),
  PRIMARY KEY (post_id, author_id)
);

CREATE TABLE IF NOT EXISTS post_tags (
  post_id INTEGER NOT NULL REFERENCES posts(id),
  tag TEXT NOT NULL,
  PRIMARY KEY (post_id, tag)
);

CREATE TABLE IF NOT EXISTS refs (
  -- Normalised cited works. One row per distinct target; see refs.py for normalisation rules.
  id INTEGER PRIMARY KEY,
  url_norm TEXT NOT NULL UNIQUE,
  kind TEXT NOT NULL,             -- substack_post | arxiv | doi | wikipedia | book | web | homepage
  identifier TEXT,                -- arxiv:<id> | doi:<doi> | asin:<asin> | wiki:<lang>:<title> | <host>/p/<slug>
  domain TEXT,
  title TEXT,
  title_source TEXT,              -- post | arxiv_api | doi_csl | page | wikipedia
  title_fetched_at TEXT,
  title_error TEXT,
  citing_posts INTEGER NOT NULL DEFAULT 0,
  citing_pubs INTEGER NOT NULL DEFAULT 0,   -- distinct publications among the citing posts
  eligible INTEGER,               -- 1 = may be used as a coupling target
  block_reason TEXT,
  target_publication_id INTEGER REFERENCES publications(id),
  target_post_id INTEGER REFERENCES posts(id),
  backward_round INTEGER,         -- round in which the cited Substack post was added to the corpus
  searched_round INTEGER,         -- round in which this reference was used as a coupling query
  first_seen_run INTEGER REFERENCES runs(id)
);
CREATE INDEX IF NOT EXISTS refs_kind ON refs(kind);
CREATE INDEX IF NOT EXISTS refs_citing ON refs(citing_posts);

CREATE TABLE IF NOT EXISTS post_refs (
  post_id INTEGER NOT NULL REFERENCES posts(id),
  ref_id INTEGER NOT NULL REFERENCES refs(id),
  url TEXT,                       -- the link as it appeared
  anchor_text TEXT,
  PRIMARY KEY (post_id, ref_id)
);
CREATE INDEX IF NOT EXISTS post_refs_ref ON post_refs(ref_id);

CREATE TABLE IF NOT EXISTS discovery (
  id INTEGER PRIMARY KEY,
  entity_type TEXT NOT NULL,      -- publication | post
  entity_id INTEGER NOT NULL,
  source TEXT NOT NULL,           -- brave | substack_posts | substack_pubs | cited_by | coupling | archive_context
  query_id INTEGER REFERENCES queries(id),
  rank INTEGER,
  page INTEGER,
  hop_depth INTEGER,
  parent_entity_type TEXT,
  parent_entity_id INTEGER,
  run_id INTEGER REFERENCES runs(id),
  seen_at TEXT NOT NULL,
  detail TEXT
);
CREATE INDEX IF NOT EXISTS discovery_entity ON discovery(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS discovery_source ON discovery(source);

CREATE TABLE IF NOT EXISTS search_results (
  -- One row per (query, result) so search channels can be re-analysed and diffed between runs.
  id INTEGER PRIMARY KEY,
  query_id INTEGER NOT NULL REFERENCES queries(id),
  run_id INTEGER REFERENCES runs(id),
  page INTEGER,
  rank INTEGER,
  url TEXT,
  title TEXT,
  snippet TEXT,
  publication_id INTEGER REFERENCES publications(id),
  post_id INTEGER REFERENCES posts(id),
  raw_ref TEXT
);
CREATE INDEX IF NOT EXISTS search_results_query ON search_results(query_id);

CREATE TABLE IF NOT EXISTS http_cache (
  -- Exact-URL response cache for paid/quota-limited endpoints (Brave). Body lives in the raw store.
  url TEXT PRIMARY KEY,
  status INTEGER NOT NULL,
  raw_ref TEXT NOT NULL,
  fetched_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fetch_log (
  id INTEGER PRIMARY KEY,
  run_id INTEGER,
  url TEXT NOT NULL,
  status INTEGER,
  elapsed_ms INTEGER,
  attempts INTEGER,
  error TEXT,
  fetched_at TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(
  title, subtitle, body_text, content='posts', content_rowid='id'
);
CREATE TRIGGER IF NOT EXISTS posts_ai AFTER INSERT ON posts BEGIN
  INSERT INTO posts_fts(rowid, title, subtitle, body_text) VALUES (new.id, new.title, new.subtitle, new.body_text);
END;
CREATE TRIGGER IF NOT EXISTS posts_ad AFTER DELETE ON posts BEGIN
  INSERT INTO posts_fts(posts_fts, rowid, title, subtitle, body_text) VALUES ('delete', old.id, old.title, old.subtitle, old.body_text);
END;
CREATE TRIGGER IF NOT EXISTS posts_au AFTER UPDATE ON posts BEGIN
  INSERT INTO posts_fts(posts_fts, rowid, title, subtitle, body_text) VALUES ('delete', old.id, old.title, old.subtitle, old.body_text);
  INSERT INTO posts_fts(rowid, title, subtitle, body_text) VALUES (new.id, new.title, new.subtitle, new.body_text);
END;

-- ---------------------------------------------------------------- analysis stages (docs/plan.md)

CREATE TABLE IF NOT EXISTS analysis_subset (
  -- Posts in the analysis population (stage 0). Rebuilt by `mcreview subset`; one row per included post.
  post_id INTEGER PRIMARY KEY REFERENCES posts(id),
  run_id INTEGER REFERENCES runs(id),
  flags TEXT                      -- JSON list: paywalled | podcast | ...
);

CREATE TABLE IF NOT EXISTS code_runs (
  -- One row per engine invocation over a set of items (stage 3/4).
  id INTEGER PRIMARY KEY,
  run_id INTEGER REFERENCES runs(id),
  engine TEXT NOT NULL,           -- jev | claude
  model TEXT NOT NULL,            -- pinned model id as sent
  codebook_version TEXT NOT NULL,
  target TEXT NOT NULL,           -- posts | publications
  config_json TEXT,
  batch_id TEXT,                  -- Anthropic Message Batch id when submitted asynchronously
  started_at TEXT NOT NULL,
  finished_at TEXT,
  n_items INTEGER DEFAULT 0,
  input_tokens INTEGER DEFAULT 0,
  output_tokens INTEGER DEFAULT 0,
  cost_usd REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS codes (
  -- One row per (item, construct, repeat) produced by an engine. Raw responses are in the raw store.
  id INTEGER PRIMARY KEY,
  code_run_id INTEGER NOT NULL REFERENCES code_runs(id),
  entity_type TEXT NOT NULL,      -- post | publication
  entity_id INTEGER NOT NULL,
  construct TEXT NOT NULL,
  repeat_no INTEGER NOT NULL DEFAULT 0,
  value TEXT,                     -- chosen option, or 'true'/'false' for noul
  probability REAL,               -- probability of `value` (noul: p(true))
  confidence REAL,                -- engine-reported confidence (jev) or NULL
  distribution_json TEXT,         -- full option distribution (choice)
  evidence TEXT,                  -- supporting quote (claude)
  raw_ref TEXT,
  coded_at TEXT NOT NULL,
  UNIQUE(code_run_id, entity_type, entity_id, construct, repeat_no)
);
CREATE INDEX IF NOT EXISTS codes_entity ON codes(entity_type, entity_id, construct);

CREATE TABLE IF NOT EXISTS code_final (
  -- Materialised coder-of-record value per item x construct after the cascade (see code.materialise).
  entity_type TEXT NOT NULL,
  entity_id INTEGER NOT NULL,
  construct TEXT NOT NULL,
  value TEXT,
  probability REAL,
  source TEXT NOT NULL,           -- jev | claude | human
  codebook_version TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (entity_type, entity_id, construct)
);

CREATE TABLE IF NOT EXISTS gold_samples (
  -- Frozen random samples for human verification (stage 2). Drawn once per name.
  id INTEGER PRIMARY KEY,
  sample_name TEXT NOT NULL,      -- relevance | stance | publications
  entity_type TEXT NOT NULL,
  entity_id INTEGER NOT NULL,
  stratum TEXT,
  position INTEGER,
  sampled_at TEXT NOT NULL,
  run_id INTEGER REFERENCES runs(id),
  codebook_version TEXT NOT NULL,
  UNIQUE(sample_name, entity_type, entity_id)
);

CREATE TABLE IF NOT EXISTS embeddings (
  -- Stage 5: one vector per post for a given model (float32 little-endian blob).
  post_id INTEGER NOT NULL REFERENCES posts(id),
  model TEXT NOT NULL,
  dim INTEGER NOT NULL,
  n_chunks INTEGER,
  vector BLOB NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (post_id, model)
);

CREATE TABLE IF NOT EXISTS topics (
  -- Stage 5: HDBSCAN clusters over the embeddings; label filled later (LLM-suggested, hand-checked).
  run_id INTEGER REFERENCES runs(id),
  cluster INTEGER NOT NULL,
  size INTEGER NOT NULL,          -- all posts assigned (core + peripheral)
  core_size INTEGER,              -- HDBSCAN core members
  top_terms TEXT,                 -- JSON list, c-TF-IDF
  exemplar_post_ids TEXT,         -- JSON list of posts nearest the centroid
  label TEXT,
  description TEXT,
  PRIMARY KEY (cluster)
);

CREATE TABLE IF NOT EXISTS post_layout (
  -- Stage 5: 2-D UMAP position and cluster per post (topic map).
  post_id INTEGER PRIMARY KEY REFERENCES posts(id),
  x REAL NOT NULL, y REAL NOT NULL,
  cluster INTEGER NOT NULL,
  cluster_prob REAL,
  run_id INTEGER REFERENCES runs(id)
);

CREATE TABLE IF NOT EXISTS network_nodes (
  -- Stage 5: citation network over corpus posts (edges = links to other corpus posts, intra-publication dropped).
  post_id INTEGER PRIMARY KEY REFERENCES posts(id),
  community INTEGER,              -- Leiden
  in_posts INTEGER NOT NULL DEFAULT 0,
  in_pubs INTEGER NOT NULL DEFAULT 0,   -- distinct citing publications
  out_posts INTEGER NOT NULL DEFAULT 0,
  pagerank REAL, betweenness REAL,
  x REAL, y REAL,
  run_id INTEGER REFERENCES runs(id)
);

CREATE TABLE IF NOT EXISTS network_edges (
  src_post_id INTEGER NOT NULL REFERENCES posts(id),
  dst_post_id INTEGER NOT NULL REFERENCES posts(id),
  PRIMARY KEY (src_post_id, dst_post_id)
);

CREATE TABLE IF NOT EXISTS pub_network (
  -- Stage 5: publication-level aggregation of the citation network with a disparity-filter backbone.
  publication_id INTEGER PRIMARY KEY REFERENCES publications(id),
  community INTEGER,
  in_pubs INTEGER NOT NULL DEFAULT 0,
  out_pubs INTEGER NOT NULL DEFAULT 0,
  in_posts INTEGER NOT NULL DEFAULT 0,
  pagerank REAL, betweenness REAL,
  x REAL, y REAL,
  run_id INTEGER REFERENCES runs(id)
);

CREATE TABLE IF NOT EXISTS pub_edges (
  src_publication_id INTEGER NOT NULL REFERENCES publications(id),
  dst_publication_id INTEGER NOT NULL REFERENCES publications(id),
  weight INTEGER NOT NULL,        -- number of post-level links
  backbone INTEGER NOT NULL DEFAULT 0,  -- 1 = survives the disparity filter
  PRIMARY KEY (src_publication_id, dst_publication_id)
);

CREATE TABLE IF NOT EXISTS gold_codes (
  -- Human decisions: for each sampled item x construct, the human's value and how it was reached.
  id INTEGER PRIMARY KEY,
  sample_id INTEGER NOT NULL REFERENCES gold_samples(id),
  construct TEXT NOT NULL,
  value TEXT,
  decision TEXT,                  -- accept | reject | fix (relative to the shown engine code) | coded (from scratch)
  shown_value TEXT,               -- engine value shown to the human, if any
  shown_evidence TEXT,
  note TEXT,
  seconds REAL,
  coded_at TEXT NOT NULL,
  codebook_version TEXT NOT NULL,
  UNIQUE(sample_id, construct)
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=60)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    _migrate(conn)
    return conn


# Columns added after the first release: (table, column, DDL type/default). Applied if missing.
MIGRATIONS: tuple[tuple[str, str, str], ...] = (
    ("refs", "citing_pubs", "INTEGER NOT NULL DEFAULT 0"),
    ("posts", "source_eligible", "INTEGER"),
    ("topics", "core_size", "INTEGER"),
    ("topics", "description", "TEXT"),
)


def _migrate(conn: sqlite3.Connection) -> None:
    for table, col, ddl in MIGRATIONS:
        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        if col not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
    conn.commit()


# ---------------------------------------------------------------- runs

def start_run(conn: sqlite3.Connection, stage: str, config_hash: str, git_sha: str | None, args: dict) -> int:
    cur = conn.execute(
        "INSERT INTO runs(stage, started_at, config_hash, git_sha, args_json, status) VALUES (?,?,?,?,?,?)",
        (stage, now(), config_hash, git_sha, json.dumps(args, default=str), "running"),
    )
    conn.commit()
    return int(cur.lastrowid)


def finish_run(conn: sqlite3.Connection, run_id: int, counts: dict, status: str = "ok") -> None:
    conn.execute(
        "UPDATE runs SET finished_at=?, counts_json=?, status=? WHERE id=?",
        (now(), json.dumps(counts, default=str), status, run_id),
    )
    conn.commit()


# ---------------------------------------------------------------- queries

def get_or_create_query(conn: sqlite3.Connection, backend: str, variant: str, facet: str, term: str, text: str) -> int:
    row = conn.execute(
        "SELECT id FROM queries WHERE backend=? AND variant=? AND term=?", (backend, variant, term)
    ).fetchone()
    if row:
        return int(row["id"])
    cur = conn.execute(
        "INSERT INTO queries(facet, term, variant, backend, text) VALUES (?,?,?,?,?)",
        (facet, term, variant, backend, text),
    )
    return int(cur.lastrowid)


# ---------------------------------------------------------------- publications

PUB_FIELDS = (
    "substack_id", "subdomain", "custom_domain", "name", "hero_text", "author_name", "author_handle",
    "author_id", "language", "type", "created_at_substack", "first_post_date", "free_subscriber_magnitude",
)


def get_publication_by_host(conn: sqlite3.Connection, host: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM publications WHERE host=?", (host,)).fetchone()


def get_publication_by_substack_id(conn: sqlite3.Connection, sid: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM publications WHERE substack_id=?", (sid,)).fetchone()


def upsert_publication(
    conn: sqlite3.Connection,
    host: str,
    run_id: int | None,
    fields: dict[str, Any] | None = None,
    confirmed: bool = False,
) -> int:
    """Insert or update a publication keyed by host (or by substack_id when the host differs).

    Returns the publication id. Existing non-null values are kept unless the new value is non-null.
    `confirmed` marks the publication as a known Substack site (its data came from Substack's API).
    """
    fields = {k: v for k, v in (fields or {}).items() if k in PUB_FIELDS and v is not None}
    row = get_publication_by_host(conn, host)
    if row is None and fields.get("substack_id") is not None:
        row = get_publication_by_substack_id(conn, int(fields["substack_id"]))
        if row is not None:
            # Same publication known under another host: record alias, keep canonical row.
            aliases = set(json.loads(row["alias_hosts"] or "[]"))
            if host != row["host"]:
                aliases.add(host)
            conn.execute("UPDATE publications SET alias_hosts=? WHERE id=?", (json.dumps(sorted(aliases)), row["id"]))
    if row is None:
        cols = ["host", "first_seen_run"] + list(fields)
        vals = [host, run_id] + [fields[k] for k in fields]
        if confirmed:
            cols.append("is_substack")
            vals.append(1)
        cur = conn.execute(
            f"INSERT INTO publications({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", vals
        )
        return int(cur.lastrowid)
    pid = int(row["id"])
    sets, vals = [], []
    for k, v in fields.items():
        sets.append(f"{k}=COALESCE(?, {k})")
        vals.append(v)
    if confirmed:
        sets.append("is_substack=COALESCE(is_substack, 1)")
    if sets:
        conn.execute(f"UPDATE publications SET {','.join(sets)} WHERE id=?", vals + [pid])
    return pid


# ---------------------------------------------------------------- posts

POST_FIELDS = (
    "substack_post_id", "canonical_url", "title", "subtitle", "description", "post_date", "type", "audience",
    "is_paywalled", "wordcount", "language", "section_name", "reaction_count", "comment_count", "restack_count",
    "cover_image", "is_ai_generated_text", "truncated_body_text", "metadata_source", "metadata_fetched_at",
    "raw_meta_ref", "entry_round",
)


def upsert_post(conn: sqlite3.Connection, publication_id: int, slug: str, run_id: int | None, fields: dict[str, Any]) -> int:
    fields = {k: v for k, v in fields.items() if k in POST_FIELDS and v is not None}
    row = conn.execute(
        "SELECT id FROM posts WHERE publication_id=? AND slug=?", (publication_id, slug)
    ).fetchone()
    if row is None and fields.get("substack_post_id") is not None:
        row = conn.execute("SELECT id FROM posts WHERE substack_post_id=?", (fields["substack_post_id"],)).fetchone()
    if row is None:
        cols = ["publication_id", "slug", "first_seen_run"] + list(fields)
        vals = [publication_id, slug, run_id] + [fields[k] for k in fields]
        cur = conn.execute(f"INSERT INTO posts({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", vals)
        return int(cur.lastrowid)
    pid = int(row["id"])
    if fields.get("substack_post_id") is not None:
        other = conn.execute("SELECT id FROM posts WHERE substack_post_id=? AND id<>?", (fields["substack_post_id"], pid)).fetchone()
        if other:
            # Same Substack post already known under another slug/publication row (e.g. subdomain vs custom
            # domain). Keep the row that already carries the id; fold this one into it.
            merge_posts(conn, int(other["id"]), pid)
            pid = int(other["id"])
    if fields:
        # Real metadata (archive/search) overrides stub metadata; otherwise keep existing non-null values.
        overriding = fields.get("metadata_source") in ("archive", "search", "post")
        # entry_round is first-wins (the earliest route into the corpus): COALESCE(existing, new).
        # Everything else is new-wins when the new value is non-null, or unconditional for authoritative sources.
        sets = []
        for k in fields:
            if k == "entry_round":
                sets.append("entry_round=COALESCE(entry_round, ?)")
            elif overriding:
                sets.append(f"{k}=?")
            else:
                sets.append(f"{k}=COALESCE(?, {k})")
        conn.execute(f"UPDATE posts SET {','.join(sets)} WHERE id=?", [fields[k] for k in fields] + [pid])
    return pid


def merge_posts(conn: sqlite3.Connection, keep_id: int, drop_id: int) -> None:
    """Fold post `drop_id` into `keep_id`: provenance, references, bylines and tags move; entry_round is the
    earliest of the two; body/metadata of `keep_id` win where present."""
    if keep_id == drop_id:
        return
    conn.execute("UPDATE discovery SET entity_id=? WHERE entity_type='post' AND entity_id=?", (keep_id, drop_id))
    conn.execute("UPDATE discovery SET parent_entity_id=? WHERE parent_entity_type='post' AND parent_entity_id=?", (keep_id, drop_id))
    conn.execute("UPDATE search_results SET post_id=? WHERE post_id=?", (keep_id, drop_id))
    conn.execute("UPDATE refs SET target_post_id=? WHERE target_post_id=?", (keep_id, drop_id))
    for table in ("post_refs", "post_bylines", "post_tags"):
        conn.execute(f"INSERT OR IGNORE INTO {table} SELECT ?, {', '.join(c for c in _cols(conn, table) if c != 'post_id')} FROM {table} WHERE post_id=?", (keep_id, drop_id))
        conn.execute(f"DELETE FROM {table} WHERE post_id=?", (drop_id,))
    drop = conn.execute("SELECT * FROM posts WHERE id=?", (drop_id,)).fetchone()
    keep = conn.execute("SELECT * FROM posts WHERE id=?", (keep_id,)).fetchone()
    rounds = [r for r in (keep["entry_round"], drop["entry_round"]) if r is not None]
    fill = {k: drop[k] for k in drop.keys() if k not in ("id", "publication_id", "slug", "substack_post_id", "entry_round") and keep[k] is None and drop[k] is not None}
    sets = ", ".join(f"{k}=?" for k in fill) + (", " if fill else "") + "entry_round=?"
    conn.execute(f"UPDATE posts SET {sets} WHERE id=?", list(fill.values()) + [min(rounds) if rounds else None, keep_id])
    conn.execute("DELETE FROM posts WHERE id=?", (drop_id,))


def _cols(conn: sqlite3.Connection, table: str) -> list[str]:
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]


def merge_publications(conn: sqlite3.Connection, keep_id: int, drop_id: int) -> None:
    """Fold publication `drop_id` into `keep_id` (same Substack publication under two hosts)."""
    if keep_id == drop_id:
        return
    for row in conn.execute("SELECT id, slug FROM posts WHERE publication_id=?", (drop_id,)).fetchall():
        dup = conn.execute("SELECT id FROM posts WHERE publication_id=? AND slug=?", (keep_id, row["slug"])).fetchone()
        if dup:
            merge_posts(conn, int(dup["id"]), int(row["id"]))
        else:
            conn.execute("UPDATE posts SET publication_id=? WHERE id=?", (keep_id, row["id"]))
    conn.execute("UPDATE discovery SET entity_id=? WHERE entity_type='publication' AND entity_id=?", (keep_id, drop_id))
    conn.execute("UPDATE discovery SET parent_entity_id=? WHERE parent_entity_type='publication' AND parent_entity_id=?", (keep_id, drop_id))
    conn.execute("UPDATE search_results SET publication_id=? WHERE publication_id=?", (keep_id, drop_id))
    conn.execute("UPDATE refs SET target_publication_id=? WHERE target_publication_id=?", (keep_id, drop_id))
    conn.execute("INSERT OR IGNORE INTO publication_authors SELECT ?, author_id, role FROM publication_authors WHERE publication_id=?", (keep_id, drop_id))
    conn.execute("DELETE FROM publication_authors WHERE publication_id=?", (drop_id,))
    keep = conn.execute("SELECT * FROM publications WHERE id=?", (keep_id,)).fetchone()
    drop = conn.execute("SELECT * FROM publications WHERE id=?", (drop_id,)).fetchone()
    aliases = set(json.loads(keep["alias_hosts"] or "[]")) | set(json.loads(drop["alias_hosts"] or "[]")) | {drop["host"]}
    aliases.discard(keep["host"])
    fill = {k: drop[k] for k in PUB_FIELDS if keep[k] is None and drop[k] is not None}
    sets = ", ".join(f"{k}=?" for k in fill) + (", " if fill else "") + "alias_hosts=?"
    conn.execute("DELETE FROM publications WHERE id=?", (drop_id,))
    conn.execute(f"UPDATE publications SET {sets} WHERE id=?", list(fill.values()) + [json.dumps(sorted(aliases)), keep_id])


# ---------------------------------------------------------------- authors

def upsert_author(conn: sqlite3.Connection, substack_user_id: int | None, handle: str | None, name: str | None, bio: str | None = None) -> int | None:
    if substack_user_id is None and not handle:
        return None
    row = None
    if substack_user_id is not None:
        row = conn.execute("SELECT id FROM authors WHERE substack_user_id=?", (substack_user_id,)).fetchone()
    if row is None and handle:
        row = conn.execute("SELECT id FROM authors WHERE handle=? AND substack_user_id IS NULL", (handle,)).fetchone()
    if row is None:
        cur = conn.execute(
            "INSERT INTO authors(substack_user_id, handle, name, bio) VALUES (?,?,?,?)",
            (substack_user_id, handle, name, bio),
        )
        return int(cur.lastrowid)
    conn.execute(
        "UPDATE authors SET substack_user_id=COALESCE(?, substack_user_id), handle=COALESCE(?, handle), "
        "name=COALESCE(?, name), bio=COALESCE(?, bio) WHERE id=?",
        (substack_user_id, handle, name, bio, row["id"]),
    )
    return int(row["id"])


# ---------------------------------------------------------------- provenance

def add_discovery(
    conn: sqlite3.Connection,
    entity_type: str,
    entity_id: int,
    source: str,
    run_id: int | None,
    query_id: int | None = None,
    rank: int | None = None,
    page: int | None = None,
    hop_depth: int | None = None,
    parent: tuple[str, int] | None = None,
    detail: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO discovery(entity_type, entity_id, source, query_id, rank, page, hop_depth, "
        "parent_entity_type, parent_entity_id, run_id, seen_at, detail) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (entity_type, entity_id, source, query_id, rank, page, hop_depth,
         parent[0] if parent else None, parent[1] if parent else None, run_id, now(), detail),
    )

