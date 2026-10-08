---
title: Over time
---

# Over time

Volume over time cannot be read from this corpus: Substack's own search returns almost only recent posts, so the raw counts rise steeply toward the present. Composition can, if the recency-skewed channel is left out. The charts below use only posts found through web search or through citation from other posts.

```js
import * as Plot from "npm:@observablehq/plot";
import {vlChart, axisColors, LEVELS, LEVEL_LABELS, AXIS_LABELS} from "./components/charts.js";
const axes = await FileAttachment("./data/stance_axes.json").json();
const summary = await FileAttachment("./data/summary.json").json();
const timeSpec = await FileAttachment("./charts/axes_over_time.vl.json").json();
```

```js
display(await vlChart(timeSpec, {width: Math.min(width, 760) - 120}));
```

## Any question, by quarter

```js
const axis = view(Inputs.select(new Map(Object.entries(AXIS_LABELS).map(([k, v]) => [v, k])), {label: "Question", value: "experience_now"}));
const minN = view(Inputs.range([5, 60], {label: "Minimum posts per quarter", step: 5, value: 15}));
```

```js
const sc = axisColors();
// Start at the first quarter from which every later quarter clears the minimum, so the series is unbroken.
const qs = Object.keys(axes.by_quarter_unbiased).sort();
const nOf = (q) => LEVELS.reduce((a, k) => a + (axes.by_quarter_unbiased[q][axis][k] || 0), 0);
const ok = qs.map((q) => nOf(q) >= minN);
const start = ok.findIndex((_, i) => ok.slice(i).every(Boolean));
const rows = [];
for (const q of start < 0 ? [] : qs.slice(start)) {
  const c = axes.by_quarter_unbiased[q][axis], n = nOf(q);
  for (const k of LEVELS) rows.push({quarter: q, option: k, share: (c[k] || 0) / n, count: c[k] || 0, n});
}
const quarters = [...new Set(rows.map((r) => r.quarter))].sort();
display(Plot.plot({
  width: Math.min(width, 900), height: 320, marginLeft: 50,
  x: {domain: quarters, label: null}, y: {label: "Share of posts addressing the question", tickFormat: ".0%", percent: false, grid: true},
  color: {domain: LEVELS, range: LEVELS.map((k) => sc[k]), legend: true, tickFormat: (d) => LEVEL_LABELS[d]},
  marks: [
    Plot.areaY(rows, {x: "quarter", y: "share", fill: "option", order: LEVELS, offset: null, curve: "monotone-x", stroke: "var(--theme-background)", strokeWidth: 1, title: (d) => `${d.quarter} · ${LEVEL_LABELS[d.option]}: ${d.count} of ${d.n}`}),
    Plot.text(quarters.map((q) => ({quarter: q, n: rows.find((r) => r.quarter === q).n})), {x: "quarter", y: 0, dy: 14, text: (d) => d.n.toLocaleString(), fill: "var(--theme-foreground-muted)", fontSize: 10})
  ]
}));
```

## Posts per quarter by discovery channel

```js
const chRows = [];
for (const [q, n] of Object.entries(summary.by_quarter_all)) chRows.push({quarter: q, channel: "all channels", n});
for (const [q, n] of Object.entries(summary.by_quarter_unbiased)) chRows.push({quarter: q, channel: "web search and citation only", n});
chRows.sort((a, b) => a.quarter.localeCompare(b.quarter));   // ordinal x does not sort the line's points
display(Plot.plot({
  width: Math.min(width, 900), height: 260, marginLeft: 50,
  x: {domain: [...new Set(chRows.map((r) => r.quarter))].sort(), label: null}, y: {label: "Relevant posts", grid: true},
  color: {legend: true, range: ["var(--series-1)", "var(--series-2)"]},
  marks: [Plot.line(chRows, {x: "quarter", y: "n", stroke: "channel", curve: "monotone-x", strokeWidth: 2}), Plot.dot(chRows, {x: "quarter", y: "n", fill: "channel", r: 3, title: (d) => `${d.quarter}: ${d.n} (${d.channel})`})]
}));
```

<div class="caption">The gap between the lines is Substack's search channel, which only surfaces 2026 posts. Even the restricted series leans recent, because citation reaches recent posts more easily; treat it as composition, not volume.</div>
