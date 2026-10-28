---
title: Changes of mind
---

# Changes of mind

Most posts hold a position. A few report that the author's own view on machine minds has moved. This page lists them: every relevant post whose author says, in their own voice, that they once thought differently, with the passage that says so. The direction is whether the author now gives more or less credence to AI systems having experience, genuine cognition, agency or moral status. The bar is a stated earlier view and a stated present view, both about whether machines have minds, with the earlier one held before the post was written. A conversion that happens inside the post's own experiment or conversation does not count, nor does a present view with no earlier one ("I came to this reluctantly"), nor a change on a neighbouring matter: terminology, which argument is decisive, whether the question is worth asking.

Self-report is the measurement because the alternative does not work. Following each publication's coded positions from post to post finds almost no clean switches; most apparent flips are a change in what is being discussed, not a change of mind. A sentence that says "I used to think otherwise" is the evidence worth having, so the coder was asked to find that sentence. Posts are linked, never reproduced; the quotations are the coder's evidence excerpts.

```js
import {axesDiverging, axesTable, GROUP_LABELS, GROUP_ORDER, statRow} from "./components/charts.js";
const posts = await FileAttachment("./data/posts.json").json();
const DIRS = ["toward_minds", "away_from_minds"];
const DIR_LABELS = {toward_minds: "Toward minds", away_from_minds: "Away from minds"};
const DIR_LONG = {
  toward_minds: "now gives more credence to AI systems having experience, cognition, agency or moral status than before",
  away_from_minds: "now gives less credence than before"
};
const DIR_COLORS = {toward_minds: "var(--axis-yes)", away_from_minds: "var(--axis-no)"};
const revised = posts.filter((p) => DIRS.includes(p.view_revised));
const pct = (n, d) => (d ? `${(100 * n / d).toFixed(1)}%` : "");
```

```js
display(statRow([
  ["Posts reporting a change", revised.length.toLocaleString(), `${pct(revised.length, posts.length)} of ${posts.length.toLocaleString()} relevant posts`],
  ...DIRS.map((d) => {
    const n = revised.filter((p) => p.view_revised === d).length;
    return [DIR_LABELS[d], n.toLocaleString(), `${pct(n, revised.length)} of the changes`];
  })
]));
```

<div class="caption">Toward minds: the author ${DIR_LONG.toward_minds}. Away from minds: ${DIR_LONG.away_from_minds}. Changes reported for other people, a lab or a model are not counted, nor are hypotheticals or posts written in the voice of an AI persona.</div>

## By who is writing

```js
const byGroup = GROUP_ORDER.flatMap((g) => {
  const all = posts.filter((p) => p.group === g);
  return DIRS.map((d) => ({group: g, dir: d, n: all.filter((p) => p.view_revised === d).length, total: all.length}));
}).filter((r) => r.total > 0);
display(Plot.plot({
  width: Math.min(width, 760), height: 44 * GROUP_ORDER.length + 60, marginLeft: 170, marginRight: 90,
  x: {label: "Share of the type's relevant posts reporting a change", percent: true, grid: true, tickFormat: (d) => `${d}%`},
  y: {domain: GROUP_ORDER, tickFormat: (g) => GROUP_LABELS[g], label: null},
  color: {domain: DIRS, range: DIRS.map((d) => DIR_COLORS[d]), legend: true, tickFormat: (d) => DIR_LABELS[d]},
  marks: [
    Plot.barX(byGroup, {x: (r) => r.n / r.total, y: "group", fill: "dir", order: DIRS, inset: 0.5}),
    Plot.text(GROUP_ORDER.map((g) => byGroup.filter((r) => r.group === g)).filter((rs) => rs.length), {
      x: (rs) => rs.reduce((a, r) => a + r.n, 0) / rs[0].total, y: (rs) => rs[0].group,
      text: (rs) => `${rs.reduce((a, r) => a + r.n, 0)} of ${rs[0].total.toLocaleString()}`, dx: 6, textAnchor: "start", fill: "var(--theme-foreground-muted)", fontSize: 11
    }),
    Plot.tip(byGroup, Plot.pointer({x: (r) => r.n / r.total, y: "group", title: (r) => `${GROUP_LABELS[r.group]}\n${DIR_LABELS[r.dir]}: ${r.n} of ${r.total} posts (${pct(r.n, r.total)})`}))
  ]
}));
```

<div class="caption">Each bar is one publication type; its length is the share of that type's relevant posts whose author reports a change of mind, split by direction. Publication types are described on <a href="./methods">Methods</a>.</div>

## The posts

```js
const dir = view(Inputs.radio(new Map([["All changes", "all"], ...DIRS.map((d) => [DIR_LABELS[d], d])]), {label: "Direction", value: "all"}));
const group = view(Inputs.select(new Map([["All publication types", "all"], ...GROUP_ORDER.map((g) => [GROUP_LABELS[g], g])]), {label: "Publication type"}));
const order = view(Inputs.radio(new Map([["Newest first", "date"], ["Most reactions", "reactions"]]), {label: "Order", value: "date"}));
```

```js
const rows = revised
  .filter((p) => (dir === "all" || p.view_revised === dir) && (group === "all" || p.group === group))
  .sort((a, b) => (order === "date" ? (b.date || "").localeCompare(a.date || "") : (b.reactions ?? 0) - (a.reactions ?? 0) || (b.date || "").localeCompare(a.date || "")));
display(html`<p class="caption">${rows.length.toLocaleString()} posts. ${dir === "all" ? "" : `Their current answers to the six questions, where they address them: these are the positions the authors moved to, not from.`}</p>`);
if (dir !== "all" && rows.length) display(axesDiverging(axesTable(rows), {width: Math.min(width, 900)}));
```

```js
display(html`<div class="revisions">${rows.map((p) => html`<div class="revision">
  <div class="meta"><span class="pill dir" style="background:${DIR_COLORS[p.view_revised]}">${DIR_LABELS[p.view_revised]}</span> ${p.date} · <a href="./publication/${p.publication_id}">${p.publication || p.host}</a>${p.author ? ` · ${p.author}` : ""} · ${GROUP_LABELS[p.group] || ""}${p.reactions ? ` · ${p.reactions.toLocaleString()} reactions` : ""}</div>
  <div class="title"><a href="${p.url}" target="_blank" rel="noopener">${p.title || "(untitled)"}</a>${p.subtitle ? html`<span class="subtitle"> — ${p.subtitle}</span>` : ""}</div>
  ${p.view_revised_quote ? html`<blockquote>${p.view_revised_quote}</blockquote>` : ""}
</div>`)}</div>`);
```

<div class="caption">The direction and the quotation are machine-assigned: Claude read each relevant post against the codebook's definition and returned a value with the passage it relied on. Quotations are verbatim excerpts, at most a few sentences, shown as evidence for the code. A human check of a sample of these codes, and of posts coded as no change whose text contains a change-of-mind phrase, is described on <a href="./methods">Methods</a>. The construct is <code>view_revised</code> in the codebook, since version 0.3.0; version 0.3.1 tightened it after a read of every post the first version had flagged, which was admitting conversions staged within the post, present views with no stated earlier view, and changes on neighbouring questions. The posts the first version flagged were re-coded under the stricter rule.</div>
