---
title: Topic map
---

# Topic map

Every relevant post, placed by the similarity of its text and coloured by cluster. Hover a dot for the title; click to open the post. Zoom in to see more cluster labels and, further in, the titles of individual posts. Clusters were found by HDBSCAN on sentence embeddings and labelled by hand after a model's suggestion.

```js
import * as d3 from "npm:d3";
import {GROUP_LABELS, GROUP_ORDER, LEVEL_LABELS, groupColors, axisColors} from "./components/charts.js";
const posts = await FileAttachment("./data/posts.json").json();
const topics = await FileAttachment("./data/topics.json").json();
```

```js
const colorBy = view(Inputs.radio(new Map([["Topic cluster", "cluster"], ["Publication type", "group"], ["Current LLMs have experience", "experience_now"], ["Current LLMs genuinely think", "cognition_now"], ["Current LLMs have goals of their own", "agency_now"]]), {label: "Colour by", value: "cluster"}));
const onlyCore = view(Inputs.toggle({label: "Core cluster members only", value: false}));
const pick = view(Inputs.select(new Map([["All clusters", null], ...topics.map((t) => [`${t.label} (${t.size})`, t.cluster])]), {label: "Highlight cluster"}));
const labelN = view(Inputs.range([0, topics.length], {label: "Cluster labels when zoomed out", step: 1, value: 12}));
```

```js
// Survives redraws (no dependency on the controls): the current zoom.
const viewState = {transform: null};
```

```js
// Cluster colours, assigned like a map: fourteen hues for 33 clusters, so some repeat, but never on clusters whose
// centroids are Delaunay neighbours, and each repeat goes to the cluster farthest from the colour's other uses.
// Largest clusters are coloured first. Deterministic, so a cluster keeps its colour across redraws and filters.
const palette = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948",
                 "#0e9aa7", "#8c5a2b", "#7c8a16", "#62b3e8", "#b33fb0", "#5f7a99"];
const clusterColorIndex = (() => {
  const cents = topics.filter((t) => t.centroid).sort((a, b) => b.size - a.size);
  const del = d3.Delaunay.from(cents, (c) => c.centroid[0], (c) => c.centroid[1]);
  const idx = new Map();
  cents.forEach((c, i) => {
    const taken = new Set([...del.neighbors(i)].map((j) => idx.get(cents[j].cluster)).filter((v) => v != null));
    let best = -1, bestScore = -1;
    palette.forEach((_, ci) => {
      if (taken.has(ci)) return;
      const score = Math.min(Infinity, ...cents.filter((o) => idx.get(o.cluster) === ci).map((o) => Math.hypot(o.centroid[0] - c.centroid[0], o.centroid[1] - c.centroid[1])));
      if (score > bestScore) { bestScore = score; best = ci; }
    });
    idx.set(c.cluster, best < 0 ? i % palette.length : best);
  });
  return idx;
})();
```

```js
const laid = posts.filter((p) => p.x != null && (!onlyCore || p.cluster_core));
const labelOf = new Map(topics.map((t) => [t.cluster, t.label]));
const gc = groupColors(), sc = axisColors();
const clusterColor = (c) => (clusterColorIndex.has(c) ? palette[clusterColorIndex.get(c)] : "var(--theme-foreground-faintest)");
let fill, legend = null;
if (colorBy === "group") { fill = (d) => gc[d.group]; legend = GROUP_ORDER.map((g) => [GROUP_LABELS[g], gc[g]]); }
else if (colorBy.endsWith("_now")) { fill = (d) => sc[d.axes[colorBy]] || "var(--theme-foreground-faintest)"; legend = ["yes", "yes_qualified", "unsure", "discussed", "no"].map((k) => [LEVEL_LABELS[k], sc[k]]); }
else { fill = (d) => clusterColor(d.cluster); }
const lit = (d) => pick == null || d.cluster === pick;
// One scale for both axes so the embedding's aspect ratio is kept, centred in the frame. The extent is over
// every placed post, not the filtered set, so filtering does not shift the dots under the current zoom.
const W = Math.min(width, 960), H = Math.round(W * 0.75), inset = 24;
const [x0, x1] = d3.extent(posts, (d) => d.x), [y0, y1] = d3.extent(posts, (d) => d.y);
const s = Math.min((W - 2 * inset) / (x1 - x0), (H - 2 * inset) / (y1 - y0));
const px = (x) => (W - s * (x1 - x0)) / 2 + s * (x - x0), py = (y) => (H + s * (y1 - y0)) / 2 - s * (y - y0);
// Dots are drawn on a canvas (one pass over 2,800 arcs per frame); only the labels actually shown live in an
// SVG overlay on top of it. Redrawing the whole thing as SVG was far too slow to zoom.
const dpr = window.devicePixelRatio || 1;
const css = (name, fallback) => getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
const surface = css("--theme-background", "#ffffff");
const faint = css("--theme-foreground-faintest", "#e1e0d9");
const frame = d3.create("div").style("position", "relative").style("width", `${W}px`).style("height", `${H}px`).style("max-width", "100%")
  .style("border", "1px solid var(--theme-foreground-faintest)").style("border-radius", "8px").style("overflow", "hidden").style("cursor", "grab")
  .style("font", "11px system-ui, sans-serif").style("touch-action", "none");
const canvas = frame.append("canvas").attr("width", Math.round(W * dpr)).attr("height", Math.round(H * dpr)).style("width", "100%").style("height", "100%").style("display", "block");
const ctx = canvas.node().getContext("2d");
const overlay = frame.append("svg").attr("viewBox", [0, 0, W, H]).style("position", "absolute").style("inset", 0).style("width", "100%").style("height", "100%").style("pointer-events", "none");
const tip = frame.append("div").style("position", "absolute").style("display", "none").style("pointer-events", "none").style("max-width", "320px").style("padding", "4px 8px")
  .style("background", "var(--theme-background-alt)").style("color", "var(--theme-foreground)").style("border", "1px solid var(--theme-foreground-faint)").style("border-radius", "4px").style("white-space", "pre-line").style("z-index", 2);
const R = 3.2;
// Per-dot base coordinates and colours, resolved once (the canvas cannot read CSS variables).
const pts = laid.map((d) => { const f = fill(d); return {d, x: px(d.x), y: py(d.y), color: f.startsWith("var(") ? faint : f, lit: lit(d)}; });
const dimmed = pts.filter((p) => !p.lit), bright = pts.filter((p) => p.lit);
const finder = d3.Delaunay.from(pts, (p) => p.x, (p) => p.y);
function draw(t) {
  const k = t.k, r = R / Math.pow(k, 0.7);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, W, H);
  ctx.translate(t.x, t.y); ctx.scale(k, k);
  ctx.lineWidth = 0.8 / k; ctx.strokeStyle = surface;
  for (const [group, alpha] of [[dimmed, 0.12], [bright, 0.75]]) {   // dimmed first so highlighted dots sit on top
    ctx.globalAlpha = alpha;
    for (const p of group) { ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, 2 * Math.PI); ctx.fillStyle = p.color; ctx.fill(); ctx.stroke(); }
  }
  ctx.globalAlpha = 1;
}
// Post titles: hidden when zoomed out, revealed by zoom level (see relabel). Ranked by reactions so the
// most-read posts in a region are named first. Links to the post, like the dots.
const byReactions = pts.slice().sort((a, b) => (b.d.reactions || 0) - (a.d.reactions || 0));
const titleLayer = overlay.append("g").attr("stroke", "var(--theme-background)").attr("stroke-width", 3).attr("paint-order", "stroke").attr("font-size", 10);
// Cluster labels at the centroids, ranked by cluster size.
const centroids = topics.filter((t) => t.centroid).map((t) => ({x: px(t.centroid[0]), y: py(t.centroid[1]), label: t.label, cluster: t.cluster, size: t.size})).sort((a, b) => b.size - a.size);
const clusterLayer = overlay.append("g").attr("text-anchor", "middle").attr("font-weight", 600).attr("font-size", 12).attr("fill", "var(--theme-foreground)").attr("stroke", "var(--theme-background)").attr("stroke-width", 4).attr("paint-order", "stroke");
// Level of detail at zoom k. Cluster labels: up to N*k^2 of the largest clusters whose centroid is in view,
// so the ones hidden at full view appear as you zoom in. Post titles: none below 2.5x; from there, at most
// MAX_TITLES posts in view, taken in order of reactions. Every label is placed only where it does not overlap
// one already placed (cluster labels first), so the most-read posts in view are named at each zoom level.
// The overlay is not transformed: labels are positioned in screen space, so text keeps its size.
const MAX_TITLES = 30;
function relabel(t) {
  const k = t.k, r = R / Math.pow(k, 0.7) * k;   // dot radius on screen
  const placed = [];   // screen-space boxes of labels already placed: [x0, y0, x1, y1]
  const fits = (box) => !placed.some((b) => box[0] < b[2] && box[2] > b[0] && box[1] < b[3] && box[3] > b[1]);
  const inView = (vx, vy) => vx >= -20 && vx <= W + 20 && vy >= -20 && vy <= H + 20;
  const cl = [];
  for (const c of centroids) {
    if (cl.length >= Math.round(labelN * k * k) || (pick != null && c.cluster !== pick)) continue;
    const vx = t.applyX(c.x), vy = t.applyY(c.y), half = 3.4 * c.label.length;
    if (!inView(vx, vy)) continue;
    const box = [vx - half, vy - 8, vx + half, vy + 8];
    if (fits(box)) { placed.push(box); cl.push({...c, vx, vy}); }
  }
  clusterLayer.selectAll("text").data(cl, (c) => c.cluster).join("text").attr("x", (c) => c.vx).attr("y", (c) => c.vy + 4).text((c) => c.label);
  const chosen = [];
  if (k >= 2.5) {
    for (const p of byReactions) {
      if (chosen.length >= MAX_TITLES) break;
      if (!p.lit) continue;
      const vx = t.applyX(p.x), vy = t.applyY(p.y);
      if (!inView(vx, vy)) continue;
      const box = [vx + r + 2, vy - 6, vx + r + 2 + 5.3 * Math.min(p.d.title.length, 60), vy + 7];
      if (fits(box)) { placed.push(box); chosen.push({p, vx: vx + r + 2, vy: vy + 3.5}); }
    }
  }
  titleLayer.selectAll("a").data(chosen, (c) => c.p.d.id).join((enter) => enter.append("a").attr("class", "netlabel").attr("target", "_blank").attr("rel", "noopener").style("pointer-events", "auto")
      .call((a) => a.append("text").attr("fill", "var(--theme-foreground-focus)").text((c) => (c.p.d.title.length > 60 ? c.p.d.title.slice(0, 58) + "…" : c.p.d.title))))
    .attr("href", (c) => c.p.d.url).select("text").attr("x", (c) => c.vx).attr("y", (c) => c.vy);
}
// One redraw per animation frame however many zoom events arrive.
let current = d3.zoomIdentity, pending = false;
function render(t) {
  current = t; viewState.transform = t;
  if (pending) return;
  pending = true;
  requestAnimationFrame(() => { pending = false; draw(current); relabel(current); });
}
// Hover shows the post; a click (not a drag) opens it. Hit-testing is by nearest dot within its radius.
function dotAt(ev) {
  const [mx, my] = d3.pointer(ev, canvas.node());
  const p = pts[finder.find(current.invertX(mx), current.invertY(my))];
  if (!p) return null;
  const r = R / Math.pow(current.k, 0.7) * current.k;
  return Math.hypot(current.applyX(p.x) - mx, current.applyY(p.y) - my) <= r + 2 ? p : null;
}
frame.on("mousemove", (ev) => {
  const p = dotAt(ev);
  frame.style("cursor", p ? "pointer" : "grab");
  if (!p) return tip.style("display", "none");
  const [mx, my] = d3.pointer(ev, frame.node());
  tip.style("display", null).style("left", `${mx + 12}px`).style("top", `${my + 12}px`).text(`${p.d.title}\n${p.d.publication || p.d.host} · ${p.d.date}\n${labelOf.get(p.d.cluster) || ""}`);
}).on("mouseleave", () => tip.style("display", "none"))
  .on("click", (ev) => { const p = dotAt(ev); if (p) window.open(p.d.url, "_blank", "noopener"); });
// Wheel or pinch to zoom, drag to pan, double-click to reset.
const zoom = d3.zoom().scaleExtent([1, 40]).translateExtent([[-W / 4, -H / 4], [W * 1.25, H * 1.25]]).on("zoom", (ev) => render(ev.transform));
frame.call(zoom).on("dblclick.zoom", () => frame.transition().duration(300).call(zoom.transform, d3.zoomIdentity));
// Restore the previous zoom after a redraw (colour, filter or label-count change), else start at full view.
frame.call(zoom.transform, viewState.transform || d3.zoomIdentity);
display(frame.node());
display(html`<p class="caption">Scroll or pinch to zoom, drag to pan, double-click to reset. Zooming in reveals the smaller clusters' labels, then (from about 2.5× in) the titles of the thirty most-read posts in view, so zooming further names smaller and smaller neighbourhoods. Click a dot or a title to open the post.</p>`);
if (legend) display(html`<div class="caption">${legend.map(([l, c]) => html`<span class="pill"><span class="swatch" style="background:${c}"></span>${l}</span>`)}</div>`);
```

<div class="caption">Colouring by cluster uses fourteen hues across 33 clusters, assigned so that neighbouring clusters never share one; a repeated hue marks clusters far apart on the map. Use the highlight control or hover to confirm a cluster. Peripheral posts are those HDBSCAN did not assign and were attached to the nearest cluster.</div>

## The clusters

```js
display(Inputs.table(topics.map((t) => ({
  label: t.label, size: t.size, core: t.core_size, description: t.description,
  deny: t.axes_experience_now.no || 0, assert: (t.axes_experience_now.yes || 0), think: (t.axes_cognition_now.yes || 0) + (t.axes_cognition_now.yes_qualified || 0), goals: t.axes_agency_now.yes || 0,
  group: Object.entries(t.groups).sort((a, b) => b[1] - a[1])[0]?.[0], terms: t.terms.slice(0, 8).join(", ")
})), {
  columns: ["label", "size", "core", "deny", "assert", "think", "goals", "group", "description", "terms"],
  header: {label: "Topic", size: "Posts", core: "Core", deny: "No experience", assert: "Has experience", think: "Thinks", goals: "Own goals", group: "Main type", description: "Description", terms: "Distinctive terms"},
  width: {label: 240, description: 320, terms: 260}, select: false, rows: 40,
  format: {group: (g) => GROUP_LABELS[g] || g}
}));
```
