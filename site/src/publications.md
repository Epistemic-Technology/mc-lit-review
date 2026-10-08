---
title: Publications
---

# Publications

Every publication with at least one relevant post. Click a name for its page.

```js
import {GROUP_LABELS, GROUP_ORDER, STANCE_LABELS} from "./components/charts.js";
const pubs = await FileAttachment("./data/publications.json").json();
```

```js
const group = view(Inputs.select(new Map([["Any type", "all"], ...GROUP_ORDER.map((g) => [GROUP_LABELS[g], g])]), {label: "Publication type"}));
const search = view(Inputs.search(pubs.filter((p) => group === "all" || p.group === group), {placeholder: "Search publications and authors…", columns: ["name", "host", "author", "tagline"]}));
```

```js
display(Inputs.table(search.map((p) => ({
  name: p.name || p.host, author: p.author, type: GROUP_LABELS[p.group] || "", relevant: p.relevant_posts, window: p.posts_in_window, share: p.relevant_share,
  lean: lean(p.stance_current_conscious), cited: p.in_pubs, subscribers: p.subscribers, id: p.id, host: p.host
})), {
  columns: ["name", "author", "type", "relevant", "window", "share", "lean", "cited", "subscribers"],
  header: {name: "Publication", author: "Author", type: "Type", relevant: "Relevant posts", window: "All posts since 2024", share: "Share", lean: "On current consciousness", cited: "Cited by", subscribers: "Subscribers"},
  width: {name: 240}, select: false, rows: 30, sort: "relevant", reverse: true,
  format: {name: (v, i, d) => html`<a href="./publication/${d[i].id}">${v}</a>`, share: (v) => (v == null ? "" : `${Math.round(v * 100)}%`)}
}));
function lean(s) {
  const a = s.asserts || 0, d = s.denies || 0, g = s.agnostic || 0;
  if (a + d + g === 0) return "";
  const top = Object.entries({asserts: a, denies: d, agnostic: g}).sort((x, y) => y[1] - x[1])[0];
  return `${STANCE_LABELS[top[0]]} (${top[1]})`;
}
```
