---
title: Overview
---

# Machine minds on Substack

What Substack writers say about whether AI systems think, feel, or matter morally. A systematic reading of the platform: every post we could find on the topic from January 2024 onward, coded by machine with human spot checks. Posts are linked, never reproduced.

```js
import {statRow, vlChart, GROUP_LABELS} from "./components/charts.js";
const summary = await FileAttachment("./data/summary.json").json();
const stanceSpec = await FileAttachment("./charts/axes_landscape.vl.json").json();
const whoSpec = await FileAttachment("./charts/who_writes.vl.json").json();
```

```js
display(statRow([
  ["Relevant posts", summary.posts_relevant.toLocaleString(), `of ${summary.prisma.jev_coded.toLocaleString()} screened`],
  ["Publications", summary.publications_relevant.toLocaleString(), "with at least one relevant post"],
  ["Period", `${summary.date_range[0].slice(0, 7)} to ${summary.date_range[1].slice(0, 7)}`, "post dates"],
  ["Essays", `${Math.round(100 * summary.by_genre.essay / summary.posts_relevant)}%`, "the rest: roundups, transcripts, fiction, podcasts"]
]));
```

## What writers say

```js
display(await vlChart(stanceSpec, {width: Math.min(width, 760) - 300}));
```

<div class="caption">Each bar is one of six questions, each combining one to three coded claims. Shares are of posts whose author addresses the question in their own voice; posts that only report others' positions, or never raise it, are excluded. "Yes, qualified" means partly (thinking), after a major advance (possibility), or future AI or precaution (moral status). Hover for counts. <a href="./positions">Filter by publication type, genre and more →</a></div>

## Who writes about it

```js
display(await vlChart(whoSpec, {width: Math.min(width, 700) - 220}));
```

<div class="caption">Publication types were coded from each publication's name, tagline, author bio and post titles. Nine fine categories are collapsed to five for display; see <a href="./methods">Methods</a>.</div>

## Where to go

- **[Positions](./positions)**: the six questions with filters, how positions differ by who is writing, and the claims behind them.
- **[Arguments and sources](./arguments)**: which arguments appear, what gets cited, who gets named.
- **[Features of the systems](./features)**: which features of the AI systems themselves authors point to as evidence, in which direction, and how that mix has shifted.
- **[Topic map](./topics)**: the relevant posts laid out by similarity, with labelled clusters.
- **[Citation network](./network)**: which publications cite which.
- **[Over time](./timeline)**: how the mix of positions has shifted by quarter.
- **[Notable posts](./notable)**: posts that beat their own publication's norm, and the most-engaged posts overall.
- **[Changes of mind](./revisions)**: posts whose author reports having once thought differently about machine minds, with the passage that says so.
- **[Browse posts](./posts)**: every relevant post with its codes, filterable and downloadable.
- **[Publications](./publications)**: one page per publication, with its posts and how it sits in the discourse.
- **[Methods](./methods)**: how the corpus was built and coded, and how well the coding holds up.
