---
title: Arguments and sources
---

# Arguments and sources

```js
import {vlChart} from "./components/charts.js";
const sources = await FileAttachment("./data/sources.json").json();
const argSpec = await FileAttachment("./charts/arguments_traction.vl.json").json();
const citedSpec = await FileAttachment("./charts/top_cited_works.vl.json").json();
const peopleSpec = await FileAttachment("./charts/people_named.vl.json").json();
```

## Which arguments appear, and which get traction

```js
display(await vlChart(argSpec));
```

<div class="caption">Thirteen argument types coded present or absent per post. Traction is the median of each post's reactions divided by its publication's average reactions over the period, so a value of 1.0 means a typical post for that publication.</div>

## What the discourse cites

```js
display(await vlChart(citedSpec));
```

```js
const tiers = Object.entries(sources.tiers).map(([t, v]) => ({tier: t, posts: v.posts_citing, works: v.works})).sort((a, b) => b.posts - a.posts);
display(Inputs.table(tiers, {columns: ["tier", "posts", "works"], header: {tier: "Source tier", posts: "Relevant posts citing it", works: "Distinct works"}, select: false, rows: 12}));
```

<div class="caption">Tiers are assigned by reference kind (arXiv and DOI are academic, Amazon ASINs are books, Wikipedia is encyclopedia, Substack posts are Substack) and then by domain list; images, link shorteners and platform pages are dropped. The full mapping is in <code>config/domain_tiers.yaml</code>. Links that point at one work under different URLs (a publisher page, its PDF and its DOI; a preprint and the journal version; a lab's blog post and its paper) are merged: ${sources.references_raw.toLocaleString()} distinct links became ${(sources.references_raw - sources.works_merged).toLocaleString()} works.</div>

### Top works by tier

```js
const tierPick = view(Inputs.select(Object.keys(sources.top_works_by_tier), {label: "Tier", value: "academic"}));
```

```js
const site = (u) => u.replace(/^https?:\/\/(www\.)?/, "").split("/")[0];
const SOURCE_NOTE = {slug: "no title found; read from the URL", anchor: "named from the text posts linked with", brave: "named from a search result for this URL", oembed: "named from the platform's embed data", pdf: "named from the PDF's metadata"};
display(Inputs.table(sources.top_works_by_tier[tierPick].map((w) => ({work: w.title || w.url, source: site(w.url) + (w.aliases && w.aliases.length ? ` +${w.aliases.length}` : ""), publications: w.citing_pubs, posts: w.citing_posts, url: w.url, title_source: w.title_source, aliases: w.aliases || []})), {
  columns: ["work", "source", "publications", "posts"], header: {work: "Work", source: "Site", publications: "Publications", posts: "Posts"}, width: {work: 400, source: 130, publications: 90, posts: 60}, select: false, rows: 25,
  format: {
    work: (v, i, data) => html`<a href="${data[i].url}" target="_blank" rel="noopener" class="${data[i].title_source === "slug" || !data[i].title_source ? "work-slug" : ""}" title="${SOURCE_NOTE[data[i].title_source] || ""}">${v}</a>`,
    source: (v, i, data) => html`<span title="${data[i].aliases.length ? "also cited as: " + data[i].aliases.join(", ") : ""}">${v}</span>`
  }
}));
```

<div class="caption">A work named in grey had no title we could recover and shows its URL slug, or the URL itself, instead; hover a name for where the title came from. "+n" after a site means n other URLs were merged into the work; hover to see them.</div>

## Who gets named

```js
display(await vlChart(peopleSpec));
```

<div class="caption">Counted by regular expression over post text; a post counts once per person. Surnames alone are used only where unambiguous. Names in blue link to the person's Wikipedia article; a name in grey has none. The list is in <code>config/names.yaml</code>.</div>
