---
title: Methods
---

# Methods

## Division of labor

This project made significant use of [Claude Code](https://claude.com/claude-code) running Claude Fable 5.1 for study design, writing code, and analysis. In addition, [Jev](https://typesafe.ai) and Claude Opus 5.5 were used for coding (categorization).

Mike:

- Overall study conception and design. Specifically, the idea to do a systematic statistical study of opinions about machine cognition as expressed by Substack posts between January 2024 and October 2026.
- Specified the methodology of obtaining posts: initial keyword searches via [Brave](https://brave.com/search/api/) and then expanding the candidate pool of posts using bibliographic coupling. This methodology was chosen to avoid biasing the sample to known hubs of discussion on Substack.
- Specified the overall pipeline: A large pool of candidate posts -> Jev for initial filtering -> LLM for final round.
- Specified the overall approach of using SQLite + Python for the analysis and website.
- Sanity-checked classifications by reading and manually classifying posts and publications.
- Wrote this methodology page.
- Wrote the Substack post.
- Inspected the database structure and key parts of the code.
- Specified the overall design and structure of the site, and offered iterative instructions on improving functionality.

Claude:

- Wrote all of the code, including for retrieval, analysis, and the website.
- Made most of the detailed study design decisions, including that Mike should manually spot check posts and publications.
- Chose the Observable framework for the website.
- Final classification of posts and publications (Claude Opus).

Jev:

- Initial triage of posts.

## Costs

- Brave Search API: $49.71 for 11,790 search requests
- Jev: $48.11 for 122,864 requests
- Claude Opus 5.5: $1,805.78 in API costs (covered by $200 Claude Max plan)
- Human coding time (classification): 594 minutes

Total: $1,903.60 ($97.82 out of pocket)

## Building the corpus

```js
const summary = await FileAttachment("./data/summary.json").json();
const p = summary.prisma;
// Posts that entered at round 0 (the keyword searches) are not in the export; the figure is
// SELECT COUNT(*) FROM posts WHERE entry_round = 0 on the database behind summary.json.
const SEARCH_POSTS = 16275;
const stages = [
  {stage: "Keyword search", detail: "Brave web search and Substack post search over the query bank", n: SEARCH_POSTS},
  {stage: "Citation expansion", detail: "Substack posts cited by corpus posts, plus bibliographic coupling: posts citing the works corpus posts share", n: p.corpus},
  {stage: "Eligible", detail: "Dated 2024 or later, English, body fetched, at least 400 characters, two aggregators excluded", n: p.after_exclusions},
  {stage: "Jev screen", detail: "Passed Jev's relevance screen (three repeats) and sent to Claude", n: p.claude_coded},
  {stage: "Claude coding", detail: "Coded by Claude Opus 5.5 as central or substantial", n: p.relevant}
].map((s, i, a) => ({...s, i, prev: i ? a[i - 1].n : null, delta: i ? s.n - a[i - 1].n : null, x1: -s.n / 2, x2: s.n / 2}));
const fmt = (n) => n.toLocaleString("en-US");
const signed = (d) => (d > 0 ? "+" : "−") + fmt(Math.abs(d));
```

```js
display(Plot.plot({
  width: Math.min(width, 760), height: 56 * stages.length + 24,
  marginLeft: 150, marginRight: 110, marginTop: 8, marginBottom: 8,
  x: {axis: null, domain: [-p.corpus / 2, p.corpus / 2]},
  y: {domain: stages.map((s) => s.stage), label: null, tickSize: 0},
  marks: [
    Plot.barX(stages, {x1: "x1", x2: "x2", y: "stage", fill: "var(--series-1)", insetTop: 5, insetBottom: 5, rx: 4,
      tip: true, title: (d) => `${d.stage}\n${d.detail}\n${fmt(d.n)} posts${d.delta == null ? "" : ` (${signed(d.delta)} from the previous stage)`}`}),
    Plot.text(stages, {x: "x2", y: "stage", text: (d) => fmt(d.n), dx: 8, textAnchor: "start", fill: "var(--theme-foreground)", fontSize: 13, fontWeight: 600}),
    Plot.text(stages.filter((d) => d.delta != null), {x: "x2", y: "stage", text: (d) => signed(d.delta), dx: 8, dy: 15, textAnchor: "start", fill: "var(--theme-foreground-muted)", fontSize: 11})
  ]
}));
display(html`<p class="caption">Posts at each stage of the pipeline. Keyword searches found ${fmt(SEARCH_POSTS)} posts; citation expansion grew the pool to ${fmt(p.corpus)}; eligibility filters, Jev's relevance screen and Claude's coding narrowed it to ${fmt(p.relevant)} relevant posts.</p>`);
```

The goals in building this corpus were to (1) cast a wide net, so that I captured relevant posts even if they had not yet reached a wide audience, (2) not privilege any particular author or set of authors, (3) not cause undue load on Substack's servers, (4) keep costs within reasonable limits, and (5) accomplish this all with a one-person research team in a short time.

Initial posts were gathered by querying Substack's public API and through Brave searches scoped to `substack.com`. This was a keyword search, with a pool of keywords such as:

- machine consciousness
- AI sentience
- does AI understand
- machine self-awareness
- AI welfare
- model welfare
- LLM cognition
- stochastic parrots
- Chinese room
- computational theory of mind
- functionalism AI
- integrated information theory AI
- Chalmers AI consciousness
- Butlin Long consciousness report
- Claude consciousness

There were 91 search terms in all, covering a wide range of concepts, arguments, and thinkers related to machine cognition.

That gave us ${fmt(SEARCH_POSTS)} initial posts. From those, I expanded in two ways: following links in those posts, and searching for other posts with the same citations as those posts (bibliographic coupling). This resulted in a collection of ${fmt(p.corpus)} posts. Some of those were excluded (outside of our date range, less than 400 characters, or not in English, for example), which narrowed the collection down to ${fmt(p.after_exclusions)} posts. Jev, a classifier service aimed at just this sort of task, was then used to judge the relevance of posts and do initial categorization (though in nearly every case the categorization was overridden by Claude or me. Jev-codings only survived in a couple of rare misses in the other coding methods). Jev's pass reduced the collection to ${fmt(p.claude_coded)} posts. Claude further reduced that to ${fmt(p.relevant)} posts. That is our final corpus.

For every post, the following was collected:

- Title, subtitle, and description
- Publication date
- Post type (newsletter, podcast, video, or note) and section within the publication
- Word count and language
- Audience and whether the post is paywalled
- Reaction, comment, and restack counts as of the crawl
- Full body text for free posts; the public preview only for paywalled posts
- Bylines (one or more authors, with name, handle, and bio)
- Tags
- Every outbound link, with its anchor text, normalised to a cited work (a Substack post, arXiv paper, DOI, Wikipedia article, book, or web page) and, where it could be recovered, the work's title
- How the post was found: which search query or which citing post led to it

And for every publication:

- Name and tagline
- Substack subdomain and custom domain, if any
- Primary author's name and handle, plus any further authors and their roles
- Language and type
- Date the publication was created on Substack and the date of its first post
- Free subscriber count, as the order of magnitude Substack reports
- Archive metadata (titles, dates, and engagement counts, but not bodies) for every post since 2024, for publications with enough corpus posts to need an engagement baseline

Two runs of this pipeline were completed: an initial run on 2026-09-27 and a final run on 2026-10-13 to bring the corpus up to date.

## Coding

For each post, I evaluated the following:

Relevance:

- Is the post about machine minds? (central, substantial, passing, irrelevant)
- Is the post about AI, but not minds? (yes/no)

Type:

- Genre (essay, roundup, fiction, model transcript, interview or podcast, other)
- Target of discussion (LLMs, AI in general, a named model or lab)
- Substantially author's own view (vs. reporting that of others)? (yes/no)

Stances:

Each question is answered on the same scale: yes, qualified yes (where defined), no, unsure, discussed without taking a position, reports others' views only, or not addressed. The answer is always the author's own position, not a view they report.

| Question | Yes means | Qualified yes means |
|---|---|---|
| **Experience now.** Do current LLMs have consciousness, feelings, or the capacity to suffer? | They do, even minimally. | — |
| **Cognition now.** Do current LLMs genuinely think, reason, understand, or know? | They do, not merely simulate it. | In some respects but not others. |
| **Agency now.** Do current LLMs have goals or preferences of their own? | They do, including emergent or misaligned ones. | — |
| **Possible in principle.** Could AI ever be conscious or genuinely think? | Yes, and the current approach could get there. | Yes, but only with a major advance beyond current architectures. |
| **Moral status.** Do AI systems' interests matter morally? | Current systems' interests matter now. | Not now, but future AI's could, or we should act with precaution as if they might. |
| **Serious question.** Is AI consciousness a serious question rather than hype? | It deserves careful thought, whatever the answer. | — |


Change of view:

- Does the author report that their own view on whether machines have minds has changed, and in which direction? (toward minds, away from minds, no change) The post must state both the earlier view and the present one. This question was added after the others, and tightened once: the first version also counted conversions that happened inside the post's own experiment or conversation, present views with no stated earlier view, and changes on neighbouring questions (terminology, which argument counts, whether the question matters). Reading every post it had flagged showed most of them to be of those kinds, so the rule was narrowed and those posts re-coded. The results are on the [Changes of mind](./revisions) page.

Features of the systems:

- Fourteen questions, one per feature of the AI systems themselves: the next-token prediction objective; the architecture (transformer, no recurrence, frozen weights); the training data; post-training and system prompts; memory and continuity; body, senses and world contact; many simultaneous instances; what the model says about itself; interpretability findings; behaviour under evaluation (scheming, blackmail, distress); agentic action in the world (tools, code, computer use, autonomous tasks); what it succeeds at; what it fails at; scale and brain comparison. For each, does the author point to the feature as bearing on whether the system has a mind, and in which direction (toward a mind, against, both ways or no direction, not cited)? A feature mentioned without being connected to minds is not cited. These were added after the stance questions, because the argument codes bundle a feature with an inference and had no place for what models now do in the world. Capabilities began as one question; reading its quotes showed two different sceptical moves under one code, conceding the performance and denying it is evidence, and denying the performance, so it was split into successes and failures, each still coded with a direction. The results are on the [Features of the systems](./features) page.

Initially, I coded 14 more granular questions:

Each was a claim the author could assert, deny, be agnostic about, discuss without concluding, report others' views on only, or not address. The question each one fed into after the recode is given in parentheses.

1. Current LLM-based systems are conscious or have subjective experience. (Experience now)
2. Current LLM-based systems have emotions, feelings, or can suffer. (Experience now)
3. We cannot know, or cannot currently determine, whether AI systems are conscious. (Experience now)
4. Current LLM-based systems genuinely think, reason, or exhibit cognition, not merely simulate it. (Cognition now)
5. Current LLM-based systems genuinely understand language or the world. (Cognition now)
6. Current LLM-based systems have beliefs or knowledge in a genuine sense. (Cognition now)
7. Current LLM-based systems have genuine goals, preferences, or agency of their own. (Agency now)
8. LLM-based or other AI systems could in principle be conscious or have subjective experience. (Possible in principle)
9. AI systems could in principle genuinely think, reason, or exhibit cognition. (Possible in principle)
10. Current architectures are in principle insufficient for consciousness or genuine cognition; a major advance would be needed first. (Possible in principle)
11. Current LLM-based systems have moral worth: their interests or welfare matter morally. (Moral status)
12. Future AI systems could have moral worth, and this deserves preparation now. (Moral status)
13. Regardless of whether AI systems are conscious, we should act with precaution as if they might be. (Moral status)
14. Talk of AI consciousness is hype, marketing, anthropomorphism, or manipulation rather than a serious question. (Serious question, inverted)

These questions proved to be too detailed: they made it hard to see patterns and contrasts in positions between different posts. Initially the questions were narrowed by programmatically combining the 14 original questions, and then they were fully recoded by Claude, with human sanity-checking.

## Human role in coding

I spent approximately 10 hours reading and coding publications and individual posts. Overall, I coded 29 publications and 209 posts. This was done through a web interface constructed by Claude. These numbers are small enough that they don't have a significant impact on the overall picture. Rather, they gave me confidence in the sanity of Claude and Jev's judgments. They were also used as feedback. Where I diverged from the models, this was used to adjust how they would do their coding.

## Note on statistical practice

This is purely exploratory research. I'm not pretending to test any hypotheses with this data, and so there are no error bars, confidence intervals, and so on. While I hope the visualizations are interesting and the classifications are informative, they aren't meant to make statistically-valid claims.

## License and citation

The text, figures and data on this site are licensed under a [Creative Commons Attribution 4.0 International License](https://creativecommons.org/licenses/by/4.0/) (CC BY 4.0). You may share and adapt them for any purpose, including commercially, provided you give appropriate credit. The posts themselves are linked, not reproduced, and remain the property of their authors.

The code that built the corpus, ran the analysis and generates this site is in the [mc-lit-review repository](https://github.com/Epistemic-Technology/mc-lit-review) under the MIT license.

Cite as: Mike Thicke, "Machine Minds on Substack," 2026, [https://machine.epistemic.technology/](https://machine.epistemic.technology/).
