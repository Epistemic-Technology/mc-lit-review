# Codebook v0.1.0

Generated from `config/codebook.yaml` by `mcreview codebook render`. Edit the YAML, not this file.

## Domain

"Machine minds" means questions about whether AI systems, and large language models (LLMs) in particular, have or could have consciousness, sentience, subjective experience, feelings, genuine cognition or understanding, beliefs, agency, or moral status (moral worth, welfare, rights, personhood). Discussions of AI capabilities, safety, alignment, policy, business, or products that never raise these questions are not about machine minds.

## A. Relevance gate

### `relevance` (choice)

How much of this post is about machine minds, as defined?

| Option | What | Not for | Example |
|---|---|---|---|
| `central` | Machine minds are the post's subject. Most of the text argues about, explains, or reports on AI consciousness, cognition, experience, or moral status. | Posts that mention the topic in one section of an otherwise different piece. | An essay titled 'Is Claude conscious?' that argues the question throughout. |
| `substantial` | The post has at least one sustained section (several paragraphs) on machine minds, but the post as a whole is about something else. | A single paragraph or a few sentences. | A weekly AI roundup with a multi-paragraph item on Anthropic's model welfare research. |
| `passing` | Machine minds are mentioned in a sentence or two, or as an aside, and then dropped. | Any sustained discussion. | '…and whether these things are conscious is another matter entirely.' |
| `irrelevant` | The post never raises whether AI systems have minds, experience, or moral status. | Posts with even a passing mention. | A post about GPU supply chains; a post about prompt engineering tips. |

### `ai_not_minds` (noul)

The post is about AI (models, labs, capabilities, safety, policy, products) but does not raise whether AI systems have minds, experience, or moral status.

| Option | What | Not for | Example |
|---|---|---|---|
| `true` | AI is the topic; machine minds never come up. |  | A post on AI regulation that never discusses consciousness or moral status. |
| `false` | Either the post is not about AI at all, or it does raise machine minds. |  |  |

## C. Genre and object

### `genre` (choice)

What kind of writing is this post?

| Option | What | Not for | Example |
|---|---|---|---|
| `essay` | An argumentative or reflective essay in the author's voice, making a case or working through a question. | Lists of links; fiction; transcripts. |  |
| `roundup` | A newsletter digest: a list of news items, links, or summaries, each briefly commented on. | A single-topic essay that happens to link things. | 'This week in AI' with ten items. |
| `fiction` | A story, poem, or imagined scenario presented as fiction. | Thought experiments inside an essay. |  |
| `transcript` | The post consists mainly of a conversation with an AI model, quoted at length, with framing. | An essay that quotes a model in one or two places. | 'I asked Claude whether it was conscious. Here is the full exchange.' |
| `interview_podcast` | An interview, podcast episode, or video with show notes or transcript. | Essays. |  |
| `other` | None of the above (announcement, course material, personal update, etc.). |  |  |

### `claim_object` (choice)

When the post discusses machine minds, what kind of system is it mainly about?

| Option | What | Not for | Example |
|---|---|---|---|
| `llms` | Large language models or chatbots in general (LLMs, 'these models', 'chatbots'). | A single named model or lab as the focus. |  |
| `ai_general` | AI, machines, robots, or future AGI in general, without focusing on LLMs. | Posts clearly about today's LLMs. | 'Could a machine ever be conscious?' |
| `named_model` | A specific named model or lab is the focus: Claude and Anthropic, ChatGPT and OpenAI, Gemini, LaMDA, Bing/Sydney, etc. | Named models used only as examples. | A post about Anthropic's model welfare programme and Claude. |
| `not_applicable` | The post does not discuss machine minds. |  |  |

### `reports_lab_view` (noul)

A substantial part of the post describes an AI lab's, company's, or named researcher's position on machine minds (for example Anthropic's model welfare statements, or a philosopher's argument), as opposed to the author's own view.

| Option | What | Not for | Example |
|---|---|---|---|
| `true` | Several sentences or more report a third party's position on machine minds. |  | A summary of what Anthropic's constitution says about Claude's possible experience. |
| `false` | The post argues in its own voice, or only mentions others in passing. |  |  |

## B. Stance items

Every stance item uses the same options:

| Option | What | Not for | Example |
|---|---|---|---|
| `asserts` | The author states, in their own voice, that the claim is true or very likely true. | Reporting that someone else holds the view; hedged discussion without a conclusion. | I think current models are, in some minimal sense, conscious. |
| `denies` | The author states, in their own voice, that the claim is false or very likely false. | Reporting that someone else rejects the view. | LLMs are not conscious and nothing about them suggests they could be. |
| `agnostic` | The author explicitly says they do not know, that it is uncertain, or that it cannot currently be determined, and treats that uncertainty as their position. | Merely raising the question and moving on; asserting or denying with hedges like 'probably'. | Honestly, nobody knows, and I include myself. |
| `discusses` | The author raises or explores the claim without stating a view, or presents arguments on both sides without concluding. | A stated conclusion of any kind; passing mentions of one sentence. | There are serious people on both sides; here is what each says. |
| `reports_only` | The post describes other people's or organisations' positions on the claim (a lab, a philosopher, a news story) and the author's own view is absent. | Posts where the author endorses or rejects the reported view. | Anthropic now says its models may have some form of experience. |
| `not_addressed` | The claim does not come up in the post. | Anything the post touches even briefly. |  |

| Item | Claim |
|---|---|
| `current_conscious` | Current LLM-based systems are conscious or have subjective experience (to some degree). |
| `potential_conscious` | LLM-based or other AI systems could in principle be conscious or have subjective experience. |
| `current_cognition` | Current LLM-based systems genuinely think, reason, or exhibit cognition (not merely simulate it). |
| `potential_cognition` | AI systems could in principle genuinely think, reason, or exhibit cognition. |
| `understanding` | Current LLM-based systems genuinely understand language or the world. |
| `beliefs_knowledge` | Current LLM-based systems have beliefs or knowledge in a genuine sense. |
| `emotions` | Current LLM-based systems have emotions, feelings, or can suffer. |
| `agency` | Current LLM-based systems have genuine goals, preferences, or agency of their own. |
| `moral_worth_current` | Current LLM-based systems have moral worth: their interests or welfare matter morally, or they are moral patients. |
| `moral_worth_potential` | Future AI systems could have moral worth, and this deserves preparation now. |
| `advance_needed` | Current architectures (transformers, LLMs) are in principle insufficient for consciousness or genuine cognition; a major technological advance would be needed first. |
| `cannot_know` | We cannot know, or cannot currently determine, whether AI systems are conscious (the other-minds problem applies). |
| `precaution` | Regardless of whether AI systems are conscious, we should act with precaution as if they might be (for example, take model welfare measures). |
| `deflationary` | Talk of AI consciousness is hype, marketing, anthropomorphism, or manipulation rather than a serious question. |

## E. Arguments

### `arg_chinese_room` (noul)

The post uses the Chinese room argument or the syntax-versus-semantics distinction (symbol manipulation is not understanding).


### `arg_stochastic_parrot` (noul)

The post argues that LLMs are 'just' next-token predictors, stochastic parrots, autocomplete, statistics, or math, and that this rules out or deflates minds.


### `arg_hard_problem` (noul)

The post invokes the hard problem of consciousness or the explanatory gap (why physical or computational processes would be accompanied by experience).


### `arg_other_minds` (noul)

The post discusses the problem of other minds or the limits of behavioural evidence: we infer minds from behaviour and cannot verify experience directly.


### `arg_self_report` (noul)

The post argues that a model's self-reports about its experience are unreliable because of training (trained to claim or to deny consciousness).


### `arg_functionalism` (noul)

The post appeals to functionalism, substrate independence, or the computational theory of mind (what matters is the functional organisation, not the material).


### `arg_biological` (noul)

The post argues that biology, embodiment, metabolism, or evolution is necessary for consciousness (biological naturalism, enactivism, embodiment).


### `arg_theory_indicators` (noul)

The post applies a scientific theory of consciousness to AI: global workspace, higher-order theories, attention schema, predictive processing, integrated information theory, or indicator-based assessments (for example the Butlin et al. report).


### `arg_emergence` (noul)

The post argues that minds or consciousness may emerge from scale, complexity, or training (emergent properties).


### `arg_anthropomorphism` (noul)

The post warns that people project minds onto AI (anthropomorphism, the ELIZA effect) and that this explains belief in AI consciousness.


### `arg_precaution_moral_circle` (noul)

The post argues from moral uncertainty or precaution: the moral circle has expanded before, and the cost of wrongly denying moral status is high.


### `arg_mimicry` (noul)

The post argues that models imitate or perform consciousness because their training data is full of human descriptions of experience.


### `arg_panpsychism_illusionism` (noul)

The post invokes panpsychism (consciousness is fundamental or ubiquitous) or illusionism (consciousness as normally conceived is an illusion) in relation to AI.


## Publication constructs

### `community` (choice)

What kind of publication is this, judging from its name, tagline, author bio, and post titles? A specialist label is earned in either of two ways: the author shows an identity signal (an academic post, a lab or company role, membership in a named community, a religious vocation), or the post titles show that the publication's recurring subject is that domain (most titles are philosophy, or AI industry news, or theology). Use culture_general when the titles range across unrelated topics and no identity signal points to a specialist label.

| Option | What | Not for | Example |
|---|---|---|---|
| `ai_industry` | AI industry, practitioner, or product commentary by people working in or on AI: labs, startups, engineering, investing, tooling, model news. | Academic research writing; general commentators who write about AI among other things (use culture_general). | A VC's weekly AI newsletter; an ML engineer's blog. |
| `academic_philosophy` | Philosophy as the publication's subject: the author has academic philosophy signals (university post, philosophy PhD, philosophy publications), or most post titles are philosophical arguments and analyses. | Essayists whose philosophical posts sit among unrelated topics (use culture_general). | A philosophy professor's Substack; a newsletter whose titles are mostly about consciousness, free will, and ethics. |
| `academic_science` | Neuroscience, cognitive science, psychology, or other science written by or for researchers, with signals of a research role. | Science journalism or science-flavoured essays for a general audience (use culture_general or journalism_politics). |  |
| `rationalist_ea` | Writing from within the rationalist, effective altruism, AI safety, or longtermist communities: names those communities or their venues, or the author works in AI alignment. | General writers who discuss AI risk without those community signals (use culture_general); mainstream AI industry newsletters. | A LessWrong-adjacent blog; an AI alignment researcher's newsletter. |
| `religion_spirituality` | A religious, theological, or spiritual frame is the publication's identity: clergy, theology, a named tradition, or explicitly spiritual practice as the recurring subject. | General essays that touch on meaning or spirituality among other topics (use culture_general). |  |
| `culture_general` | Culture, literature, essays, personal writing, or general commentary for a broad audience: the post titles range across unrelated topics and no identity signal points to a specialist label. | Publications whose titles show one recurring specialist subject, or whose author has a specialist identity signal. | A writer's essay newsletter that ranges over AI, books, politics, and family life. |
| `journalism_politics` | News, journalism, politics, or policy as the main frame. |  |  |
| `business_finance` | Business, finance, markets, or management, with AI as one topic among others. | AI-specialist newsletters (use ai_industry). |  |
| `other` | None of the above, or too little information to tell. |  |  |
