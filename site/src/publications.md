---
title: Publications
---

# Publications

Every publication with at least one relevant post. Click a name for its page.

```js
import {GROUP_LABELS, GROUP_ORDER, LEVEL_LABELS} from "./components/charts.js";
const pubs = await FileAttachment("./data/publications.json").json();
```

```js
const group = view(Inputs.select(new Map([["Any type", "all"], ...GROUP_ORDER.map((g) => [GROUP_LABELS[g], g])]), {label: "Publication type"}));
```

```js
// Own block: a view()'s value is only resolved in later blocks (in the same block it is still a generator).
const search = view(Inputs.search(pubs.filter((p) => group === "all" || p.group === group), {placeholder: "Search publications and authors…", columns: ["name", "host", "author", "tagline"]}));
```

```js
display(Inputs.table(search.map((p) => ({
  name: p.name || p.host, author: p.author, type: GROUP_LABELS[p.group] || "", relevant: p.relevant_posts, window: p.posts_in_window, share: p.relevant_share,
  lean: lean(p.axes_experience_now), cited: p.in_pubs, subscribers: p.subscribers, id: p.id, host: p.host
})), {
  columns: ["name", "author", "type", "relevant", "window", "share", "lean", "cited", "subscribers"],
  header: {name: "Publication", author: "Author", type: "Type", relevant: "Relevant posts", window: "All posts since 2024", share: "Share", lean: "Current LLMs have experience", cited: "Cited by", subscribers: "Subscribers"},
  width: {name: 240}, select: false, rows: 30, sort: "relevant", reverse: true,
  format: {name: (v, i, d) => html`<a href="./publication/${d[i].id}">${v}</a>`, share: (v) => (v == null ? "" : `${Math.round(v * 100)}%`)}
}));
// The publication's most common committed answer on the experience question, with its count.
function lean(s) {
  const committed = {yes: (s.yes || 0) + (s.yes_qualified || 0), no: s.no || 0, unsure: s.unsure || 0};
  const top = Object.entries(committed).sort((x, y) => y[1] - x[1])[0];
  return top[1] ? `${LEVEL_LABELS[top[0]]} (${top[1]})` : "";
}
```
