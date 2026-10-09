---
title: Methods
---

# Methods

```js
import {statRow, ITEM_LABELS} from "./components/charts.js";
const summary = await FileAttachment("./data/summary.json").json();
const methods = await FileAttachment("./data/methods.json").json();
const codebook = await FileAttachment("./data/codebook.json").json();
```

## How the corpus was built

Posts entered through documented routes only: a lexical search over a query bank (Brave web search with and without a `site:substack.com` filter, and Substack's own post search), then three rounds of citation expansion (every Substack post cited by a corpus post was fetched; every outside work cited by two or more corpus posts became a new search). Every post records how it was found. Bodies were fetched for free posts; paywalled posts keep their public preview only.

```js
const p = summary.prisma;
display(Inputs.table([
  {step: "Posts gathered (2026-09-27)", posts: p.corpus},
  {step: "Dated 2024-01-01 or later", posts: p.after_date},
  {step: "English or undetected language", posts: p.after_language},
  {step: "Body fetched (free posts)", posts: p.after_body},
  {step: "At least 400 characters", posts: p.after_min_chars},
  {step: "After excluding two aggregator publications", posts: p.after_exclusions},
  {step: "Screened by Jev (decision model), three repeats", posts: p.jev_coded},
  {step: "Coded by Claude (relevance mass ≥ 0.05 in the Jev screen)", posts: p.claude_coded},
  {step: "Relevant: central or substantial", posts: p.relevant}
], {columns: ["step", "posts"], header: {step: "Stage", posts: "Posts"}, width: {step: 480}}));
```

## How posts were coded

Two engines read every post against one codebook. **Jev** (TypeSafe's decision model) screened all posts for relevance and produced structural codes, three times with option order permuted; its confidence is a calibrated probability. **Claude Opus 5.5** coded every post Jev rated at all likely to be relevant, returning for each construct a value and a verbatim evidence quote. Claude is the coder of record for stance and arguments; where it disagrees with Jev on relevance, Claude's judgment stands.

The codebook has ${codebook.constructs.length} post-level constructs: a four-level relevance gate, genre, the object of the claim, ${codebook.constructs.filter((c) => c.group === "stance").length} stance items each coded on a six-value scale (asserts, denies, agnostic, discusses without committing, reports others only, not addressed), and ${codebook.constructs.filter((c) => c.group === "argument").length} argument types coded present or absent. Publications were typed into nine communities from name, tagline, author bio and post titles, after a crawl of each publication's archive back to 2024.

### From fourteen claims to six questions

The stance items proved too granular to read: most were not addressed in most posts, and when a post committed on two related items it almost always answered them the same way (current cognition and understanding agree 95% of the time, current consciousness and emotions 91%, future moral worth and precaution 98%). The site therefore reports six derived questions, computed deterministically from the coded items without re-coding. Agency (goals of one's own) is kept apart from thinking even though the two agree when both are coded, because a third of the posts that commit on agency commit on no other cognition claim, and many grant goals while unsure about experience. Each question has a primary item whose committed answer wins; related items are consulted when it is silent; asserting that we cannot know counts as unsure on experience; and a post that only discusses any contributing item counts as discussed. The qualified-yes level captures the one real nuance per question: thinking in some respects but not others, possibility only after a major advance, and moral status for future AI or as a precaution. Posts that only report others' positions count as not addressed, since the question asks for the author's own view.

```js
display(html`<table class="axes">
  <thead><tr><th>Question</th><th>Asks</th><th>Qualified yes means</th><th>Built from (primary first)</th></tr></thead>
  <tbody>${codebook.axes.map((a) => html`<tr><td><b>${a.label}</b></td><td>${a.question}</td><td>${a.qualified || ""}</td><td>${a.items.map((i) => ITEM_LABELS[i] || i).join("; ")}</td></tr>`)}</tbody>
</table>`);
```

### Codebook 0.2.0: the six questions coded directly

Once the derived questions proved readable, codebook 0.2.0 made them the instrument: each question is a construct with its own options, with a shared level scheme and a question-specific qualified yes. Claude re-coded the six questions on every relevant post on 2026-10-08. Nothing else changed; relevance, genre, object, and the thirteen argument types keep their 0.1.0 codes, and the fourteen retired items stay in the data.

The re-code is a check on the derivation. Below, each post's derived answer is compared with its coded answer. Exact agreement counts the full six-level match; polarity agreement collapses yes and qualified yes to "pro", no to "con", unsure and discussed to "neutral", and is computed over posts that both sides treat as addressing the question. Reversals are posts where one side says yes and the other no.

```js
const cmp = methods.axes_derived_vs_coded;
if (cmp) {
  display(html`<p class="caption">${cmp.n.toLocaleString()} relevant posts with both a derived and a coded answer on every question.</p>`);
  display(Inputs.table(cmp.axes.map((a) => ({question: a.label, exact: a.exact, coarse: a.coarse, n_both: a.n_both, polarity: a.polarity, reversals: a.reversals, na_derived: a.na_derived, na_coded: a.na_coded})), {
    columns: ["question", "exact", "polarity", "n_both", "reversals", "na_derived", "na_coded"],
    header: {question: "Question", exact: "Exact agreement", polarity: "Polarity agreement", n_both: "Both address it", reversals: "Reversals", na_derived: "Not addressed (derived)", na_coded: "Not addressed (coded)"},
    format: {exact: (v) => v.toFixed(2), polarity: (v) => (v == null ? "" : v.toFixed(2)), n_both: (v) => v.toLocaleString(), na_derived: (v) => v.toLocaleString(), na_coded: (v) => v.toLocaleString()},
    width: {question: 240}, select: false, rows: 8
  }));
} else {
  display(html`<p class="caption">The 0.2.0 re-code has not been exported yet.</p>`);
}
```

```js
const cmpAxis = cmp ? view(Inputs.select(new Map(cmp.axes.map((a) => [a.label, a.name])), {label: "Confusion matrix for"})) : null;
```

```js
if (cmp) {
  const a = cmp.axes.find((x) => x.name === cmpAxis);
  const lv = cmp.levels, short = {yes: "Yes", yes_qualified: "Yes, qualified", unsure: "Unsure", discussed: "Discussed", no: "No", not_addressed: "Not addressed"};
  const cell = Object.fromEntries(a.matrix.map((m) => [`${m.derived}|${m.coded}`, m.n]));
  display(html`<table class="axes"><thead><tr><th>Derived ↓ · Coded →</th>${lv.map((c) => html`<th>${short[c]}</th>`)}</tr></thead>
    <tbody>${lv.map((d) => html`<tr><td><b>${short[d]}</b></td>${lv.map((c) => html`<td style="text-align:right;${d === c ? "font-weight:600" : ""}">${cell[`${d}|${c}`] || ""}</td>`)}</tr>`)}</tbody></table>`);
}
```

The two agree closely on experience, goals, and moral status; the differences sit in the neutral band, between unsure and discussed, where the codebook expects fuzziness. Two questions moved by design rather than by disagreement. On seriousness, the retired item only fired when an author argued the hype line or rebutted it, whereas the new question asks about the author's framing, so the coder now marks most engaged essays as treating the question seriously. On possibility in principle, the coder infers a yes from how an author treats the current path, where the old item needed an explicit claim. The qualified yes on thinking is used about three times as often once it is defined for the coder rather than inferred from a split across items. Reversals are rare on every question; on thinking, nearly all of them are posts the derivation had as no that the coder now reads as partly. The published figures use the coded answers; the derived ones remain in the export for anyone who wants to repeat this comparison.

The engine-agreement and human-verification figures below are on the coded items; the stance rows refer to the retired 0.1.0 items, and a new verification sample against the six questions is still to be drawn.

## How well the coding holds up

This is a one-person project. There is no inter-rater study; reliability rests on three things: agreement between the two engines at scale, a human verification of a sample, and publication of every code and quote so any reader can audit any post.

### Engine versus engine

```js
display(Inputs.table(methods.jev_vs_claude_posts.map((r) => ({construct: ITEM_LABELS[r.construct] || r.construct, n: r.n, agree: r.agree, c9: r["agree@0.9"], cov9: r["cov@0.9"]})), {
  columns: ["construct", "n", "agree", "c9", "cov9"], header: {construct: "Construct", n: "Posts", agree: "Agreement", c9: "Agreement where Jev ≥ 0.9 confident", cov9: "Share of posts there"},
  format: {agree: (v) => v.toFixed(2), c9: (v) => (isNaN(v) ? "" : v.toFixed(2)), cov9: (v) => `${Math.round(v * 100)}%`}, width: {construct: 300}, select: false, rows: 40, sort: "agree", reverse: true
}));
```

Arguments and structural codes agree at 0.84 to 0.96; stance items at 0.27 to 0.69, with Jev's characteristic error being to attribute a position where Claude finds the claim not addressed. That is why Claude, not Jev, is the coder of record for stance.

### Engine versus human

```js
display(Inputs.table(methods.engine_vs_human.map((r) => ({construct: ITEM_LABELS[r.construct] || r.construct, engine: r.source, n: r.n, agree: r.agree})), {
  columns: ["construct", "engine", "n", "agree"], header: {construct: "Construct", engine: "Engine", n: "Items checked", agree: "Agreement"}, format: {agree: (v) => v.toFixed(2)}, width: {construct: 300}, select: false, rows: 30
}));
```

The human checks: 100 random posts for relevance from title and lead; 40 relevant posts for the four headline stance items, verifying Claude's codes against its quotes; and 29 publications for type. Median time per decision was about six seconds. On relevance, the human and Claude agreed on relevant-versus-not for 19 of 22 posts both judged, with Claude conservative in every disagreement. On the four stance items, agreement was 0.83 to 0.95. On publication type, 0.69 across nine categories and 0.90 across the five groups used in charts.

### Known limitations

- **Recall at the gate.** In the relevance sample, 4 of 12 human-relevant posts had been screened out by Jev at the original threshold; lowering it recovered a 2 percent yield from 1,749 more posts. Some relevant posts with oblique titles remain unfound; the residual loss is estimated from the sample, not measured.
- **Time.** Substack's search returns almost only recent posts, so volume over time is not analysable. Composition over time uses only posts found through web search and citation, which still lean recent.
- **Paywalls.** ${summary.paywalled} relevant posts are paywalled and were coded from their public preview.
- **Closed models.** Both engines are hosted, closed models pinned by version. Every raw response is stored; the codebook, prompts, and gold sample are published so the coding can be rerun with any classifier.
- **One coder.** The human sample is small; its numbers are a sanity check on direction and magnitude, not a validation.

## Engines and versions

```js
display(Inputs.table(summary.engines.map((e) => ({engine: e.engine, model: e.model, target: e.target, version: e.codebook_version, items: e.n_items, started: (e.started_at || "").slice(0, 10)})), {
  columns: ["engine", "model", "target", "version", "items", "started"], header: {engine: "Engine", model: "Model", target: "Target", version: "Codebook", items: "Items", started: "Date"}, select: false, rows: 20
}));
```

Codebook version ${codebook.version}. Data generated ${summary.generated_at.slice(0, 10)}.
