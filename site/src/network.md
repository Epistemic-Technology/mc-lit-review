---
title: Citation network
---

# Citation network

Which publications cite which. An edge means at least one post in the source publication links to a post in the target; links between a publication's own posts are ignored. The backbone keeps edges that are statistically significant for at least one of their endpoints (disparity filter, α = 0.05), which is what makes the graph legible.

```js
import * as d3 from "npm:d3";
import {GROUP_LABELS, GROUP_ORDER, AXIS_LABELS, LEVEL_LABELS, groupColors, axisColors, escapeHtml} from "./components/charts.js";
const net = await FileAttachment("./data/network.json").json();
```

```js
const minIn = view(Inputs.range([0, 20], {label: "Minimum citing publications", step: 1, value: 2}));
const onlyTyped = view(Inputs.toggle({label: "Only publications with relevant posts", value: true}));
const labelTop = view(Inputs.range([0, 80], {label: "Labels in view (top N by citations)", step: 5, value: 20}));
const minWeight = view(Inputs.range([1, 10], {label: "Minimum links per edge", step: 1, value: 1}));
const backboneOnly = view(Inputs.toggle({label: "Backbone edges only", value: false}));
const colorBy = view(Inputs.select(new Map([["Publication type", "group"], ...Object.entries(AXIS_LABELS).map(([k, v]) => [`Position: ${v}`, k])]), {label: "Colour nodes by", value: "group"}));
```

```js
// Survives redraws (no dependency on the controls): the current zoom and the focused node.
const viewState = {transform: null, focused: null};
```

```js
const gc = groupColors();
// Position colouring on a derived axis: lean = (yes + qualified yes - no) / positioned posts on a
// red-grey-blue diverging scale; paleness = share of positioned posts that commit either way, so publications
// that are all unsure or non-committal render pale. Node axes counts are [yes, yes_qualified, unsure, discussed, no].
const ac = axisColors();
const leanColor = d3.scaleLinear().domain([-1, 0, 1]).range([ac.no || "#e34948", "#b4b3ac", ac.yes || "#2a78d6"]).interpolate(d3.interpolateRgb);
function stanceOf(n) {
  const c = n.axes?.[colorBy];
  if (!c) return null;
  const [y, q, u, x, d] = c, pos = y + q + u + x + d;
  if (!pos) return null;
  return {lean: (y + q - d) / pos, commit: (y + q + d) / pos, y, q, u, x, d, pos};
}
// Paleness is a blend toward the surface colour rather than transparency, so disks stay opaque and edges
// end at their border.
const surface = getComputedStyle(document.documentElement).getPropertyValue("--theme-background").trim() || "#ffffff";
const nodeFill = (n) => {
  if (colorBy === "group") return gc[n.group] || "#b4b3ac";
  const st = stanceOf(n);
  if (!st) return d3.interpolateRgb(surface, "#b4b3ac")(0.45);
  return d3.interpolateRgb(surface, leanColor(st.lean))(0.3 + 0.7 * st.commit);
};
// Nodes with a position are the ones on the backbone; the layout was computed on that subgraph.
const placed = net.pub_nodes.filter((n) => n.x != null && (n.in_pubs >= minIn || n.out_pubs >= 1) && (!onlyTyped || n.relevant_posts > 0));
const placedIds = new Set(placed.map((n) => n.id));
// All edges among the displayed publications by default. The disparity-filter backbone drops a hub's
// light edges to other hubs (weight 1-2 against a strength of 100+), which hides hub-to-hub citation.
const edges = net.pub_edges.filter((e) => e.weight >= minWeight && (!backboneOnly || e.backbone) && placedIds.has(e.source) && placedIds.has(e.target));
const touched = new Set(edges.flatMap((e) => [e.source, e.target]));
const nodes = placed.filter((n) => touched.has(n.id));
const byId = new Map(nodes.map((n) => [n.id, n]));
const W = Math.min(width, 960), H = Math.round(W * 0.8);
const r = d3.scaleSqrt([0, d3.max(nodes, (n) => n.in_pubs) || 1], [2.5, 14]);
// Seed from the precomputed layout (deterministic), then relax the displayed subgraph with a force
// simulation so neighbours sit at a readable distance from their hub instead of inside its radius.
const sx = d3.scaleLinear(d3.extent(nodes, (n) => n.x), [40, W - 40]);
const sy = d3.scaleLinear(d3.extent(nodes, (n) => n.y), [40, H - 40]);
const sim = nodes.map((n) => ({id: n.id, x: sx(n.x), y: sy(n.y), r: r(n.in_pubs)}));
const simById = new Map(sim.map((n) => [n.id, n]));
const links = edges.map((e) => ({source: e.source, target: e.target, weight: e.weight}));
const simulation = d3.forceSimulation(sim)
  .force("link", d3.forceLink(links).id((d) => d.id).distance((l) => 28 + 6 * Math.log1p(l.weight)).strength(0.6))
  .force("charge", d3.forceManyBody().strength(-70).distanceMax(220))
  .force("collide", d3.forceCollide((d) => d.r + 5).iterations(2))
  .force("x", d3.forceX(W / 2).strength(0.03)).force("y", d3.forceY(H / 2).strength(0.03))
  .stop();
for (let i = 0; i < 300; ++i) simulation.tick();
const xs = (v) => v, ys = (v) => v;
for (const n of nodes) { const s = simById.get(n.id); n.px = s.x; n.py = s.y; }
const svg = d3.create("svg").attr("viewBox", [0, 0, W, H]).attr("width", W).attr("height", H)
  .style("max-width", "100%").style("font", "11px system-ui, sans-serif").style("cursor", "grab")
  .style("border", "1px solid var(--theme-foreground-faintest)").style("border-radius", "8px");
const root = svg.append("g");   // everything inside is zoomable
// Edges first, in a visible grey; opaque nodes on top so converging lines do not show through them.
const lines = root.append("g").attr("stroke", "var(--theme-foreground-faint)").attr("stroke-opacity", 0.7).attr("fill", "none")
  .selectAll("line").data(edges).join("line").attr("vector-effect", "non-scaling-stroke")
  .attr("x1", (e) => byId.get(e.source).px).attr("y1", (e) => byId.get(e.source).py)
  .attr("x2", (e) => byId.get(e.target).px).attr("y2", (e) => byId.get(e.target).py)
  .attr("stroke-width", (e) => Math.min(4, 1 + Math.log1p(e.weight)));
const ranked = nodes.slice().sort((a, b) => b.in_pubs - a.in_pubs);
ranked.forEach((n, i) => (n.rank = i));
// Clicking a node focuses it: everything not connected to it dims. Click it again, or the background, to clear.
const circles = root.append("g").selectAll("circle").data(ranked).join("circle")
  .attr("cx", (n) => n.px).attr("cy", (n) => n.py).attr("r", (n) => r(n.in_pubs))
  .attr("fill", nodeFill).attr("stroke", "var(--theme-background)").attr("stroke-width", 1.5)
  .style("cursor", "pointer")
  .on("click", (ev, n) => { ev.stopPropagation(); setFocus(focused && focused.length === 1 && focused[0] === n.id ? null : n.id); });
circles.append("title").text((n) => {
  const st = colorBy !== "group" ? stanceOf(n) : null;
  const pos = st ? `\n${AXIS_LABELS[colorBy]}: yes ${st.y}, qualified ${st.q}, unsure ${st.u}, discussed ${st.x}, no ${st.d}` : colorBy !== "group" ? `\n${AXIS_LABELS[colorBy]}: no position taken` : "";
  return `${n.name || n.host}\n${GROUP_LABELS[n.group] || "untyped"}\ncited by ${n.in_pubs} publications · cites ${n.out_pubs}\n${n.relevant_posts} relevant posts${pos}\nClick to focus; click the name to open its page`;
});
// Labels are links to the publication page, in the site's link colour with an underline on hover.
// They are ranked by citations: at zoom k the top N*k^2 are shown, so zooming in reveals smaller nodes' names.
const labels = root.append("g").attr("stroke", "var(--theme-background)").attr("paint-order", "stroke")
  .selectAll("a").data(ranked).join("a").attr("href", (n) => `./publication/${n.id}`).attr("class", "netlabel")
  .append("text").attr("fill", "var(--theme-foreground-focus)").attr("x", (n) => n.px + r(n.in_pubs) + 3).attr("y", (n) => n.py + 4)
  .text((n) => (n.name || n.host).slice(0, 34));
labels.append("title").text((n) => `Open the page for ${n.name || n.host}`);
let focused = null;
const neighbours = new Map();
for (const e of edges) { (neighbours.get(e.source) || neighbours.set(e.source, new Set()).get(e.source)).add(e.target); (neighbours.get(e.target) || neighbours.set(e.target, new Set()).get(e.target)).add(e.source); }
// Focus on one node (click) or several (the table's checkboxes): the focused nodes and their neighbours
// stay lit, everything else dims. `ids` is null, a number, or an array of numbers.
function setFocus(ids) {
  const set = new Set(ids == null ? [] : Array.isArray(ids) ? ids : [ids]);
  for (const id of [...set]) if (!byId.has(id)) set.delete(id);   // ignore publications not in the current view
  focused = set.size ? [...set] : null; viewState.focused = focused;
  const isF = (n) => set.has(n.id);
  const keep = (n) => !set.size || isF(n) || [...set].some((id) => neighbours.get(id)?.has(n.id));
  circles.attr("opacity", (n) => (keep(n) ? 1 : 0.12))
    .attr("stroke", (n) => (isF(n) ? "var(--theme-foreground)" : "var(--theme-background)"))
    .attr("stroke-width", (n) => (isF(n) ? 3 / currentK : 1.5))
    .attr("r", (n) => r(n.in_pubs) * (isF(n) ? 1.6 : 1));
  lines.attr("stroke-opacity", (e) => (!set.size ? 0.7 : set.has(e.source) || set.has(e.target) ? 0.95 : 0.05));
  labels.attr("opacity", (n) => (keep(n) ? 1 : 0.15))
    .attr("font-weight", (n) => (isF(n) ? 700 : 400))
    .attr("x", (n) => n.px + r(n.in_pubs) * (isF(n) ? 1.6 : 1) + 3);
  circles.filter(isF).raise();
  labels.filter(isF).each(function () { this.parentNode.parentNode.appendChild(this.parentNode); });
  relabel(currentK, focused);
}
viewState.apply = setFocus;
let currentK = 1, currentT = d3.zoomIdentity;
function relabel(k, ids = focused, t = currentT) {
  currentK = k; currentT = t;
  const set = new Set(ids || []);
  const isF = (n) => set.has(n.id);
  // Label the top N by citations among the nodes currently inside the viewport, so zooming into a region
  // labels that region. With a focus, the focused nodes' neighbours in view are labelled first.
  const keep = (n) => !set.size || isF(n) || [...set].some((id) => neighbours.get(id)?.has(n.id));
  const inView = (n) => { const x = t.applyX(n.px), y = t.applyY(n.py); return x >= -20 && x <= W + 20 && y >= -20 && y <= H + 20; };
  const candidates = ranked.filter((n) => inView(n) && keep(n));
  const chosen = new Set(candidates.slice(0, labelTop).map((n) => n.id));
  for (const id of set) chosen.add(id);
  labels.attr("display", (n) => (chosen.has(n.id) ? null : "none")).attr("font-size", (n) => (isF(n) ? 13 : 11) / k).attr("stroke-width", (n) => (isF(n) ? 4 : 3) / k);
}
relabel(1);
svg.on("click", () => setFocus(null));
// Wheel or pinch to zoom, drag to pan, double-click to reset.
const zoom = d3.zoom().scaleExtent([0.5, 12]).on("zoom", (ev) => { viewState.transform = ev.transform; root.attr("transform", ev.transform); relabel(ev.transform.k, focused, ev.transform); });
svg.call(zoom).on("dblclick.zoom", () => svg.transition().duration(300).call(zoom.transform, d3.zoomIdentity));
// Restore the previous zoom and focus after a redraw (colour or filter change).
if (viewState.transform) svg.call(zoom.transform, viewState.transform);
if (viewState.focused) setFocus(viewState.focused);
display(svg.node());
display(html`<p class="caption">Scroll or pinch to zoom, drag to pan, double-click to reset. About twenty labels are shown for whatever is in view, so zooming into a region labels it. Click a node to focus on it and its neighbours; click the name to open the publication page.</p>`);
const legend = colorBy === "group"
  ? GROUP_ORDER.map((k) => html`<span class="pill"><span class="swatch" style="background:${gc[k]}"></span>${GROUP_LABELS[k]}</span>`)
  : html`<span class="pill"><span class="swatch" style="background:${leanColor(-1)}"></span>No</span><span class="pill"><span class="swatch" style="background:linear-gradient(90deg, ${leanColor(-1)}, ${leanColor(0)}, ${leanColor(1)}); width:60px"></span>lean</span><span class="pill"><span class="swatch" style="background:${leanColor(1)}"></span>Yes</span><span class="pill"><span class="swatch" style="background:${d3.interpolateRgb(surface, leanColor(0))(0.3)}"></span>pale: mostly unsure or non-committal</span><span class="pill"><span class="swatch" style="background:${d3.interpolateRgb(surface, "#b4b3ac")(0.45)}"></span>no position taken</span>`;
display(html`<div class="caption">${nodes.length} publications, ${edges.length} edges. ${legend} Node size: citing publications.${colorBy !== "group" ? html` Colour: the publication's lean on "${AXIS_LABELS[colorBy]}", yes (including qualified) minus no over posts taking a position; a single post is enough.` : ""}</div>`);
```

## Most cited publications

Tick publications to focus them in the graph above; the graph keeps its zoom. Only publications currently drawn can be focused.

```js
const picked = view(Inputs.table(net.pub_nodes.slice().sort((a, b) => b.in_pubs - a.in_pubs).slice(0, 40).map((n) => ({name: n.name || n.host, host: n.host, group: GROUP_LABELS[n.group] || "", in_pubs: n.in_pubs, in_posts: n.in_posts, out_pubs: n.out_pubs, pagerank: n.pagerank, relevant: n.relevant_posts, id: n.id})), {
  columns: ["name", "group", "in_pubs", "in_posts", "out_pubs", "relevant"], header: {name: "Publication", group: "Type", in_pubs: "Citing publications", in_posts: "Citing posts", out_pubs: "Cites", relevant: "Relevant posts"},
  width: {name: 260}, rows: 40, multiple: true, required: false, format: {name: (v, i, d) => html`<a href="./publication/${d[i].id}">${v}</a>`}
}));
```

```js
// Runs when the table selection changes; the graph cell is not re-run, so zoom and layout stay put.
viewState.apply?.(picked.map((r) => r.id));
```

## Do camps cite each other?

```js
const cc = net.cross_camp_axes.filter((d) => d.citing && d.cited && d.citing !== "not_addressed" && d.cited !== "not_addressed");
const order = ["yes", "unsure", "discussed", "no"];
const short = {yes: "Yes", unsure: "Unsure", discussed: "Discussed", no: "No"};
display(Plot.plot({
  width: 420, height: 320, marginLeft: 90, marginBottom: 60, padding: 0.05,
  x: {domain: order, label: "Cited post's position →", tickFormat: (d) => short[d]}, y: {domain: order, label: "↑ Citing post's position", tickFormat: (d) => short[d]},
  color: {scheme: "blues", legend: true, label: "Links"},
  marks: [Plot.cell(cc, {x: "cited", y: "citing", fill: "n", inset: 1, title: (d) => `${LEVEL_LABELS[d.citing]} → ${LEVEL_LABELS[d.cited]}: ${d.n} links`}), Plot.text(cc, {x: "cited", y: "citing", text: "n", fill: (d) => (d.n > 15 ? "white" : "var(--theme-foreground)")})]
}));
```

<div class="caption">Links between relevant posts, by the citing and cited authors' positions on whether current LLMs have experience. Counts are small: most posts about machine minds do not link to other Substack posts about machine minds.</div>
