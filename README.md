# mc-lit-review

Wide-net, replicable corpus builder for writing about machine cognition and machine consciousness on Substack.
Phase 1 is lexical search; phase 2 expands by citation (backward chasing and bibliographic coupling).
See `PLAN.md` for design and rationale.

## Setup

```bash
uv sync
# credentials (never committed): ~/.config/substack-publish/.env with BRAVE_API_KEY and, optionally, COOKIES_STRING
uv run mcreview init
```

## Pipeline

```bash
uv run mcreview discover             # phase 1: Brave + Substack search -> posts (round 0)
uv run mcreview resolve              # confirm web-search hosts are Substack publications
uv run mcreview fetch-bodies         # free post bodies -> text
uv run mcreview cite-round           # phase 2: references -> backward chase + coupling search (one round)
uv run mcreview run-all              # discover, resolve, bodies, then rounds until nothing new
uv run mcreview archive-meta         # optional context: archive metadata for publications with >= N corpus posts
uv run mcreview check-validation     # were the publications in config/validation.yaml found unaided?
uv run mcreview report               # unique yield per channel / term, top coupling references
uv run mcreview status
```

Every stage is idempotent and records a row in `runs` with the config hash. Provenance for every post is in
`discovery`; the post-by-reference matrix is `post_refs`; every HTTP request is in `fetch_log`; raw responses
are in `data/raw/`.
