# Jev (TypeSafe AI) for corpus coding: research notes

Written 2026-09-29. Jev was released 2026-09-15, so this is based on the vendor's documentation and the
first two weeks of independent evaluation. Re-check before relying on any number here.

## 1. What Jev is

Jev is TypeSafe AI's first "System One" or decision model. It reads a block of *state* (text, JSON, or an
array of either) plus a set of *typed questions*, and returns typed answers with probability distributions
and a confidence score. It generates no text. TypeSafe says it is transformer-based, trained on synthetic
data with a method they call Reinforcement Learning for Calibrated Decisions (RLCD). Weights, architecture
and a technical paper are unpublished.

Question primitives:

| Type | Returns | Limits |
|---|---|---|
| `choice` | highest-probability option, full distribution over options, confidence | up to 255 options |
| `score` | probability-weighted position on ordered levels, distribution, confidence | 2 to 10 levels |
| `noul` | probability (0 to 1) that a statement is true | one statement |

Every question in a request is evaluated in parallel, so a request with thirty questions takes about as
long as one with a single question. Instructions and criteria (option descriptions, level descriptions,
Noul true/false boundaries) accept structured JSON, e.g. `{"what": ..., "not_for": ..., "examples": [...]}`,
which the docs recommend when options are easily confused.

Confidence is not an independent signal. For Choice it is computed from the distribution as
`(N * p_max - 1) / (N - 1)`: 1.0 when all mass is on one option, 0.0 when spread evenly.

Operational facts (2026-09-29):

| Item | Value | Source |
|---|---|---|
| Release | 2026-09-15, early access; open signup 2026-09-20 with $5 credit | Wikipedia, jevaiguide |
| Access routes | `console.typesafe.ai` direct API; Cloudflare Workers AI (`typesafe/jev`); Vercel AI Gateway (`typesafe-ai/jev`); DigitalOcean | search results |
| Endpoint | `POST https://api.typesafe.ai/v1/systemone`, bearer auth | API reference |
| Model ids | `jev-latest`, `jev-preview` (both resolve to `jev-1.13.0`); pinning supported | API reference, systemonemodels.org |
| State budget | 32,000 tokens (state plus longest question); 64,000 total context | Cloudflare, systemonemodels.org |
| Price | $0.042 per million input tokens; output free; cached input free | TypeSafe blog, Cloudflare |
| Rate limits | ~250k tokens/s, ~1,200 requests/min, "can change without notice" | systemonemodels.org |
| Latency | 70 to 500 ms server-side; 1 to 3 s end-to-end on long documents | TypeSafe, independent tests |
| Python SDK | `pip install typesafe-sdk`; `TypeSafeClient().system_one(state, questions)`; async client; retry policy | SDK docs |
| Data | "not trained on customer requests"; zero retention only for enterprise DPA; not audited | systemonemodels.org |
| Deprecation policy | none published; no changelog; weights not released | systemonemodels.org |

Cost for this corpus: the English, 2024+ posts with bodies are 23,445 posts and roughly 96 million tokens.
One pass of the entire codebook over the entire corpus is therefore about **$4**. 154 posts exceed the
32k-token state budget and need truncation or chunking.

## 2. Independent evidence on accuracy

### 2.1 Computational social science annotation (most relevant to us)

Ibrahim & Zaki (NYU Abu Dhabi), "Evaluating Decision Models for Text Annotation in Computational Social
Science", arXiv 2609.24574. Jev vs 19 LLMs vs fine-tuned RoBERTa-large on 18 tasks, 7,977 items, using the
Ziems et al. (2024) benchmark prompts restated as typed Choice questions.

| Task | Jev macro-F1 | Best LLM | Fine-tuned RoBERTa | Note |
|---|---|---|---|---|
| Stance detection (utterance) | 73.4 | 74.3 | 76.0 | parity; CI spans zero |
| Ideology (utterance) | 63.3 | 65.3 | 64.8 | parity |
| Ideology (document-level) | 65.4 | 82.6 | | 17-point deficit |
| Misinformation | 79.6 | 83.9 | | significant deficit |
| Emotion | 48.4 | 61.9 | | 13.5-point deficit |
| Humor | 56.3 | 69.3 | | 13-point deficit |
| Toxicity prediction (conversation) | 50.2 | 59.0 | | 8.8-point deficit |

Overall: Jev trailed the per-task best LLM on 14 of 15 evaluation tasks, median deficit 11.6 macro-F1
points. It beat mid-size open-weight models (Gemma 4 31B by 3, Qwen3 235B by 2).

Calibration: median expected calibration error 0.157, better than 16 of 19 LLMs' verbalized confidence but
worse than Opus 5 (0.066), Fable 5.1 (0.073), Sonnet 5 (0.075). Per-task variance is large: figurative
language 0.039, empathy 0.538 (78% of items at confidence >= 0.9 with accuracy at the base rate, i.e. the
confidence carried no information). A scalar temperature fit on 50 to 300 labels reduced median ECE from
0.071 to under 0.025 in another test, and also moved several cheap LLMs ahead of Jev on calibration.

Confidence gating at 0.9: 37.6% of items covered at median accuracy 0.815. "Confident items alone are not
accurate enough to keep unconditionally, but the confidence signal retains ranking value on most tasks."

Cascades (Jev first, low-confidence items routed to a partner model):

| Partner | Threshold | Cascade accuracy | Partner alone | Cost vs partner |
|---|---|---|---|---|
| Gemini 3.8 Flash (frontier) | 0.8 | 0.674 | 0.678 | 56% |
| Gemma 4 31B (cheap) | 0.5 | 0.638 | 0.626 | |
| Haiku 4.5 | | 0.639 | 0.622 | 27% |

Cost: $0.027 per 1,000 items, median 44x cheaper than the per-task best LLM; the whole 7,977-item grid
cost $0.21. Zero parsing failures.

Authors' conclusion: decision models "are not yet substitutes for frontier LLM annotation, but can already
serve as an inexpensive first stage of an annotation pipeline, provided their stated confidence is
validated on each construct before it is trusted."

### 2.2 Legal document inference

"Same Scores, Different Decisions", arXiv 2609.27678. ContractNLI: 17 hypotheses per contract, three
labels (entailment / contradiction / not mentioned), 123 contracts.

| Model | Accuracy | Cost per contract |
|---|---|---|
| Jev 1.13 | 77.38% | $0.000228 |
| Gemini 3.5 Flash-Lite | 82.54% | $0.001353 |
| Claude Haiku | 79.44% | |
| Claude Sonnet 5 | 82.40% | |
| Gemini 3.1 Pro | 83.21% | |

Repeated-condition stability: Jev kept the correct label across all 12 repeats on 23 of 30 anchors, Sonnet
on 24 of 30. Jev repeated the same label on 28 of 30 targets, but 5 of those consistent labels were wrong.
Consistency is not correctness.

### 2.3 Other tests

- Spam (18,514 emails): 98.33%, level with a TF-IDF classifier trained on 14,800 labels.
- IMDb sentiment (Raschka): ~96.5% vs ~95% for fine-tuned ModernBERT; 25,000 items in 22 min for $0.65.
- Banking77 intent (77 classes): 75.3 to 84.0% across eight independent runs, best LLM ahead in every run.
- Multi-task 200-item set (Janardhan): Jev 72.5%, Fable 5.1 84.0%, DeepSeek V4.1 Flash 76.0%.
- Non-English: Russian dropped from 88.3% to 77.3%; Spanish 3 to 6 points down.
- Schema compliance: 0 invalid answers in 23,703 calls (guaranteed by construction).

Summary across tests: level with mid-price LLMs, 6 to 12 points behind the frontier, best on binary and
few-class English tasks, worst on document-level and subjective judgments.

## 3. Failure modes relevant to our codebook

From TypeSafe's "Jev 1.13 jaggedness" page and the community robustness audit (awesome-jev-robustness):

| Failure mode | Evidence | Implication for us |
|---|---|---|
| Position bias on value-laden questions | first-listed option gained up to +0.37 probability; arithmetic accuracy 88% with correct answer first vs 57% last | stance items are value-laden: permute option order across runs and average |
| Option names read semantically | swapping which name was bound to which rubric changed 70 answers per 100; AUC 0.81 to 0.58 | names must match rubrics and stay fixed across runs; never use A/B/C |
| Criteria wording is the largest lever | rewording moved paired accuracy 70% to 96% and 83% to 100% | iterate codebook wording against the gold set |
| No abstention option | without "none/unknown", 79% chose a stereotyped answer at 0.79 confidence; 0 of 30 out-of-scope inputs flagged; removing abstain dropped accuracy 0.950 to 0.000 and ECE 0.023 to 0.793 | every stance item needs "not addressed" as a real option; relevance gate needs "irrelevant" |
| Fluent added context flips answers | 61.4% of items flipped when answer-preserving persuasive context was added | essays that report Anthropic's or a philosopher's view at length may be coded as holding it; author-vs-reported needs explicit criteria and validation |
| Irrelevant context is a distractor | documented by TypeSafe; document-level tasks weakest in 2.1 | pass title, subtitle, body as separate structured fields; consider passage-level coding for long essays |
| Literal reading, indirection, double negatives | documented by TypeSafe | write criteria as direct positive statements; one judgment per question |
| Not deterministic | std 0.001 to 0.015 across identical calls; 15 distinct answer sets in 50 identical calls | run 3 times, average probabilities; report variance |
| Noul under-confident, Choice/Score over-confident on identical inputs | robustness audit | don't compare confidence across primitive types; calibrate per question on the gold set |
| Multiple documents per request | 40 rows in one request broke ranking; 53 of 360 rows tied at 0.99 | one post per request |
| No explanations | by design | cannot return the sentence that justified a code; evidence quotes need an LLM |
| No numeric or date reasoning | documented by TypeSafe | do dates, counts, and thresholds in code |

Replicability: Jev is closed, hosted, and two weeks old, with no deprecation policy. This is the same
class of risk as any hosted frontier model, but the vendor is younger. Mitigations: pin `jev-1.13.0`,
store every raw response in `data/raw`, publish the codebook and gold set so the coding can be rerun with
any classifier, and report agreement with a frontier model on the gold set.

## 4. Recommended use in this project

Jev is the cheap first pass in a cascade, not the coder of record.

1. **Relevance gate** (all ~23,400 English 2024+ bodies). One Choice question with the four relevance
   levels plus the "AI but not minds" Noul. Validate against the double-coded gold set (300 to 500 posts).
   Accept above a per-construct confidence threshold chosen on the gold set; route the remainder to a
   frontier model. Expected cost of the Jev pass: a few dollars.
2. **Structural codes** on the relevant subset: genre, claim object, publication community type (state =
   publication name, tagline, author bio, corpus post titles), and the 13 argument-presence Nouls. These
   resemble the tasks where Jev was at parity in 2.1.
3. **Stance items** via cascade. Include "not addressed" and "reports others' view only" as explicit
   options. Measure per-item agreement with the gold set. Keep Jev where it is at parity; where it trails,
   route low-confidence items to a frontier model, or use the frontier model for that item outright.
4. **Sensitivity analysis as a reported result.** With a full pass at ~$4, run: option-order permutations,
   two or three criteria wordings, three repeats. Report the variance. This is cheap here and rare in
   annotation studies.
5. **Evidence extraction stays with an LLM.** For a sample of posts per stance and argument code, have a
   frontier model quote the supporting passage. Jev cannot do this.

Design rules for requests:

- One post per request. State as a JSON object: `{"title", "subtitle", "body"}`, body truncated to fit
  the 32k budget (154 posts affected).
- All codebook questions in one request (parallel evaluation; state tokens are paid once).
- Structured criteria with `what`, `not_for`, `examples` for every option.
- Meaningful, fixed option names that match their rubric.
- An explicit abstain option on every question.
- Store request, response, model id, and timestamp raw.

## 5. Sources

Vendor:
- https://typesafe.ai/blog/introducing-system-one-models-and-jev
- https://docs.typesafe.ai/ (index at https://docs.typesafe.ai/llms.txt)
- https://docs.typesafe.ai/model-jaggedness/jev-1.13
- https://docs.typesafe.ai/primitives/choice.md, .../primitives/advanced.md, .../confidence.md, .../api.md
- https://docs.typesafe.ai/cookbooks/classification_using_confidence.md
- https://docs.typesafe.ai/sdk/python/usage.md

Specs and hosting:
- https://systemonemodels.org/models/jev/
- https://developers.cloudflare.com/ai/models/typesafe/jev
- https://www.digitalocean.com/resources/articles/what-is-jev
- https://jevaiguide.com/get-jev-api-key/

Independent evaluations:
- Ibrahim & Zaki, Evaluating Decision Models for Text Annotation in Computational Social Science, arXiv 2609.24574: https://arxiv.org/html/2609.24574v1
- Same Scores, Different Decisions: Evaluating JEV and Language Models for Legal Document Understanding, arXiv 2609.27678: https://arxiv.org/html/2609.27678v1
- Jev After Eight Days of Independent Tests: https://dev.to/aws-builders/jev-after-eight-days-of-independent-tests-level-with-mid-price-llms-behind-the-frontier-1c60
- awesome-jev-robustness: https://github.com/GautamTalksDev/awesome-jev-robustness
- Paul Simmering, Jev for Computational Social Science: https://simmering.dev/blog/jev-css/
- Sebastian Raschka, From Bag-of-Words to Jev: https://magazine.sebastianraschka.com/p/classifier-history-and-jev
- LangChain, Can Jev Be a Better Agent Evaluator?: https://www.langchain.com/blog/jev-agent-evals-langsmith
- Arize, Can Decision Models Replace LLM Judges?: https://arize.com/blog/typesafe-jev-llm-judge/

Commentary:
- Simon Willison: https://simonwillison.net/2026/Sep/21/jev
- KDnuggets: https://www.kdnuggets.com/what-everyone-is-getting-wrong-about-typesafe-ais-jev
- Wikipedia: https://en.wikipedia.org/wiki/Jev_(AI_model)
