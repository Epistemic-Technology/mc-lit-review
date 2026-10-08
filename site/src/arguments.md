---
title: Arguments and sources
---

# Arguments and sources

```js
import {vlChart, ARG_LABELS, GROUP_LABELS, GROUP_ORDER, groupColors} from "./components/charts.js";
import * as Plot from "npm:@observablehq/plot";
const args = await FileAttachment("./data/arguments.json").json();
const sources = await FileAttachment("./data/sources.json").json();
const argSpec = await FileAttachment("./charts/arguments_traction.vl.json").json();
const citedSpec = await FileAttachment("./charts/top_cited_works.vl.json").json();
const peopleSpec = await FileAttachment("./charts/people_named.vl.json").json();
```

## Which arguments appear, and which get traction

```js
display(await vlChart(argSpec));
```

<div class="caption">Thirteen argument types coded present or absent per post. Traction is the median of each post's reactions divided by its publication's average reactions over the period, so a value of 1.0 means a typical post for that publication.</div>

## Arguments by publication type

```js
const rows = [];
for (const a of args) for (const g of GROUP_ORDER) rows.push({argument: ARG_LABELS[a.name] || a.name, group: g, share: a.group_share[g] || 0, n: a.by_group[g] || 0});
const order = args.slice().sort((a, b) => b.share - a.share).map((a) => ARG_LABELS[a.name] || a.name);
const gc = groupColors();
display(Plot.plot({
  width: Math.min(width, 900), height: 30 * order.length + 60, marginLeft: 250,
  x: {label: "Share of the type's relevant posts using the argument", tickFormat: ".0%", grid: true},
  y: {domain: order, label: null},
  color: {domain: GROUP_ORDER, range: GROUP_ORDER.map((g) => gc[g]), legend: true, tickFormat: (g) => GROUP_LABELS[g]},
  marks: [
    Plot.dot(rows, {x: "share", y: "argument", fill: "group", r: 5, stroke: "var(--theme-background)", strokeWidth: 2, title: (d) => `${d.argument}\n${GROUP_LABELS[d.group]}: ${d.n} posts (${Math.round(d.share * 100)}%)`}),
    Plot.ruleX([0])
  ]
}));
```

## What the discourse cites

```js
display(await vlChart(citedSpec));
```

```js
const tiers = Object.entries(sources.tiers).map(([t, v]) => ({tier: t, posts: v.posts_citing, works: v.works})).sort((a, b) => b.posts - a.posts);
display(Inputs.table(tiers, {columns: ["tier", "posts", "works"], header: {tier: "Source tier", posts: "Relevant posts citing it", works: "Distinct works"}, select: false, rows: 12}));
```

<div class="caption">Tiers are assigned by reference kind (arXiv and DOI are academic, Amazon ASINs are books, Wikipedia is encyclopedia, Substack posts are Substack) and then by domain list; images, link shorteners and platform pages are dropped. The full mapping is in <code>config/domain_tiers.yaml</code>.</div>

### Top works by tier

```js
const tierPick = view(Inputs.select(Object.keys(sources.top_works_by_tier), {label: "Tier", value: "academic"}));
```

```js
display(Inputs.table(sources.top_works_by_tier[tierPick].map((w) => ({work: w.title || w.url, publications: w.citing_pubs, posts: w.citing_posts, url: w.url})), {
  columns: ["work", "publications", "posts"], header: {work: "Work", publications: "Citing publications", posts: "Citing posts"}, width: {work: 520}, select: false, rows: 25,
  format: {work: (v, i, data) => html`<a href="${data[i].url}" target="_blank" rel="noopener">${v}</a>`}
}));
```

## Who gets named

```js
display(await vlChart(peopleSpec));
```

<div class="caption">Counted by regular expression over post text; a post counts once per person. Surnames alone are used only where unambiguous. The list is in <code>config/names.yaml</code>.</div>
