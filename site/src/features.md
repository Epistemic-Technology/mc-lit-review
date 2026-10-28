---
title: Features of the systems
---

# Features of the systems

The arguments page tracks the philosophical moves. This page tracks what authors point to in the AI systems themselves: the training objective, the architecture, the absence of memory or a body, what the model says when asked, what interpretability finds inside it, how it behaves under evaluation, what it succeeds and fails at, and what it now does in the world. Each of fourteen features is coded per post with a direction: cited as a reason to think the system has or could have a mind, cited as a reason to think it lacks one, or raised without a direction. A feature mentioned without being connected to the question of minds is not counted. Successes and failures are separate questions so that the common sceptical move of granting the performance and denying it is evidence shows up as successes cited against a mind, distinct from pointing at what the system gets wrong.

```js
import * as Plot from "npm:@observablehq/plot";
import {vlChart, statRow, FEATURE_LABELS, DIRECTION_LABELS, directionColors} from "./components/charts.js";
const feats = await FileAttachment("./data/features.json").json();
const landscapeSpec = await FileAttachment("./charts/features_landscape.vl.json").json();
const timeSpec = await FileAttachment("./charts/features_over_time.vl.json").json();
const sidesSpec = await FileAttachment("./charts/features_sides.vl.json").json();
const DIRS = feats.directions;
const byName = new Map(feats.features.map((f) => [f.name, f]));
const pct = (n, d) => (d ? `${(100 * n / d).toFixed(0)}%` : "");
```

```js
const top = [...feats.features].sort((a, b) => b.n - a.n)[0];
const forTotal = feats.features.reduce((a, f) => a + f.direction.for, 0);
const againstTotal = feats.features.reduce((a, f) => a + f.direction.against, 0);
display(statRow([
  ["Posts coded", feats.n_coded.toLocaleString(), `of ${feats.n_posts.toLocaleString()} relevant posts`],
  ["Point to at least one feature", feats.any_feature.toLocaleString(), `${pct(feats.any_feature, feats.n_coded)} of coded posts`],
  ["Most cited", FEATURE_LABELS[top.name], `${pct(top.n, feats.n_coded)} of posts`],
  ["Direction, all citations", `${pct(forTotal, forTotal + againstTotal)} for`, `${forTotal.toLocaleString()} toward a mind, ${againstTotal.toLocaleString()} against`]
]));
```

## Which features get pointed to, and which way

```js
display(await vlChart(landscapeSpec));
```

<div class="caption">Each bar is the share of coded relevant posts that point to the feature, split by direction: to the right, cited as reason to think the system has or could have a mind; to the left, cited as reason it lacks one; grey straddling zero, raised without a direction. The number at the right is the count of posts citing the feature.</div>

## Where each side finds its evidence

```js
display(await vlChart(sidesSpec));
```

<div class="caption">A post affirms if it answers yes, or a qualified yes, to at least one of the six questions and no to none; it denies if the reverse. Posts that do both, or commit to neither, are left out. Among the posts on each side that cite at least one feature in their own direction, the top panel shows the share citing each feature: denying posts to the left, affirming posts to the right, sorted by the denying side. Denials converge on a small package, led by granting what the system succeeds at and denying that it counts; affirmations spread across the list, with no feature cited by more than half.</div>

## Over time

Volume cannot be read from this corpus, so the chart shows composition: among the relevant posts found through web search or citation (Substack's own search is recency-skewed and excluded), the share per quarter that point to each feature. Features are grouped into four families.

```js
display(await vlChart(timeSpec, {width: Math.min(width, 760) - 120}));
```

### Any feature, by quarter, with direction

```js
const featPick = view(Inputs.select(new Map(feats.features.map((f) => [FEATURE_LABELS[f.name], f.name])), {label: "Feature", value: "feat_agentic_action"}));
const minN = view(Inputs.range([5, 60], {label: "Minimum posts per quarter", step: 5, value: 15}));
```

```js
const f = byName.get(featPick);
const dc = directionColors();
const qs = Object.keys(feats.quarter_n_unbiased).sort();
const ok = qs.map((q) => feats.quarter_n_unbiased[q] >= minN);
const start = ok.findIndex((_, i) => ok.slice(i).every(Boolean));
const rows = [];
for (const q of start < 0 ? [] : qs.slice(start)) {
  const n = feats.quarter_n_unbiased[q];
  for (const d of DIRS) rows.push({quarter: q, direction: d, share: (f.by_quarter_unbiased[q]?.[d] || 0) / n, count: f.by_quarter_unbiased[q]?.[d] || 0, n});
}
const quarters = [...new Set(rows.map((r) => r.quarter))].sort();
display(Plot.plot({
  width: Math.min(width, 900), height: 300, marginLeft: 50,
  x: {domain: quarters, label: null}, y: {label: "Share of posts in the quarter", tickFormat: ".0%", grid: true},
  color: {domain: DIRS, range: DIRS.map((d) => dc[d]), legend: true, tickFormat: (d) => DIRECTION_LABELS[d]},
  marks: [
    Plot.areaY(rows, {x: "quarter", y: "share", fill: "direction", order: DIRS, curve: "monotone-x", stroke: "var(--theme-background)", strokeWidth: 1, title: (d) => `${d.quarter} · ${DIRECTION_LABELS[d.direction]}: ${d.count} of ${d.n}`}),
    Plot.text(quarters.map((q) => ({quarter: q, n: rows.find((r) => r.quarter === q).n})), {x: "quarter", y: 0, dy: 14, text: (d) => d.n.toLocaleString(), fill: "var(--theme-foreground-muted)", fontSize: 10})
  ]
}));
```

<div class="caption">Stacked: the share of the quarter's posts pointing to the feature in each direction. The number under each quarter is how many posts it contains; quarters below the minimum at the start of the series are dropped so the series is unbroken.</div>

## What the citations look like

```js
const exFeat = view(Inputs.select(new Map(feats.features.map((f) => [FEATURE_LABELS[f.name], f.name])), {label: "Feature", value: "feat_agentic_action"}));
const exDir = view(Inputs.radio(new Map(DIRS.map((d) => [DIRECTION_LABELS[d], d])), {label: "Direction", value: "for"}));
```

```js
const ex = byName.get(exFeat).examples[exDir] || [];
display(html`<div class="quotes">${ex.length ? ex.map((e) => html`<blockquote><p>${e.quote}</p><footer><a href="${e.url}" target="_blank" rel="noopener">${e.title}</a> · ${e.publication} · ${e.date}</footer></blockquote>`) : html`<p class="muted">No posts coded this way yet.</p>`}</div>`);
```

<div class="caption">The coder's evidence excerpts for the most-reacted posts coded in this direction. Posts are linked, never reproduced.</div>
