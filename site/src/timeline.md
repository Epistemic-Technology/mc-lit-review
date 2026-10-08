---
title: Over time
---

# Over time

Volume over time cannot be read from this corpus: Substack's own search returns almost only recent posts, so the raw counts rise steeply toward the present. Composition can, if the recency-skewed channel is left out. The charts below use only posts found through web search or through citation from other posts.

```js
import * as Plot from "npm:@observablehq/plot";
import {vlChart, stanceColors, STANCE_LABELS, ITEM_LABELS} from "./components/charts.js";
const stance = await FileAttachment("./data/stance.json").json();
const summary = await FileAttachment("./data/summary.json").json();
const timeSpec = await FileAttachment("./charts/stance_over_time.vl.json").json();
```

```js
display(await vlChart(timeSpec, {width: Math.min(width, 760) - 120}));
```

## Any claim, by quarter

```js
const item = view(Inputs.select(new Map(Object.entries(ITEM_LABELS).map(([k, v]) => [v, k])), {label: "Claim", value: "current_conscious"}));
const minN = view(Inputs.range([5, 60], {label: "Minimum posts per quarter", step: 5, value: 15}));
```

```js
const sc = stanceColors();
const opts = ["denies", "agnostic", "discusses", "asserts"];
const rows = [];
for (const [q, table] of Object.entries(stance.by_quarter_unbiased)) {
  const c = table[item]; const n = opts.reduce((a, k) => a + (c[k] || 0), 0);
  if (n < minN) continue;
  for (const k of opts) rows.push({quarter: q, option: k, share: (c[k] || 0) / n, count: c[k] || 0, n});
}
const quarters = [...new Set(rows.map((r) => r.quarter))].sort();
display(Plot.plot({
  width: Math.min(width, 900), height: 320, marginLeft: 50,
  x: {domain: quarters, label: null}, y: {label: "Share of posts addressing the claim", tickFormat: ".0%", percent: false, grid: true},
  color: {domain: opts, range: opts.map((k) => sc[k]), legend: true, tickFormat: (d) => STANCE_LABELS[d]},
  marks: [
    Plot.areaY(rows, {x: "quarter", y: "share", fill: "option", order: opts, offset: null, curve: "monotone-x", stroke: "var(--theme-background)", strokeWidth: 1, title: (d) => `${d.quarter} · ${STANCE_LABELS[d.option]}: ${d.count} of ${d.n}`}),
    Plot.text([...new Set(rows.map((r) => r.quarter))].map((q) => ({quarter: q, n: rows.find((r) => r.quarter === q).n})), {x: "quarter", y: 0, dy: 14, text: (d) => d.n.toLocaleString(), fill: "var(--theme-foreground-muted)", fontSize: 10})
  ]
}));
```

## Posts per quarter by discovery channel

```js
const chRows = [];
for (const [q, n] of Object.entries(summary.by_quarter_all)) chRows.push({quarter: q, channel: "all channels", n});
for (const [q, n] of Object.entries(summary.by_quarter_unbiased)) chRows.push({quarter: q, channel: "web search and citation only", n});
display(Plot.plot({
  width: Math.min(width, 900), height: 260, marginLeft: 50,
  x: {domain: [...new Set(chRows.map((r) => r.quarter))].sort(), label: null}, y: {label: "Relevant posts", grid: true},
  color: {legend: true, range: ["var(--series-1)", "var(--series-2)"]},
  marks: [Plot.line(chRows, {x: "quarter", y: "n", stroke: "channel", curve: "monotone-x", strokeWidth: 2}), Plot.dot(chRows, {x: "quarter", y: "n", fill: "channel", r: 3, title: (d) => `${d.quarter}: ${d.n} (${d.channel})`})]
}));
```

<div class="caption">The gap between the lines is Substack's search channel, which only surfaces 2026 posts. Even the restricted series leans recent, because citation reaches recent posts more easily; treat it as composition, not volume.</div>
