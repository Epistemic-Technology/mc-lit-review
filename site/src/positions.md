---
title: Positions
---

# Positions, filtered

Choose a slice of the corpus and the chart redraws. Each row is one of six questions; shares are of posts whose author addresses the question in their own voice.

```js
import {axesDiverging, axesTable, GROUP_LABELS, GROUP_ORDER, GENRE_LABELS, AXIS_LABELS, AXIS_QUALIFIED, ITEM_LABELS, vlChart} from "./components/charts.js";
const posts = await FileAttachment("./data/posts.json").json();
const codebook = await FileAttachment("./data/codebook.json").json();
const byGroupSpec = await FileAttachment("./charts/axes_by_group.vl.json").json();
const profileSpec = await FileAttachment("./charts/axes_profile.vl.json").json();
const agencySpec = await FileAttachment("./charts/axes_profile_agency.vl.json").json();
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
display(axesDiverging(axesTable(subset), {width: Math.min(width, 900)}));
```

<div class="caption">"Yes, qualified" is question-specific: partly (yes on some capacities, no on others) for thinking; yes but only after a major advance for possibility in principle; not now but future AI could, or act with precaution regardless, for moral status.</div>

## By who is writing

One panel per publication type, from the static figure in the post.

```js
display(await vlChart(byGroupSpec, {width: Math.min(width, 760) - 300}));
```

## Thinking, and goals, without experience

```js
display(html`<div class="grid grid-cols-2">${await vlChart(profileSpec, {width: Math.min(width / 2, 320)})}${await vlChart(agencySpec, {width: Math.min(width / 2, 300)})}</div>`);
```

<div class="caption">Posts with a position on experience and on one other "now" question. The lower-right cells, granting cognition or goals while denying or doubting experience, are real camps; the reverse corners are nearly empty.</div>

## The six questions

Each question is coded directly from the post (codebook 0.2.0). An earlier version of this site derived them from fourteen finer claims; the two agree closely, and the comparison is on the <a href="./methods">Methods</a> page.

```js
display(html`<table class="axes">
  <thead><tr><th>Question</th><th>Asks</th><th>Qualified yes means</th><th>Replaced these 0.1.0 claims</th></tr></thead>
  <tbody>${codebook.axes.map((a) => html`<tr><td><b>${AXIS_LABELS[a.name] || a.label}</b></td><td>${a.question}</td><td>${AXIS_QUALIFIED[a.name] || ""}</td><td>${a.items.map((i) => ITEM_LABELS[i] || i).join("; ")}</td></tr>`)}</tbody>
</table>`);
```
