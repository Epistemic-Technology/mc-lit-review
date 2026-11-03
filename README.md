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
uv run mcreview titles               # name cited works the rounds left untitled (lab blogs, books, social, refused pages)
uv run mcreview archive-meta         # optional context: archive metadata for publications with >= N corpus posts
uv run mcreview update --since YYYY-MM-DD   # bring the corpus up to the present (see below)
uv run mcreview check-validation     # were the publications in config/validation.yaml found unaided?
uv run mcreview report               # unique yield per channel / term, top coupling references
uv run mcreview status
```

Every stage is idempotent and records a row in `runs` with the config hash. Provenance for every post is in
`discovery`; the post-by-reference matrix is `post_refs`; every HTTP request is in `fetch_log`; raw responses
are in `data/raw/`.

## Updating the corpus

`mcreview update --since <date>` brings an existing corpus up to the present without disturbing it (first run
2026-10-13 against the 2026-09-27 corpus, `--since 2026-09-20`, a week of overlap). Everything already
gathered, coded, embedded or laid out is kept; only new material is processed.

Gathering: the Brave query bank is re-run with Brave's date filter from `--since` to today (separate query
rows, variant suffixed `@<since>`, results enter as the usual `brave` channel at round 0); Substack post
search is re-run as is (it is recency-ranked); citation rounds are numbered after the corpus's last round and
do what a round does for the new posts, plus, in the first round, a date-filtered coupling pass over the
references already searched (new posts citing the corpus's shared references). Analysis: subset, Jev on the
new posts (on the constructs Jev has coded before), Claude on those Jev rates relevant, code_final, publication
enrichment and typing for new relevant publications, archive refresh for known ones (`archive-meta
--relevant-only --refresh` pages newest-first and stops at the first page with nothing new; stored engagement
counts are not refreshed), titles, embeddings, topic assignment (`topics --assign`: each new post joins the
cluster of its nearest laid-out neighbours, as a peripheral member, so cluster numbers and hand-checked labels
survive), network, export. Then `uv run python analysis/figures/make.py` and the site build. Every stage is
idempotent, so an interrupted update is resumed by running the same command again.

## License

Code is released under the [MIT License](LICENSE). The text, figures and exported data of the companion site
([machine.epistemic.technology](https://machine.epistemic.technology/)) are licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
