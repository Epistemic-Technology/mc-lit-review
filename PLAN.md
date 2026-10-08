# Machine Cognition / Machine Consciousness on Substack: Data-Gathering Plan

Status: agreed 2026-09-26, all §6 decisions resolved. Implementation not yet started.

## 1. Goal and principles

Build a wide-net, replicable corpus of Substack **publications**, **authors**, and **posts** that plausibly discuss machine cognition, machine consciousness, AI sentience, digital minds, AI moral status, and adjacent topics. Downstream (out of scope for this plan): classifiers to filter, label, cluster, and analyse.

Principles:

- **Recall over precision at gathering time.** Every filter in the gathering pipeline is loose; tight filtering happens later, on the stored corpus, where it can be re-run.
- **Provenance for everything.** Every publication and post records *how* it entered the corpus (which source, which query or seed, which hop of snowballing, when). This lets us report a PRISMA-style flow diagram and lets anyone re-run the pipeline.
- **Raw before derived.** Store the raw JSON/HTML we fetched, unmodified, alongside the parsed fields. Re-parsing is then possible without re-fetching.
- **Config in the repo, not in heads.** Seed lists, query banks, thresholds, and stop conditions live in version-controlled YAML/JSON files. Each pipeline run writes a manifest (config hash, code version, timestamps, counts).
- **Polite access.** Public endpoints only, ~1 request/second, identified User-Agent, exponential backoff, respect robots.txt, never circumvent paywalls. Paywalled posts are recorded as metadata plus the public preview only.

## 2. What Substack exposes (verified 2026-09-26, anonymous requests)

Per publication (works on `*.substack.com` and custom domains alike):

| Need | Endpoint | Notes |
|---|---|---|
| Full post list | `/api/v1/archive?sort=new&offset=N&limit=20` | Page cap is ~20 (limit=25 returned 23; limit=100 returned 1). Deep offsets work. Returns title, subtitle, description, post_date, audience (`everyone`/`only_paid`), wordcount, language, postTags, reaction_count, comment_count, restacks, publishedBylines, canonical_url, type (newsletter/podcast/video/thread), section, truncated_body_text. **No body.** |
| Post body | `/api/v1/posts/<slug>` | `body_html` for free posts (~48 KB for a 2.7k-word post). Paid posts: body empty, only ~180-char preview. |
| Recommendations (snowball edges) | `/recommendations` (HTML) | Embedded JSON contains `recommendedPublication` objects with subdomain/custom_domain. ~19 for a mid-size pub. |
| All post URLs (cross-check) | `/sitemap.xml` | Useful to verify archive completeness. |
| Recent posts only | `/feed` (RSS) | Last ~8–20 posts. Useful for incremental updates, not for backfill. |
| Publication metadata | `/api/v1/publication` | **403 anonymously.** Use the homepage HTML `_preloads` JSON instead, or the fields embedded in archive results. |

Substack-wide:

| Need | Endpoint | Notes |
|---|---|---|
| Category list | `https://substack.com/api/v1/categories` | philosophy=114, science=134, technology=4, culture=96, education=34, etc. |
| Category leaderboard | `https://substack.com/api/v1/category/public/{id}/all?page=N` | 25 pubs/page, `more` flag for pagination. |
| Author profile | `https://substack.com/api/v1/user/{handle}/public_profile` | Publications the author writes for, bio. |
| Site-wide post search | `https://substack.com/api/v1/post/search?query=<q>&includePlatformResults=true&filter=all&page=N` | **Works anonymously** once the two extra parameters the web app sends are included (without them it returns empty). 20 results/page, `more` flag, deep pagination. Each result carries the same rich post metadata as the archive endpoint, and a parallel `publications` array gives publication metadata including custom_domain. Bursty rate limit: ~15 rapid requests triggered a 429 that cleared within seconds; ~2.5 s spacing was fine. **Recency skew:** paginating "machine consciousness" to 41 pages gave 774 unique posts from 683 publications, every one dated 2026, and `sort=` is ignored. Substack search is therefore a discovery channel for publications and *recent* posts; historical coverage must come from archive harvesting and web search. |
| Site-wide publication search | `https://substack.com/api/v1/publication/search?query=<q>&page=N` | **Needs the session cookie** (empty anonymously). 19 results/page, ~4 pages for "consciousness". Returns full publication objects. |
| Authenticated extras | same post search with cookie | Adds per-post `is_ai_generated_text` / `is_ai_detection_disabled` flags (Substack's own AI-text detector) plus reader-state fields. Worth capturing. |

External:

- **Web search** with `site:substack.com "<term>"` queries. DuckDuckGo HTML endpoint works without a key; Brave Search API / SerpAPI / Bing are more replicable (structured JSON, stable pagination) and cheap at our scale (a few thousand queries).
- **Custom domains** are invisible to `site:substack.com`. Mitigation: (a) also search without the site filter for the most specific terms and detect Substack-hosted pages by markers (`substackcdn.com`, `window._preloads`, working `/api/v1/archive`); (b) snowballing via recommendations and cross-links naturally reaches custom-domain pubs; (c) the category leaderboards expose `custom_domain` directly.

**Client note (2026-09-26):** Cloudflare serves a managed challenge (HTTP 403, `cf-mitigated: challenge`) to Python `httpx` on substack.com and every `*.substack.com` host regardless of headers or HTTP version, while `urllib`, `urllib3`, `requests` and `curl` with identical headers pass. Custom-domain publications are not affected. The pipeline therefore uses `requests`.

## 3. Pipeline design (revised 2026-09-26: two phases, post-centred)

The first design harvested whole publications and snowballed through recommendation networks. It was dropped because
(a) it biases any discourse map toward whichever publications were seeds or early hits, and (b) with ~92 terms it
would have pulled in tens of thousands of publications, i.e. most of Substack. The unit of inclusion is now the
**post**, and a post enters the corpus only through documented evidence: it matched a query, or it is connected by
citation to posts that did.

### Phase 1: lexical search (`discover`)
- Brave web search over the query bank (site-filtered and, for core facets, unfiltered variants).
- Substack post search (anonymous, relevance-ranked, recency-skewed).
- Substack publication search (cookie) records publications as *context only*; it never adds posts.
Posts found here have `entry_round = 0`. Publications are recorded with metadata; nothing is harvested wholesale.

### Bodies (`resolve`, `fetch-bodies`)
Hosts that came from web search are confirmed as Substack sites via their homepage; free post bodies are fetched,
paywalled posts keep the public preview. Posts dated before the cutoff that were reached by citation are kept as
reference targets (`body_status = pre_cutoff`) but are not corpus members.

### Phase 2: citation expansion (`cite-round`, repeated)
Standard citation searching, in bibliometric terms:
1. **References.** Every outbound link in a corpus body is normalised into a cited work (`refs`): arXiv ids,
   DOIs, Wikipedia titles, Amazon ASINs, Substack posts (including `open.substack.com/pub/...` forms), or a cleaned
   URL. Tracking parameters are stripped. `post_refs` is the post-by-reference matrix.
2. **Backward chasing.** Cited Substack posts enter the corpus directly (`cited_by`).
3. **Bibliographic coupling** (Kessler 1963). Every reference cited by at least `min_citing_posts` corpus posts
   becomes a Brave query (identifier for arXiv/DOI, exact title otherwise; titles fetched from the arXiv API, DOI
   content negotiation, or the page). Posts found this way enter as `coupling`, with the shared reference recorded.
4. Rounds repeat until one adds nothing or `max_rounds` is hit. The threshold guarantees convergence; caps on
   targets per round and on backward fetches bound each round.

Generic targets (social media, video, platform and product pages) are excluded from coupling by a domain blocklist,
and web pages without a fetched title of reasonable length are ineligible. All rules live in `config/settings.yaml`.

**Drift control (source gating, 2026-09-27).** Every admitted post stays in the corpus, but a post contributes
references to later rounds only with relevance evidence: it came from phase 1, entered by two or more routes, or its
title/body contains a query term. Wide net for inclusion, no propagation from weak nodes.

**Custom domains.** A `/p/<slug>` link on an unknown host is a candidate Substack post (`maybe_substack_post`),
confirmed or demoted when the host is resolved. This is how custom-domain publications are reached by citation.

**Brave budget.** Responses are cached by exact URL and coupling queries are deduplicated by text. Expected first-run
cost is ~4,000-6,500 API calls (phase 1 ~1,100; coupling ~1.2 calls per target). The free tier (2,000/month) is not
enough; the paid tier costs on the order of $20-30 for the run.

### Optional context (`archive-meta`)
For publications with several corpus posts, archive *metadata* (no bodies) back to the cutoff, so per-publication
output shares can be computed. These posts have `entry_round = NULL` and are never treated as corpus members.

### Validation, not seeds (`check-validation`)
`config/validation.yaml` lists publications we believe belong. It plays no role in discovery. After a run the
command reports which were found, via which channels, and with how many posts. A miss is a recall finding; the
principled response is a new query term, not hand-insertion.

### Reporting (`report`)
Unique-yield per channel and per query term (how many corpus posts only that route found), the round distribution,
and the most-cited coupling references. This turns "how sensitive is the corpus to the query bank" into a measurement.

## 4. Query bank (initial, deliberately broad)

Core: machine consciousness, artificial consciousness, AI consciousness, conscious AI, conscious machines, machine sentience, AI sentience, sentient AI, digital minds, digital sentience, digital consciousness, robot consciousness, LLM consciousness, "is ChatGPT conscious", "is Claude conscious", "do LLMs understand", "does AI understand", "AI feelings", "AI emotions", AI inner life, AI experience, AI qualia, AI phenomenology, AI self-awareness, machine self-awareness.

Moral status / welfare: AI welfare, model welfare, AI moral status, AI moral patienthood, AI rights, robot rights, AI personhood, AI suffering, digital suffering, sentientism.

Cognition: machine cognition, artificial cognition, AI cognition, LLM cognition, machine psychology, AI psychology, "theory of mind" LLM, LLM reasoning, LLM understanding, world models, machine understanding, stochastic parrots, "Chinese room", "Turing test", AI intelligence explosion? (borderline, include), AGI consciousness, superintelligence consciousness, mind uploading, whole brain emulation, substrate independence, computational theory of mind, functionalism AI.

Theory anchors: global workspace AI, integrated information theory AI, higher-order theory AI, predictive processing AI, attention schema AI, hard problem AI, "other minds" AI, panpsychism AI, illusionism AI.

Named anchors (people/events/works): Chalmers, Dennett, Searle, Nagel, Butlin Long report, Birch "Edge of Sentience", Schwitzgebel, Seth, Tononi, Goff, Frankish, Metzinger, Levin, Blake Lemoine LaMDA, Anthropic model welfare, Claude constitution consciousness, "Bing Sydney".

Each term is run as a quoted phrase and, for multiword terms, unquoted. Terms are tagged by facet (core / moral status / cognition / theory / anchor) so we can report which facets recruited which posts.

## 5. Storage: SQLite plus raw files

SQLite is the right default for this: single portable file that can be committed or archived with the paper, zero infrastructure, transactional so the crawler can resume after a crash, FTS5 for full-text keyword queries across the corpus, and every analysis tool (pandas, DuckDB, R) reads it directly. DuckDB is better for heavy analytics but worse as a crawler's write store; the plan is SQLite for gathering and DuckDB/pandas over the SQLite file (or Parquet exports) for analysis. Postgres is unnecessary at this scale (<1M rows).

Raw responses go in a content-addressed directory `data/raw/<sha256[:2]>/<sha256>.json.gz` referenced from the DB, so the DB stays small (<1 GB) and raw is immutable.

Tables (as implemented in `db.py`):

- `publications` host-keyed, with Substack id, custom domain, aliases, resolution status, optional archive-meta status.
- `authors`, `publication_authors`, `post_bylines`, `post_tags`.
- `posts` unique per (publication, slug); `entry_round` (0 lexical, n citation round, NULL context-only); body status/text/raw ref.
- `refs` normalised cited works with kind, identifier, title, citing count, eligibility, target post/publication, rounds used.
- `post_refs` the post x reference matrix (with raw URL and anchor text).
- `discovery` provenance: one row per way an entity was found (source, query, rank, page, round, parent, run).
- `queries`, `search_results` (every search hit, including rejected ones), `runs`, `fetch_log`, `posts_fts` (FTS5).

## 6. Decisions needed before implementing

1. **Time window.** Decided 2026-09-26: posts dated 2024-01-01 or later. Publications are kept regardless of age (a publication founded in 2019 with 2024+ posts is in scope; its pre-2024 posts are not harvested). Archive pagination is sorted newest-first, so harvesting stops at the first page whose posts all predate the cutoff; this cuts harvest and body-fetch volume substantially. The cutoff is a config value so a later run can widen it.
2. **Language.** Default: harvest everything, record `language`, restrict to English at analysis time.
3. **Content types.** Default: newsletter posts, podcast and video posts (metadata + show notes/transcript if present). Exclude Substack Notes and comments in v1; note as a limitation.
4. **Body-fetch policy.** A (everything, ~6 GB raw, ~a day of polite crawling) vs. B (targeted plus a calibration sample). Recommendation: A, it removes a whole class of false negatives and the cost is only disk and time.
5. **Site-wide search.** Decided 2026-09-26. Post search turned out to work anonymously with the right parameters, so it is a first-class, fully replicable discovery channel. The cookie is needed only for publication search and for the `is_ai_generated_text` flag; both are optional extras. The cookie is read from `~/.config/substack-publish/.env` (`COOKIES_STRING`), the same file and format the writing-workflow publish script uses, so it is never in this repo. Anyone replicating needs their own Substack account cookie in that file; the pipeline degrades gracefully (skips the channel, logs it in the run manifest) when it is absent. Verified 2026-09-26: publication search returns results with the cookie.
6. **Search backend.** Decided 2026-09-26: Brave Search API primary (key in `BRAVE_API_KEY`, same env file or environment). Optional later: one SerpAPI Google pass for a coverage comparison.
7. **Snowballing.** Dropped 2026-09-26 in favour of citation expansion (see §3). Seeds became a validation list.
8. **Unit of inclusion.** The post. Publications and authors are recorded as context and can be analysed, but nothing enters the corpus because of the publication it belongs to.
9. **Coupling threshold.** `min_citing_posts: 2` to start; the report shows the distribution of citing counts so it can be tuned with evidence.

## 7. Project layout

```
mc-lit-review/
  pyproject.toml           # uv-managed: requests, pyyaml, typer, python-dotenv, selectolax
  config/settings.yaml  queries.yaml  validation.yaml
  src/mcreview/
    config.py context.py db.py raw.py http.py      # infrastructure
    substack.py brave.py                           # endpoint wrappers
    discover.py                                    # phase 1 + resolve
    bodies.py                                      # bodies, text
    refs.py citations.py                           # phase 2
    harvest.py                                     # optional archive-meta context
    cli.py
  data/corpus.sqlite  data/raw/                    # gitignored
  runs/                                            # logs
  PLAN.md  README.md
```

## 8. Rough sizing

| Stage | Requests | Notes |
|---|---|---|
| Phase 1 web search, 222 queries x 5 pages | ~1,100 | ~20 min at Brave's 1 req/s |
| Phase 1 Substack search, 92 terms x 10 pages | ~920 | ~40 min at 2.5 s spacing |
| Bodies for phase-1 posts | 10-20k | hours; 4 workers, per-host and global spacing |
| Per citation round: titles + coupling queries | hundreds to a few thousand | depends on how many references cross the threshold |
| Bodies for citation-round posts | thousands | as above |

## 9. Known limitations to document in METHODS.md

- Paywalled posts: metadata only.
- Deleted/unpublished posts and publications that moved off Substack (e.g. to Ghost/beehiiv) are missed unless captured via Wayback.
- Substack's own search is recency-skewed; 2024-2025 coverage relies on Brave and citation expansion.
- Search-engine results are non-deterministic across time; we store dated result sets and treat them as one sampled channel among several.
- Custom-domain publications are reached only through unfiltered web queries, Substack search, and citations from posts already in the corpus; `.substack.com` coverage is likely higher. Coupling searches use the `site:substack.com` filter and therefore find only `.substack.com` hosts.
- Citation expansion favours posts that link; essays without links are found only lexically.
- Coupling targets require an identifier or a title: tweets, videos and untitled pages cannot be coupling targets even when widely cited.
