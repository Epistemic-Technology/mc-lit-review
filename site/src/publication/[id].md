---
title: Publication
---

```js
import {axesDiverging, axesTable, statRow, GROUP_LABELS, LEVEL_LABELS, GENRE_LABELS, ARG_LABELS} from "../components/charts.js";
const slice = await FileAttachment(`../data/pub/${observable.params.id}.json`).json();
const pub = slice.publication, node = slice.node;
const mine = slice.posts.slice().sort((a, b) => (b.date || "").localeCompare(a.date || ""));
```

```js
display(html`<h1>${pub.name || pub.host}</h1>
<p class="caption"><a href="https://${pub.host}" target="_blank" rel="noopener">${pub.host}</a>${pub.author ? ` · ${pub.author}` : ""}${pub.tagline ? ` · ${pub.tagline}` : ""}</p>`);
```

```js
display(statRow([
  ["Relevant posts", String(pub.relevant_posts ?? 0), pub.posts_in_window ? `of ${pub.posts_in_window.toLocaleString()} posts since 2024 (${Math.round(100 * pub.relevant_share)}%)` : ""],
  ["Publication type", GROUP_LABELS[pub.group] || "untyped", pub.community ? `fine label: ${pub.community}` : ""],
  ["Cited by", String(node?.in_pubs ?? 0), "other publications, on relevant posts"],
  ["Cites", String(node?.out_pubs ?? 0), "other publications"],
  ["Main topic", pub.top_cluster || "", ""]
]));
```

## Positions taken here

```js
display(mine.length >= 3 ? axesDiverging(axesTable(mine), {width: Math.min(width, 860)}) : html`<p class="caption">Too few posts for a position profile; see the table below.</p>`);
```

<div class="caption">The six questions combine the coded claims; see <a href="../positions">Positions</a> for the definitions.</div>

## Relevant posts

```js
const lv = (v) => (v && v !== "not_addressed" ? LEVEL_LABELS[v] : "");
display(Inputs.table(mine.map((p) => ({date: p.date, title: p.title, genre: GENRE_LABELS[p.genre] || p.genre, experience: lv(p.axes.experience_now), cognition: lv(p.axes.cognition_now), moral: lv(p.axes.moral_status), arguments: p.arguments.map((a) => ARG_LABELS[a] || a).join("; "), topic: p.cluster_label || "", reactions: p.reactions, over: p.over_performance, url: p.url})), {
  columns: ["date", "title", "genre", "experience", "cognition", "moral", "topic", "arguments", "reactions", "over"],
  header: {date: "Date", title: "Post", genre: "Genre", experience: "Experience now?", cognition: "Thinks now?", moral: "Moral status?", topic: "Topic", arguments: "Arguments", reactions: "Reactions", over: "× the norm"},
  width: {title: 300, arguments: 260, topic: 200}, layout: "auto", select: false, rows: 30,
  format: {title: (v, i, d) => html`<a href="${d[i].url}" target="_blank" rel="noopener">${v}</a>`, over: (v) => (v == null ? "" : `${v >= 10 ? Math.round(v) : v.toFixed(1)}×`)}
}));
```

<div class="caption">"× the norm" compares a post's reactions with the mean of this publication's other newsletter and podcast posts since 2024${pub.norm_posts ? ` (${pub.norm_posts.toLocaleString()} posts, mean ${pub.baseline_reactions} reactions)` : ""}; blank when the publication has fewer than ten other posts. See <a href="../notable">Notable posts</a>.</div>

## Cited by and cites

```js
display(html`<div class="grid grid-cols-2">
  <div><h3>Cited by</h3>${slice.cited_by.length ? html`<ul>${slice.cited_by.slice(0, 25).map((e) => html`<li><a href="./${e.id}">${e.name}</a> <span class="caption">(${e.weight})</span></li>`)}</ul>` : html`<p class="caption">No incoming links from other publications' relevant posts.</p>`}</div>
  <div><h3>Cites</h3>${slice.cites.length ? html`<ul>${slice.cites.slice(0, 25).map((e) => html`<li><a href="./${e.id}">${e.name}</a> <span class="caption">(${e.weight})</span></li>`)}</ul>` : html`<p class="caption">No outgoing links to other publications.</p>`}</div>
</div>`);
```

<div class="caption">Codes are machine-assigned (Claude, with a Jev first pass) and spot-checked by a human; see <a href="../methods">Methods</a>. If a code for one of your posts looks wrong, the post is linked above so a reader can judge.</div>
