---
title: Topic map
---

# Topic map

Every relevant post, placed by the similarity of its text and coloured by cluster. Hover a dot for the title; click to open the post. Clusters were found by HDBSCAN on sentence embeddings and labelled by hand after a model's suggestion.

```js
import * as Plot from "npm:@observablehq/plot";
import {GROUP_LABELS, GROUP_ORDER, STANCE_LABELS, groupColors, stanceColors} from "./components/charts.js";
const posts = await FileAttachment("./data/posts.json").json();
const topics = await FileAttachment("./data/topics.json").json();
```

```js
const colorBy = view(Inputs.radio(new Map([["Topic cluster", "cluster"], ["Publication type", "group"], ["Position on current consciousness", "stance"]]), {label: "Colour by", value: "cluster"}));
const onlyCore = view(Inputs.toggle({label: "Core cluster members only", value: false}));
const pick = view(Inputs.select(new Map([["All clusters", null], ...topics.map((t) => [`${t.label} (${t.size})`, t.cluster])]), {label: "Highlight cluster"}));
```

```js
const laid = posts.filter((p) => p.x != null && (!onlyCore || p.cluster_core));
const labelOf = new Map(topics.map((t) => [t.cluster, t.label]));
const gc = groupColors(), sc = stanceColors();
const palette = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"];
const clusterColor = (c) => palette[((c % palette.length) + palette.length) % palette.length];
let fill, legend = null;
if (colorBy === "group") { fill = (d) => gc[d.group]; legend = GROUP_ORDER.map((g) => [GROUP_LABELS[g], gc[g]]); }
else if (colorBy === "stance") { fill = (d) => sc[d.stance.current_conscious] || "var(--theme-foreground-faintest)"; legend = ["asserts", "agnostic", "discusses", "denies"].map((k) => [STANCE_LABELS[k], sc[k]]); }
else { fill = (d) => clusterColor(d.cluster); }
const dim = (d) => pick == null || d.cluster === pick;
const labelN = view(Inputs.range([0, topics.length], {label: "Label the largest N clusters", step: 1, value: 12}));
const centroids = topics.filter((t) => t.centroid).slice(0, labelN).map((t) => ({x: t.centroid[0], y: t.centroid[1], label: t.label, cluster: t.cluster}));
display(Plot.plot({
  width: Math.min(width, 960), height: Math.min(width, 960) * 0.75, inset: 20, aspectRatio: 1,
  x: {axis: null}, y: {axis: null},
  marks: [
    Plot.dot(laid, {x: "x", y: "y", r: 3.2, fill, fillOpacity: (d) => (dim(d) ? 0.75 : 0.12), stroke: "var(--theme-background)", strokeWidth: 0.8,
      href: "url", target: "_blank", title: (d) => `${d.title}\n${d.publication || d.host} · ${d.date}\n${labelOf.get(d.cluster) || ""}`}),
    Plot.text(centroids.filter((c) => pick == null || c.cluster === pick), {x: "x", y: "y", text: "label", fontSize: 11, fontWeight: 600, fill: "var(--theme-foreground)", stroke: "var(--theme-background)", strokeWidth: 4, paintOrder: "stroke"})
  ]
}));
if (legend) display(html`<div class="caption">${legend.map(([l, c]) => html`<span class="pill"><span class="swatch" style="background:${c}"></span>${l}</span>`)}</div>`);
```

<div class="caption">Colouring by cluster cycles eight hues across 33 clusters, so neighbouring clusters can share a colour; use the highlight control or hover to disambiguate. Peripheral posts are those HDBSCAN did not assign and were attached to the nearest cluster.</div>

## The clusters

```js
const sc2 = stanceColors();
display(Inputs.table(topics.map((t) => ({
  label: t.label, size: t.size, core: t.core_size, description: t.description,
  deny: t.stance_current_conscious.denies || 0, assert: t.stance_current_conscious.asserts || 0,
  group: Object.entries(t.groups).sort((a, b) => b[1] - a[1])[0]?.[0], terms: t.terms.slice(0, 8).join(", ")
})), {
  columns: ["label", "size", "core", "deny", "assert", "group", "description", "terms"],
  header: {label: "Topic", size: "Posts", core: "Core", deny: "Deny", assert: "Assert", group: "Main type", description: "Description", terms: "Distinctive terms"},
  width: {label: 240, description: 320, terms: 260}, select: false, rows: 40,
  format: {group: (g) => GROUP_LABELS[g] || g}
}));
```
