---
title: Positions
---

# Positions, filtered

Choose a slice of the corpus and the stance chart redraws. Shares are of posts whose author addresses the claim.

```js
import {stanceDiverging, stanceTable, GROUP_LABELS, GROUP_ORDER, GENRE_LABELS, ITEM_LABELS, vlChart} from "./components/charts.js";
const posts = await FileAttachment("./data/posts.json").json();
const byGroupSpec = await FileAttachment("./charts/stance_by_group.vl.json").json();
```

```js
const group = view(Inputs.select(new Map([["All publication types", "all"], ...GROUP_ORDER.map((g) => [GROUP_LABELS[g], g])]), {label: "Publication type"}));
const genre = view(Inputs.select(new Map([["All genres", "all"], ...Object.entries(GENRE_LABELS).map(([k, v]) => [v, k])]), {label: "Genre"}));
const object = view(Inputs.select(new Map([["Any subject", "all"], ["LLMs in general", "llms"], ["AI in general", "ai_general"], ["A named model or lab", "named_model"]]), {label: "Claim is about"}));
const relevance = view(Inputs.select(new Map([["Central and substantial", "both"], ["Central only", "central"]]), {label: "Relevance"}));
const channel = view(Inputs.select(new Map([["All discovery channels", "all"], ["Web search and citation only (time-unbiased)", "unbiased"]]), {label: "Channel"}));
```

```js
const subset = posts.filter((p) =>
  (group === "all" || p.group === group) &&
  (genre === "all" || p.genre === genre) &&
  (object === "all" || p.claim_object === object) &&
  (relevance === "both" || p.relevance === "central") &&
  (channel === "all" || p.unbiased));
display(html`<p class="caption">${subset.length.toLocaleString()} posts in this slice.</p>`);
display(stanceDiverging(stanceTable(subset), {width: Math.min(width, 900)}));
```

## By who is writing

The four headline claims, one panel per publication type, from the static figure in the post.

```js
display(await vlChart(byGroupSpec, {width: Math.min(width, 760) - 300}));
```

## The claims

```js
const codebook = await FileAttachment("./data/codebook.json").json();
display(Inputs.table(codebook.constructs.filter((c) => c.group === "stance").map((c) => ({Item: ITEM_LABELS[c.name] || c.name, Claim: c.claim})), {columns: ["Item", "Claim"], width: {Item: 260}, select: false, rows: 20}));
```
