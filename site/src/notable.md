---
title: Notable posts
---

# Notable posts

Two ways a post can stand out. It can do far better than its own publication usually does, which finds writing that travelled beyond its regular readers. Or it can draw more engagement than almost anything else in the corpus, which finds what the platform as a whole responded to. The two lists overlap less than you might expect. Posts are linked, never reproduced.

```js
import {GROUP_LABELS, GROUP_ORDER, groupColors, statRow} from "./components/charts.js";
const posts = await FileAttachment("./data/posts.json").json();
const METRICS = {reactions: "Reactions", restacks: "Restacks", comments: "Comments"};
const fmtRatio = (v) => (v == null ? "" : `${v >= 10 ? Math.round(v) : v.toFixed(1)}×`);
```

```js
const metric = view(Inputs.radio(new Map(Object.entries(METRICS).map(([k, v]) => [v, k])), {label: "Measure", value: "reactions"}));
const group = view(Inputs.select(new Map([["Any type", "all"], ...GROUP_ORDER.map((g) => [GROUP_LABELS[g], g])]), {label: "Publication type"}));
const minCount = view(Inputs.select(new Map([["10", 10], ["25", 25], ["50", 50], ["100", 100]]), {label: "Minimum count to appear in the first list", value: 10}));
const hideAi = view(Inputs.toggle({label: "Hide posts Substack flags as AI-written", value: true}));
```

```js
const eligible = posts.filter((p) => (group === "all" || p.group === group) && !(hideAi && p.ai_flag === 1));
const count = (p) => p[metric] ?? 0;
const norm = (p) => p.norm?.[metric];
const fmtRank = (p) => (p.norm?.n ? `${p.norm[metric].rank} of ${p.norm.n + 1}` : "");
const compared = eligible.filter((p) => norm(p)?.ratio != null);
const over = compared.filter((p) => count(p) >= minCount).sort((a, b) => norm(b).ratio - norm(a).ratio);
const top = eligible.slice().sort((a, b) => count(b) - count(a) || (b.reactions ?? 0) - (a.reactions ?? 0));
const ratios = compared.map((p) => norm(p).ratio).sort((a, b) => a - b);
const median = ratios.length ? ratios[Math.floor(ratios.length / 2)] : null;
const share = (f) => (compared.length ? `${Math.round(100 * compared.filter(f).length / compared.length)}%` : "");
```

```js
display(statRow([
  ["Posts compared", compared.length.toLocaleString(), "with a norm from ten or more other posts of their publication"],
  ["Beat their publication's norm", share((p) => norm(p).ratio > 1), `median post: ${fmtRatio(median)} the norm`],
  ["Doubled it", share((p) => norm(p).ratio >= 2), "twice the publication's typical post or more"],
  ["Ten times it", share((p) => norm(p).ratio >= 10), "the breakout posts"]
]));
```

<div class="caption">A publication's norm is the mean of its other newsletter and podcast posts dated 2024 or later, from its public archive, leaving the post itself out. Restacked Notes are excluded from the norm. Counts are as of the crawl (late September to early October 2026; posts added in the 2026-10-13 update carry counts from that date), so recent posts have had less time to accumulate them. Posts in publications with fewer than ten other posts have no norm and appear only in the second list.</div>

## Each post against its publication's norm

```js
const pts = compared.filter((p) => count(p) >= 1 && norm(p).baseline > 0);
const gc = groupColors();
const lo = Math.max(0.1, d3.min(pts, (p) => Math.min(norm(p).baseline, count(p))) || 0.1), hi = d3.max(pts, (p) => Math.max(norm(p).baseline, count(p))) || 10;
const refs = [1, 10].map((k) => ({k, x1: lo, y1: lo * k, x2: hi / k, y2: hi}));
display(Plot.plot({
  width: Math.min(width, 860), height: 460, marginLeft: 56, marginRight: 40,
  x: {type: "log", label: `Publication's typical post (${METRICS[metric].toLowerCase()})`, grid: true},
  y: {type: "log", label: `This post (${METRICS[metric].toLowerCase()})`, grid: true},
  color: {domain: GROUP_ORDER, range: GROUP_ORDER.map((g) => gc[g]), legend: true, tickFormat: (d) => GROUP_LABELS[d]},
  marks: [
    Plot.link(refs, {x1: "x1", y1: "y1", x2: "x2", y2: "y2", stroke: "var(--axis)", strokeDasharray: (d) => (d.k === 1 ? null : "4,4")}),
    Plot.text(refs, {x: "x2", y: "y2", text: (d) => `${d.k}× the norm`, dx: 6, dy: -4, textAnchor: "end", fill: "var(--theme-foreground-muted)", fontSize: 11}),
    Plot.dot(pts, {x: (p) => norm(p).baseline, y: count, fill: "group", r: 3, fillOpacity: 0.65, stroke: "var(--theme-background)", strokeWidth: 0.5, href: "url", target: "_blank"}),
    Plot.tip(pts, Plot.pointer({x: (p) => norm(p).baseline, y: count, title: (p) => `${p.title}\n${p.publication || p.host}\n${count(p).toLocaleString()} ${METRICS[metric].toLowerCase()}, norm ${norm(p).baseline.toLocaleString()} (${fmtRatio(norm(p).ratio)}), rank ${fmtRank(p)}`}))
  ]
}));
```

<div class="caption">One dot per relevant post with at least one ${METRICS[metric].toLowerCase()}; both axes are logarithmic. Dots on the solid line match their publication's typical post; dots above the dashed line did ten times better. Click a dot to open the post.</div>

## Posts that beat their publication's norm

```js
const overRows = over.slice(0, 100).map((p) => ({date: p.date, title: p.title, publication: p.publication || p.host, type: GROUP_LABELS[p.group] || "", count: count(p), baseline: norm(p).baseline, ratio: norm(p).ratio, rank: fmtRank(p), url: p.url, publication_id: p.publication_id}));
display(html`<p class="caption">${over.length.toLocaleString()} posts with at least ${minCount} ${METRICS[metric].toLowerCase()} and a norm; the top ${Math.min(100, over.length)} by ratio.</p>`);
display(Inputs.table(overRows, {
  columns: ["date", "title", "publication", "count", "baseline", "ratio", "rank"],
  header: {date: "Date", title: "Post", publication: "Publication", type: "Type", count: METRICS[metric], baseline: "Publication's typical", ratio: "× the norm", rank: "Rank in publication"},
  width: {date: 84, title: 250, publication: 150, count: 72, baseline: 72, ratio: 64, rank: 80}, select: false, rows: 25, sort: "ratio", reverse: true,
  format: {title: (v, i, d) => html`<a href="${d[i].url}" target="_blank" rel="noopener">${v}</a>`, publication: (v, i, d) => html`<a href="./publication/${d[i].publication_id}">${v}</a>`, ratio: fmtRatio, baseline: (v) => v.toLocaleString()}
}));
```

## Most engagement overall

```js
const topRows = top.slice(0, 100).map((p) => ({date: p.date, title: p.title, publication: p.publication || p.host, type: GROUP_LABELS[p.group] || "", reactions: p.reactions, restacks: p.restacks, comments: p.comments, ratio: norm(p)?.ratio, rank: fmtRank(p), url: p.url, publication_id: p.publication_id}));
display(html`<p class="caption">The top ${Math.min(100, top.length)} of ${eligible.length.toLocaleString()} posts by ${METRICS[metric].toLowerCase()}. The ratio column shows how each compares with its own publication's norm, where one exists.</p>`);
display(Inputs.table(topRows, {
  columns: ["date", "title", "publication", "reactions", "restacks", "comments", "ratio", "rank"],
  header: {date: "Date", title: "Post", publication: "Publication", type: "Type", reactions: "Reactions", restacks: "Restacks", comments: "Comments", ratio: "× the norm", rank: "Rank in publication"},
  width: {date: 84, title: 230, publication: 140, reactions: 64, restacks: 64, comments: 64, ratio: 64, rank: 80}, select: false, rows: 25, sort: metric, reverse: true,
  format: {title: (v, i, d) => html`<a href="${d[i].url}" target="_blank" rel="noopener">${v}</a>`, publication: (v, i, d) => html`<a href="./publication/${d[i].publication_id}">${v}</a>`, ratio: fmtRatio}
}));
```

<div class="caption">Reactions, restacks and comments are Substack's public counts. They favour large publications and older posts, which is why the first list exists. Whether a post is relevant, and its codes, are machine-assigned with human spot checks; see <a href="./methods">Methods</a>.</div>
