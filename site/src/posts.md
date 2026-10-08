---
title: Browse posts
---

# Browse posts

Every relevant post with its codes. Search matches titles, publications and authors. Download the filtered table as CSV; bodies are not included anywhere on this site.

```js
import {GROUP_LABELS, GROUP_ORDER, GENRE_LABELS, STANCE_LABELS, ITEM_LABELS, ARG_LABELS} from "./components/charts.js";
const posts = await FileAttachment("./data/posts.json").json();
const topics = await FileAttachment("./data/topics.json").json();
```

```js
const group = view(Inputs.select(new Map([["Any type", "all"], ...GROUP_ORDER.map((g) => [GROUP_LABELS[g], g])]), {label: "Publication type"}));
const item = view(Inputs.select(new Map([["Any claim", null], ...Object.entries(ITEM_LABELS).map(([k, v]) => [v, k])]), {label: "Claim"}));
const position = view(Inputs.select(new Map([["Any position", null], ...Object.entries(STANCE_LABELS).map(([k, v]) => [v, k])]), {label: "Position"}));
const argument = view(Inputs.select(new Map([["Any argument", null], ...Object.entries(ARG_LABELS).map(([k, v]) => [v, k])]), {label: "Uses argument"}));
const cluster = view(Inputs.select(new Map([["Any topic", null], ...topics.map((t) => [t.label, t.cluster])]), {label: "Topic"}));
const genre = view(Inputs.select(new Map([["Any genre", "all"], ...Object.entries(GENRE_LABELS).map(([k, v]) => [v, k])]), {label: "Genre"}));
```

```js
const filtered = posts.filter((p) =>
  (group === "all" || p.group === group) &&
  (item == null || position == null || p.stance[item] === position) &&
  (item != null || position == null || Object.values(p.stance).includes(position)) &&
  (argument == null || p.arguments.includes(argument)) &&
  (cluster == null || p.cluster === cluster) &&
  (genre === "all" || p.genre === genre));
const search = view(Inputs.search(filtered, {placeholder: "Search titles, publications, authors…", columns: ["title", "subtitle", "publication", "author", "host"]}));
```

```js
const rows = search.map((p) => ({
  date: p.date, title: p.title, publication: p.publication || p.host, type: GROUP_LABELS[p.group] || "", genre: GENRE_LABELS[p.genre] || p.genre,
  conscious: STANCE_LABELS[p.stance.current_conscious] || "", moral: STANCE_LABELS[p.stance.moral_worth_current] || "", topic: p.cluster_label || "",
  reactions: p.reactions, restacks: p.restacks, cited_by: p.in_pubs, url: p.url, id: p.id, publication_id: p.publication_id
}));
display(html`<p class="caption">${rows.length.toLocaleString()} posts. ${Inputs.button("Download CSV", {reduce: () => downloadCsv(rows)})}</p>`);
display(Inputs.table(rows, {
  columns: ["date", "title", "publication", "type", "genre", "conscious", "moral", "topic", "reactions", "restacks", "cited_by"],
  header: {date: "Date", title: "Post", publication: "Publication", type: "Type", genre: "Genre", conscious: "Conscious now?", moral: "Moral worth now?", topic: "Topic", reactions: "Reactions", restacks: "Restacks", cited_by: "Cited by"},
  width: {title: 320, publication: 160, topic: 200}, select: false, rows: 25, sort: "date", reverse: true,
  format: {title: (v, i, d) => html`<a href="${d[i].url}" target="_blank" rel="noopener">${v}</a>`, publication: (v, i, d) => html`<a href="./publication/${d[i].publication_id}">${v}</a>`}
}));
function downloadCsv(rows) {
  const cols = ["id", "date", "title", "publication", "type", "genre", "conscious", "moral", "topic", "reactions", "restacks", "cited_by", "url"];
  const esc = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const csv = [cols.join(","), ...rows.map((r) => cols.map((c) => esc(r[c])).join(","))].join("\n");
  const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([csv], {type: "text/csv"})); a.download = "machine-minds-posts.csv"; a.click();
}
```
