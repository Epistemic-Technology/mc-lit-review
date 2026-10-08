---
title: Browse posts
---

# Browse posts

Every relevant post with its codes. Search matches titles, publications and authors. Download the filtered table as CSV; bodies are not included anywhere on this site.

```js
import {GROUP_LABELS, GROUP_ORDER, GENRE_LABELS, AXIS_LABELS, LEVEL_LABELS, ARG_LABELS} from "./components/charts.js";
const posts = await FileAttachment("./data/posts.json").json();
const topics = await FileAttachment("./data/topics.json").json();
```

```js
const group = view(Inputs.select(new Map([["Any type", "all"], ...GROUP_ORDER.map((g) => [GROUP_LABELS[g], g])]), {label: "Publication type"}));
const axis = view(Inputs.select(new Map([["Any question", null], ...Object.entries(AXIS_LABELS).map(([k, v]) => [v, k])]), {label: "Question"}));
const position = view(Inputs.select(new Map([["Any position", null], ...Object.entries(LEVEL_LABELS).map(([k, v]) => [v, k])]), {label: "Position"}));
const argument = view(Inputs.select(new Map([["Any argument", null], ...Object.entries(ARG_LABELS).map(([k, v]) => [v, k])]), {label: "Uses argument"}));
const cluster = view(Inputs.select(new Map([["Any topic", null], ...topics.map((t) => [t.label, t.cluster])]), {label: "Topic"}));
const genre = view(Inputs.select(new Map([["Any genre", "all"], ...Object.entries(GENRE_LABELS).map(([k, v]) => [v, k])]), {label: "Genre"}));
```

```js
const filtered = posts.filter((p) =>
  (group === "all" || p.group === group) &&
  (axis == null || position == null || p.axes[axis] === position) &&
  (axis != null || position == null || Object.values(p.axes).includes(position)) &&
  (argument == null || p.arguments.includes(argument)) &&
  (cluster == null || p.cluster === cluster) &&
  (genre === "all" || p.genre === genre));
const search = view(Inputs.search(filtered, {placeholder: "Search titles, publications, authors…", columns: ["title", "subtitle", "publication", "author", "host"]}));
```

```js
const lv = (v) => (v && v !== "not_addressed" ? LEVEL_LABELS[v] : "");
const rows = search.map((p) => ({
  date: p.date, title: p.title, publication: p.publication || p.host, type: GROUP_LABELS[p.group] || "", genre: GENRE_LABELS[p.genre] || p.genre,
  experience: lv(p.axes.experience_now), cognition: lv(p.axes.cognition_now), agency: lv(p.axes.agency_now), moral: lv(p.axes.moral_status), topic: p.cluster_label || "",
  reactions: p.reactions, restacks: p.restacks, cited_by: p.in_pubs, url: p.url, id: p.id, publication_id: p.publication_id
}));
display(html`<p class="caption">${rows.length.toLocaleString()} posts. ${Inputs.button("Download CSV", {reduce: () => downloadCsv(rows)})}</p>`);
display(Inputs.table(rows, {
  columns: ["date", "title", "publication", "type", "genre", "experience", "cognition", "agency", "moral", "topic", "reactions", "restacks", "cited_by"],
  header: {date: "Date", title: "Post", publication: "Publication", type: "Type", genre: "Genre", experience: "Experience now?", cognition: "Thinks now?", agency: "Own goals?", moral: "Moral status?", topic: "Topic", reactions: "Reactions", restacks: "Restacks", cited_by: "Cited by"},
  width: {title: 320, publication: 160, topic: 200}, select: false, rows: 25, sort: "date", reverse: true,
  format: {title: (v, i, d) => html`<a href="${d[i].url}" target="_blank" rel="noopener">${v}</a>`, publication: (v, i, d) => html`<a href="./publication/${d[i].publication_id}">${v}</a>`}
}));
function downloadCsv(rows) {
  const cols = ["id", "date", "title", "publication", "type", "genre", "experience", "cognition", "agency", "moral", "topic", "reactions", "restacks", "cited_by", "url"];
  const esc = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const csv = [cols.join(","), ...rows.map((r) => cols.map((c) => esc(r[c])).join(","))].join("\n");
  const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([csv], {type: "text/csv"})); a.download = "machine-minds-posts.csv"; a.click();
}
```

<div class="caption">Positions are the six derived questions; "qualified" yes is question-specific (see <a href="./positions">Positions</a>). Posts that never raise a question show a blank.</div>
