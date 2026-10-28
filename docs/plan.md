# Analysis, visualisation and companion-site plan

Status: 2026-09-30. Stages 0-3 complete. Jev coded 22,842 posts x 3 repeats (34 min, $37.20); Claude Opus 5.5
via Claude Code coded the 4,107 posts Jev rated relevant at >= 0.25 (29 h wall-clock across six subscription
windows, 0 failures, $538 list-price equivalent, no charge). Claude finds 2,763 relevant (central 1,519,
substantial 1,244). Jev-Claude agreement: arguments and structure 0.84-0.96, stance items 0.27-0.69 (Jev
over-attributes stance where Claude says not addressed), relevance 0.65 on this borderline-inclusive set.
Human verification done 2026-10-01 to 10-06 (relevance 100, stance 40, publications 29 of 30; median 6 s per
decision). Results: Claude vs human on the four headline stance items 0.83-0.95 (n=40), with scattered
adjacent-category disagreements and no systematic direction; Jev vs human on relevance 0.80 (n=85); Jev vs
human on publication community 0.66 (n=29), Jev over-assigning specialist labels where the human chose
culture_general (rubric to be tightened). The Jev gate missed 4 of the 12 human-relevant posts (Jev mass
0.013-0.083), so the Claude threshold was lowered from 0.25 to 0.05 on 2026-10-06, adding ~1,750 posts
Second Claude pass done 2026-10-06 (1,749 posts, 4 h incl. one usage pause): it added only 35 relevant posts
(2%), so Claude's relevant set is 2,791 (central 1,514, substantial 1,277) from 5,856 posts coded. Residual
loss below 0.05 is documented from the human sample. On the 22 sample posts both coded, human and Claude
agree on relevant-vs-not for 19; the 3 misses are human "central", Claude "passing" (Claude is conservative,
never the reverse). Publication typing: Jev vs human 0.66 under both rubric 0.1.0 (over-specialist) and
0.1.1 (over-general); rubric 0.1.2 is the middle ground and Claude codes publications as coder of record.
Claude's first pass (thin state) agreed with the human on only 14 of 29 and coded 405 publications "other";
the cause was missing metadata, so stage 6 ran early: homepage metadata for 345 publications, byline bios,
and an archive-meta crawl of all 1,606 relevant publications (14,958 pages, 276,651 context posts, 10 h,
2026-10-06/07; 5 publications gone 404/403). On the enriched state (publication_version 0.1.3) Claude
agrees with the human on 17 of 29, Jev on 17 of 29, Jev with Claude on 0.72 (from 0.53); "other" fell to
119. The human re-checked the sample on the enriched state (2026-10-07; 11 of 29 labels changed): Claude vs
human 20 of 29 (0.69), Jev 17 of 29 (0.59). The nine remaining disagreements sit on three boundaries
(philosophy vs science, rationalist vs AI industry, general vs business), so charts use a five-group
collapse (academic, AI field, general, journalism, religion) where agreement is higher; the nine-way labels
stay in the data. Publication constructs carry their own version (`publication_version`) so rubric changes
re-code publications only.

Stage 5 (2026-10-07): citation network built over the analysis subset: 5,527 posts touch a cross-publication
corpus link, 5,270 edges, 755 Leiden communities (most are small components). Only 715 of the 2,791
relevant posts have any such link and 79 are cited by two or more publications, so the discourse is
sparsely interlinked and post-level centrality is thin; the publication-level graph (2,628 nodes, 3,182
edges, 1,688 backbone edges) is the one to chart. Most-cited relevant posts: Dwarkesh Patel's "The Rise and
Fall of Agent Civilizations" (63 citing publications), then Gary Marcus and Astral Codex Ten pieces (5-10
each), Joe Carlsmith on AI moral status and Erik Hoel on ChatGPT's consciousness (4 each). Embeddings:
bge-small-en-v1.5, 2,803 relevant posts, mean of up to 12 x 2,000-char chunks (39 min CPU). Topics: UMAP 10-D +
HDBSCAN leaf selection (eom collapsed to 2 clusters) gives 33 clusters with 1,380 peripheral posts attached
to their nearest centroid (cluster_prob 0); Claude-suggested labels in `topics.label`, to be hand-checked.
Largest: moral recognition and welfare politics (240), general consciousness debate (179), human-Claude
companion testimonies (155), souls and spirituality (141), humanity's fate after superintelligence (127).
Labels hand-checked 2026-10-08 (`analysis/topic_labels.csv`, `mcreview topics-export/import`).

Stages 7, 9, 10 (2026-10-08): `mcreview export` writes site/src/data/*.json (posts with codes, stance/argument/
topic/network/source/publication aggregates, methods, per-publication slices; no bodies). Stage 4 leftovers
done: `config/domain_tiers.yaml` (source tiers) and `config/names.yaml` (named-person mentions).
`analysis/figures/make.py` renders eight post figures (PNG+SVG in figures/, Vega-Lite specs in
site/src/charts/) with the dataviz method's reference palette: stance landscape (diverging stacked bars),
stance by publication type, arguments frequency+traction, stance over time (unbiased channels only), top
cited works by tier, who writes, who gets named, largest topics. The site (Observable Framework, site/) has
nine pages plus 1,606 publication pages, builds clean, and ships with a Dockerfile (node build -> Caddy),
Caddyfile and railway.json for Railway. Not done: stage 8 (outreach lists), stage 11 (METHODS.md as a
document; the site's Methods page carries the content), PRISMA diagram as a figure, static network figure,
Railway deployment itself, git commit (nothing committed yet). The gathering pipeline
and its decisions are in `../PLAN.md`; the research questions are in the Obsidian note "questions for
Substack machine cognition study"; the Jev research is in `jev.md`.

Update (2026-10-13): `mcreview update --since 2026-09-20` brought the corpus from the 2026-09-27 gathering run to
the present (README, "Updating the corpus"). Clusters, labels and existing codes were kept; new posts were
attached to the existing topic clusters by nearest neighbours rather than re-clustered. Counts below describe
the 2026-09-27 corpus; the site's Methods page carries the current ones.

## 1. Principles (carried over from gathering)

- **Every code is a measurement.** Each label on a post records which engine produced it, with which
  codebook version, at what confidence, and in which run. Raw model responses are stored.
- **Gold set before scale.** No classifier output is reported until its agreement with a human-coded
  sample is measured per construct.
- **Config in the repo.** Codebook, question definitions, thresholds, domain tiers, and site data
  exports are versioned files. Re-running the analysis is a command, not a memory.
- **Publish codes, not bodies.** The companion site and the released dataset carry metadata, links and
  codes. Post bodies stay in `data/` and are never republished.

## 2. Stages

Each stage is a `mcreview` subcommand or a script in `analysis/`, and each writes to new tables in the
same SQLite file so provenance joins stay trivial.

### Stage 0: analysis subset (`mcreview subset`)

Defines the population all later stages use. Rules live in `config/analysis.yaml`.

- English (`language = 'en'` or NULL with an English-detected body), `post_date >= 2024-01-01`,
  `body_status = 'ok'`, `entry_round IS NOT NULL`.
- Drop publications on a spam list (`config/exclusions.yaml`; seeded with the self-linking and
  aggregator hosts found in the reference table).
- Flag, not drop: paywalled (preview only), podcast/video (show notes only), roundup newsletters
  (detected in stage 3 as genre).
- Output: `analysis_posts` view plus a `subset_runs` row with counts at each rule, for the PRISMA figure.

Current estimate: 23,445 posts, ~96M tokens.

### Stage 1: codebook (`docs/codebook.md`, `config/codebook.yaml`)

One human-readable codebook and one machine-readable file that generates the Jev questions and the
frontier-model prompts from the same definitions. Constructs, in coding order:

| Construct | Primitive | Options |
|---|---|---|
| relevance | choice | central / substantial / passing / irrelevant |
| ai_not_minds | noul | AI is the topic but minds are not |
| genre | choice | argumentative essay / news roundup / fiction / model-conversation transcript / interview or podcast / other |
| claim_object | choice | LLMs generally / AI generally / named model or lab / not applicable |
| stance_* (12 items) | choice | asserts / denies / agnostic / discusses without committing / reports others only / not addressed |
| argument_* (13 items) | noul | present / absent |
| reports_lab_view | noul | post substantially reports a lab's or philosopher's position |

Every Choice has an abstain option ("not addressed", "not applicable", "other"). Option names are
meaningful and fixed. Each option carries structured criteria (`what`, `not_for`, `examples`).
The codebook has a version string; every code row records it.

### Stage 2: validation (`mcreview gold sample`, `mcreview gold agreement`)

Solo project, one human, a few hours of coding time in total. There is no inter-rater reliability
study. Reliability is established three ways instead, and the write-up says so plainly:

1. **Two model families as independent coders at scale.** Jev and a frontier model code every post.
   Their agreement per construct, over the whole relevant subset, is the reported reliability figure.
   It measures consistency, not validity, and the methods page says that.
2. **Human verification, not human coding.** The frontier model returns an evidence quote for every
   stance and argument code. The human checks whether the quote supports the code. Verifying a quote
   takes seconds; coding a 2,700-word essay from scratch takes ten minutes. This is where the human
   hours go.
3. **Targeted spot checks where errors concentrate.** Items where the two engines disagree, and items
   below the confidence threshold, are sampled for verification in addition to a small random sample.

Human budget, about four hours:

| Task | Items | Basis for judgment | Time |
|---|---|---|---|
| Relevance | 100 random from the subset | title, subtitle, first 300 words | ~1 h |
| Stance and arguments, random | 20 relevant posts | model codes plus evidence quotes, full text on hand | ~1 h |
| Stance and arguments, disagreements | ~40 codes where Jev and the frontier model disagree | evidence quotes, surrounding paragraph | ~1 h |
| Publication community type | 30 publications | name, tagline, bio, titles | ~30 min |
| Codebook revision after round one | | | ~30 min |

What this buys: with 20 posts an observed 85% agreement has a confidence interval of roughly 62% to
97%, so the numbers are a sanity check, not a validation. The relevance check at n=100 is tighter
(±7 points) and matters most, because every downstream number depends on that gate. Stance items are
checked by quote verification, which is the right unit anyway: a wrong quote is a wrong code.

Rules:
- The random samples are drawn once, before any prompt tuning, and frozen (`gold_codes`, with a
  `sampled_at` and `codebook_version`).
- Disagreement adjudication may revise the codebook; the random sample is then re-scored under the new
  version but never re-drawn.
- Everything the human sees is stored: the quote, the decision, and the time spent.
- All codes and quotes are published in the dataset, so readers can audit any post themselves. For a
  Substack post the standard is transparency, and the site makes every code checkable in one click.

**Tool.** A single-page app (`analysis/coder/index.html`) showing, per item, the model's code, its quote,
the surrounding text, and accept / reject / fix buttons. Keyboard-driven so 100 relevance checks take
an hour. Served by `python3 analysis/coder/serve.py 8765` (exposed over the tailnet with
`devserve start coder 8765`): the page lists the exported samples in `analysis/coder/data/` and
autosaves decisions to `data/<sample>-decisions.json` on the server, which `mcreview gold-import` reads.

### Stage 3: machine coding (`mcreview code`)

Cascade design, per `jev.md` §4.

1. **Jev pass** over the full subset, all questions in one request per post, state as
   `{"title", "subtitle", "body"}` with body truncated to fit 32k tokens. Pinned `jev-1.13.0`. Three
   repeats with permuted option order; probabilities averaged; per-run values stored. Cost ≈ $12 for
   three passes.
2. **Frontier pass** on the relevant subset (relevance = central or substantial, by Jev, with a
   generous threshold so the frontier model also sees the borderline). Structured output, same
   codebook text, evidence quote required for every stance and argument code. The frontier model is
   the coder of record for stance; Jev is the coder of record for relevance and the cheap structural
   codes where the two agree. (Decision needed: which model; see §5.)
3. **Agreement** Jev vs frontier per construct over the whole relevant subset: accuracy treating the
   frontier as reference, macro-F1, calibration of Jev's confidence against frontier agreement
   (reliability diagram, ECE), and the agreement/coverage curve by confidence threshold. The human
   spot checks from stage 2 sit alongside these numbers.
4. **Thresholds** per construct chosen from the agreement/coverage curve and written to
   `config/thresholds.yaml`. Above threshold Jev's code stands; below it the frontier code stands;
   where the two disagree above threshold the item goes to the human disagreement queue (stage 2).
5. **Sensitivity runs**, reported not hidden: two alternative criteria wordings, option-order
   permutation variance, repeat variance.

Tables: `code_runs` (engine, model id, codebook version, config hash, started/finished, cost),
`codes` (post_id, run_id, construct, value, probability, confidence, evidence_quote, raw_ref),
`code_final` (post_id, construct, value, source engine, confidence) materialised after the cascade.

### Stage 4: entities and sources

- **Publication typing** (`mcreview code --target publications`): community type from name, tagline,
  author bio, and corpus post titles. Same cascade. Human check on 30 publications (stage 2). Where
  Substack's category leaderboards overlap, report agreement.
- **Author typing**: academic philosopher / AI researcher or lab staff / journalist or science writer /
  generalist / anonymous, from `authors.bio`. Only for authors with two or more relevant posts plus the
  outreach list.
- **Named-person mentions**: regex over bodies for a fixed list of philosophers, scientists and lab
  figures (`config/names.yaml`), counted per post. Cheap and fully deterministic.
- **Source tiers**: `config/domain_tiers.yaml` maps reference domains to academic / lab / press /
  encyclopedia / forum / social / book / other. arXiv and DOI are academic by kind. Image hosts and
  tracking domains are dropped. Reference counts are recomputed on the relevant subset.
- **Academic uptake**: a hand-built list of the 2023–2026 academic works on AI consciousness and welfare
  with their arXiv/DOI ids, matched against `refs`.

### Stage 5: structure

- **Embeddings**: one open embedding model, pinned by name and version, run locally over title plus
  body of the relevant subset (`embeddings` table, vectors stored as blobs or a parquet sidecar).
- **Topics**: UMAP to 2D for display, HDBSCAN on the full-dimensional vectors (or BERTopic wrapping
  both). Cluster labels written by the frontier model from the top terms and ten central titles, then
  hand-checked. Positions and cluster ids stored in `post_layout`.
- **Citation network**: edges from `post_refs` where the target is a corpus post, intra-publication
  edges excluded. igraph: Leiden communities, in-degree by distinct citing publications, PageRank,
  betweenness. Publication-level aggregation with a disparity-filter backbone for the static figure.
  Layout computed once (ForceAtlas2 or Fruchterman-Reingold) and stored in `network_layout`.
- **Cross-check**: contingency of topic cluster vs citation community; stance composition per community.

### Stage 6: archive metadata for baselines (`mcreview archive-meta`)

Run the already-designed optional stage for the 3,677 publications with two or more corpus posts:
archive metadata back to 2024-01-01, no bodies. Yields per-publication baseline reactions, comments
and restacks, and output share (relevant posts / all posts). About 3,700 publications × a few pages at
2.5 s spacing ≈ 6–8 hours, resumable.

### Stage 7: analyses (`analysis/notebooks/` or scripts, one per research question group)

Every figure and table in the post and on the site is produced by a script that reads only the SQLite
file and writes to `figures/` or `site/src/data/`. Mapping to the questions note:

| Section | Outputs |
|---|---|
| A relevance | PRISMA flow with counts at each gate; relevance by channel and by facet of the query bank |
| B stance | stance landscape (stacked bars per item); stance × claim object; stance × genre |
| C who and where | community type distribution; stance × community; author type; AI-flag share; engagement × stance |
| D sources | tiered top-cited works; named-person counts; academic uptake by community; topic map; network centrality tables; topic × community contingency; cross-camp citation matrix |
| E arguments | argument frequency; frequency × traction scatter; arguments × community; rare-argument list |
| F time | composition by quarter on unbiased channels; event windows |
| Methods | Jev vs frontier agreement at scale; human spot-check results; calibration; sensitivity; query-term unique yield |

### Stage 8: outreach lists (`mcreview outreach`)

Four ranked lists from the relevant subset, each with publication, author handle, subscriber band,
and a one-line stance summary:

1. central: in-degree by distinct publications;
2. over-performing: reactions / publication baseline (stage 6), fallback reactions / subscriber band;
3. bridging: betweenness, and posts cited from more than one community;
4. representatives: top engagement within each stance camp × community type cell.

Excludes posts flagged AI-generated. Merged and deduplicated to ~40 candidates in
`outreach/candidates.csv`; the hand-picked ~20–25 for the post and the ~200 for the site are separate
columns. Every candidate's stance summary is checked against the evidence quote before use.

### Stage 9: static figures

- Altair (Vega-Lite) with one shared theme module (`analysis/theme.py`): palette, fonts, sizes; the
  dataviz guidance is loaded before the theme is written. PNG via `vl-convert` at 1200 px wide, checked
  at 600 px.
- Network and topic-map statics are rendered from the stored layouts with matplotlib or Vega using
  precomputed positions; no live force simulation.
- Post figure list (final selection later): PRISMA flow; stance landscape; stance × community;
  argument frequency × traction; composition over time; top-cited works; backbone network.

### Stage 10: companion site (`site/`, Observable Framework, Railway)

**Content.**
- Home: the headline charts, interactive versions of the post figures.
- Explore: linked dashboard (community selector → stance, arguments, sources update).
- Network: D3 rendering of the stored layout; post and publication views; hover title, click opens post;
  filters for stance, community, quarter.
- Topic map: UMAP scatter with cluster hulls and the same filters; brushing updates side charts.
- Timeline: composition by quarter with clickable event markers.
- Corpus table: searchable, filterable, sortable; columns title, publication, author, date, codes,
  reactions, restacks, link. Download as CSV.
- Publications: one page per publication in the relevant subset (posts, network position, stance
  profile vs field). This is the outreach hook.
- Methods: gathering flow, codebook, gold-set agreement, calibration, sensitivity, dataset download,
  licence.

**Data.** `mcreview export` writes `site/src/data/*.json` and `*.parquet`: aggregates per figure,
`posts.parquet` (metadata + codes, no bodies), `network.json` (nodes with positions, edges), `layout.json`
for the topic map, `publications.json`. Files are committed; a data refresh is a commit.

**Framework.** Observable Framework. Pages are Markdown with JavaScript cells; charts via Observable Plot;
network and map via D3. Data loaders are unnecessary because the export step produces the files
directly. Build output is a static `dist/`.

**Railway.**
- One service, deployed from the GitHub repo with root directory `site`.
- Dockerfile, multi-stage: `node:22` builds (`npm ci && npm run build`), `caddy:2` serves `dist/`.
  Caddyfile listens on `:{$PORT}` (Railway injects `PORT`), serves static files with gzip and
  long-cache headers for hashed assets, `try_files` for clean URLs.
- Watch paths limited to `site/**` so pipeline commits don't trigger deploys.
- Health check on `/`. Custom domain via Railway's domain settings and a CNAME.
- Preview environments per PR for reviewing site changes.
- No database, no volume, no secrets in the service; the site is fully static.

**Privacy and licence.** No bodies, no comments, no subscriber-count precision beyond Substack's own
public band. Dataset released under CC BY 4.0 for the codes and metadata we produced; post titles and
links are facts about public documents. State this on the methods page.

### Stage 11: methods document and replicability

`METHODS.md` at the repo root (or `docs/methods.md`): gathering summary with the run manifest, subset
rules with counts, codebook version, validation design (two engines, human verification budget and
results), engine versions and thresholds, calibration, sensitivity, network and topic parameters,
limitations (paywalls, recency skew, closed models, non-English exclusion, single coder). Every number
is generated by a script and pasted from its output.

## 3. Repo additions

```
config/analysis.yaml  exclusions.yaml  codebook.yaml  thresholds.yaml  names.yaml  domain_tiers.yaml
docs/codebook.md  jev.md  plan.md  methods.md
src/mcreview/subset.py  codebook.py  engines/{jev,claude}.py  code.py  gold.py  entities.py
                embeddings.py  network.py  outreach.py  export.py
analysis/theme.py  analysis/figures/*.py  analysis/coder/   analysis/notebooks/
figures/            # generated PNG/SVG, committed
outreach/           # candidates.csv, hand-picked lists
site/               # Observable Framework project, Dockerfile, Caddyfile, src/data/*
```

New tables: `subset_runs`, `gold_codes`, `code_runs`, `codes`, `code_final`, `publication_codes`,
`author_codes`, `name_mentions`, `ref_tiers`, `embeddings`, `post_layout`, `network_layout`,
`network_metrics`, `outreach_candidates`.

## 4. Order of work

1. Stage 0 subset and Stage 1 codebook draft. (days)
2. Draw and freeze the random samples. Jev pass, then the frontier pass on the relevant subset. (days,
   mostly waiting on API calls)
3. Verification tool; the four hours of human checks; codebook revision; re-score. Thresholds.
4. Stage 6 archive-meta run in the background from step 1 onward.
5. Publication typing, names, tiers, embeddings, network. (days)
6. Analyses and figures; iterate on the post's chart list. (a week)
7. Site scaffold on Railway early, with placeholder data, so deployment is solved before content exists;
   then fill pages as exports stabilise.
8. Outreach lists; hand-check summaries; write the post.
9. METHODS.md and dataset release alongside the post.

## 5. Decisions needed

1. **Validation budget.** Decided 2026-09-29: solo, no second coder, ~4 hours of human verification as
   in stage 2. Open: whether to add a second frontier model family for a three-engine agreement figure
   (cheap, strengthens the reliability claim, no human time).
2. **Frontier engine.** Decided 2026-09-29: Claude Opus 5.5 driven through the Claude Code CLI on the
   subscription (`coding.claude.transport: cli`), not the API. No per-token charge; throughput is
   bounded by the subscription's usage windows, and each call carries ~12k tokens of Claude Code's own
   context. The API transport (with batch mode) stays available behind a config switch. Open: the
   effort level, once evidence quotes have been inspected.
3. **Embedding model**: an open, locally runnable model pinned by version, so the topic map is
   replicable without an API.
4. **Archive-meta scope**: all 3,677 publications with two or more corpus posts, or only those in the
   relevant subset (known after stage 3).
5. **Mentions in the post**: target count (20–25 proposed) and whether large accounts are mentioned or
   only linked.
6. **Site domain** and whether the dataset download lives on the site or on Zenodo with a DOI.
7. **Which stance items get human verification.** All twelve on 20 posts, or the four headline items
   (current consciousness, potential consciousness, current cognition, current moral worth) on 40
   posts. The second gives tighter numbers where the post's claims will rest.

## 6. Rough costs

| Item | Estimate |
|---|---|
| Jev, three full passes over 23k posts | ~$12 |
| Jev sensitivity runs (three wordings) | ~$12 |
| Claude Opus 5.5 on the relevant subset via Claude Code subscription | no charge; days of wall-clock at subscription pace (list-price equivalent ~$300-600 for ~10k posts, recorded for reference) |
| Archive-meta run | 6–8 hours of polite crawling, no API cost |
| Embeddings, local | GPU/CPU hours only |
| Railway static service | hobby tier, a few dollars a month |
| Human verification | ~4 hours, one person |
