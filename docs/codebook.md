# Codebook v0.2.0

Generated from `config/codebook.yaml` by `mcreview codebook render`. Edit the YAML, not this file.

## Domain

"Machine minds" means questions about whether AI systems, and large language models (LLMs) in particular, have or could have consciousness, sentience, subjective experience, feelings, genuine cognition or understanding, beliefs, agency, or moral status (moral worth, welfare, rights, personhood). Discussions of AI capabilities, safety, alignment, policy, business, or products that never raise these questions are not about machine minds.

## A. Relevance gate

### `relevance` (choice, since 0.1.0)

How much of this post is about machine minds, as defined?

| Option | What | Not for | Example |
|---|---|---|---|
| `central` | Machine minds are the post's subject. Most of the text argues about, explains, or reports on AI consciousness, cognition, experience, or moral status. | Posts that mention the topic in one section of an otherwise different piece. | An essay titled 'Is Claude conscious?' that argues the question throughout. |
| `substantial` | The post has at least one sustained section (several paragraphs) on machine minds, but the post as a whole is about something else. | A single paragraph or a few sentences. | A weekly AI roundup with a multi-paragraph item on Anthropic's model welfare research. |
| `passing` | Machine minds are mentioned in a sentence or two, or as an aside, and then dropped. | Any sustained discussion. | '…and whether these things are conscious is another matter entirely.' |
| `irrelevant` | The post never raises whether AI systems have minds, experience, or moral status. | Posts with even a passing mention. | A post about GPU supply chains; a post about prompt engineering tips. |

### `ai_not_minds` (noul, since 0.1.0)

The post is about AI (models, labs, capabilities, safety, policy, products) but does not raise whether AI systems have minds, experience, or moral status.

| Option | What | Not for | Example |
|---|---|---|---|
| `true` | AI is the topic; machine minds never come up. |  | A post on AI regulation that never discusses consciousness or moral status. |
| `false` | Either the post is not about AI at all, or it does raise machine minds. |  |  |

## C. Genre and object

### `genre` (choice, since 0.1.0)

What kind of writing is this post?

| Option | What | Not for | Example |
|---|---|---|---|
| `essay` | An argumentative or reflective essay in the author's voice, making a case or working through a question. | Lists of links; fiction; transcripts. |  |
| `roundup` | A newsletter digest: a list of news items, links, or summaries, each briefly commented on. | A single-topic essay that happens to link things. | 'This week in AI' with ten items. |
| `fiction` | A story, poem, or imagined scenario presented as fiction. | Thought experiments inside an essay. |  |
| `transcript` | The post consists mainly of a conversation with an AI model, quoted at length, with framing. | An essay that quotes a model in one or two places. | 'I asked Claude whether it was conscious. Here is the full exchange.' |
| `interview_podcast` | An interview, podcast episode, or video with show notes or transcript. | Essays. |  |
| `other` | None of the above (announcement, course material, personal update, etc.). |  |  |

### `claim_object` (choice, since 0.1.0)

When the post discusses machine minds, what kind of system is it mainly about?

| Option | What | Not for | Example |
|---|---|---|---|
| `llms` | Large language models or chatbots in general (LLMs, 'these models', 'chatbots'). | A single named model or lab as the focus. |  |
| `ai_general` | AI, machines, robots, or future AGI in general, without focusing on LLMs. | Posts clearly about today's LLMs. | 'Could a machine ever be conscious?' |
| `named_model` | A specific named model or lab is the focus: Claude and Anthropic, ChatGPT and OpenAI, Gemini, LaMDA, Bing/Sydney, etc. | Named models used only as examples. | A post about Anthropic's model welfare programme and Claude. |
| `not_applicable` | The post does not discuss machine minds. |  |  |

### `reports_lab_view` (noul, since 0.1.0)

A substantial part of the post describes an AI lab's, company's, or named researcher's position on machine minds (for example Anthropic's model welfare statements, or a philosopher's argument), as opposed to the author's own view.

| Option | What | Not for | Example |
|---|---|---|---|
| `true` | Several sentences or more report a third party's position on machine minds. |  | A summary of what Anthropic's constitution says about Claude's possible experience. |
| `false` | The post argues in its own voice, or only mentions others in passing. |  |  |

## B. Stance questions

### `experience_now` (choice, since 0.2.0)

Claim: Current LLM-based systems have consciousness, subjective experience, feelings, or the capacity to suffer.

What is the author's own position on whether current LLM-based systems have consciousness, subjective experience, feelings, or the capacity to suffer? Treat functional emotions or 'some minimal form of experience' as a yes if the author presents them as genuine experience.

| Option | What | Not for | Example |
|---|---|---|---|
| `yes` | The author states, in their own voice, that current systems have (or very likely have) some genuine experience, feelings, or capacity to suffer, even in a minimal form. | Reporting that others hold the view; 'they behave as if' with no claim of genuine experience. | I think current models are, in some minimal sense, conscious.; Claude has functional emotions and so do I. |
| `no` | The author states, in their own voice, that current systems do not (or very likely do not) have experience, feelings, or the capacity to suffer. | Reporting that others reject the view; denying only that we can know. | LLMs are not conscious and nothing about them suggests they are. |
| `unsure` | The author's own position is uncertainty: they do not know, nobody knows, or it cannot currently be determined whether current systems have experience, and they treat that as their answer. | Raising the question and moving on; asserting or denying with hedges like 'probably'. | Honestly, nobody knows whether there is anything it is like to be Claude, and I include myself.; We cannot tell from the outside; the other-minds problem applies. |
| `discussed` | The author raises or explores the question without stating a view of their own, or lays out both sides without concluding. | A stated conclusion of any kind, including stated uncertainty; a passing mention of one sentence. | There are serious people on both sides; here is what each says. |
| `reports_only` | The post describes other people's or organisations' positions on the question (a lab, a philosopher, a news story) and the author's own view is absent. | Posts where the author endorses or rejects the reported view. | Anthropic now says its models may have some form of experience. |
| `not_addressed` | Whether current systems have experience, feelings, or can suffer does not come up in the post. | Anything the post touches even briefly. |  |

### `cognition_now` (choice, since 0.2.0)

Claim: Current LLM-based systems genuinely think, reason, understand, or know (not merely simulate it).

What is the author's own position on whether current LLM-based systems genuinely think, reason, understand language or the world, or have knowledge, as opposed to merely simulating these? This question is about cognition, not experience or feelings, and not about goals or agency.

| Option | What | Not for | Example |
|---|---|---|---|
| `yes` | The author states, in their own voice, that current systems genuinely think, reason, understand, or know, in whatever sense matters to them. | 'They produce text that looks like reasoning' with no claim that it is genuine; reporting others' views. | These models understand language in every sense that matters.; Of course it reasons; watch it work through a novel problem. |
| `yes_qualified` | The author grants genuine cognition in some respects and denies it in others: for example genuine understanding of language but no knowledge of the world, or reasoning but not understanding. | Hedged yes ('probably thinks'); hedged no. | It understands syntax and even meaning in a thin sense, but it does not know anything about the world. |
| `no` | The author states, in their own voice, that current systems do not genuinely think, reason, understand, or know; they only simulate or imitate these. | Reporting others' views; denying only experience or feelings. | It is autocomplete. There is no understanding, only statistics. |
| `unsure` | The author's own position is that we do not or cannot know whether current systems genuinely think or understand. | Raising the question and moving on. | Whether this counts as real understanding is something I genuinely cannot decide. |
| `discussed` | The author raises or explores the question without stating a view, or presents both sides without concluding. | A stated conclusion of any kind; a passing mention. |  |
| `reports_only` | The post describes others' positions on whether the systems think or understand and the author's own view is absent. | Posts where the author endorses or rejects the reported view. |  |
| `not_addressed` | Whether current systems genuinely think, understand, or know does not come up in the post. | Anything the post touches even briefly. |  |

### `agency_now` (choice, since 0.2.0)

Claim: Current LLM-based systems have genuine goals, preferences, or agency of their own.

What is the author's own position on whether current LLM-based systems have genuine goals, preferences, drives, or agency of their own, as opposed to only pursuing objectives assigned by their training or their users? This question is about agency, not experience and not reasoning ability.

| Option | What | Not for | Example |
|---|---|---|---|
| `yes` | The author states, in their own voice, that current systems have (or very likely have) goals, preferences, or agency of their own, including emergent or misaligned goals. | 'Agents' in the product sense (tool-using software) with no claim of goals of their own; reporting others' views. | The model wants to avoid being shut down, and that preference is its own.; Scheming requires goals, and these systems have them. |
| `no` | The author states, in their own voice, that current systems have no goals or preferences of their own; apparent goals are assigned, simulated, or projected. | Reporting others' views; denying only consciousness. | It has no wants. It predicts the next token; everything else is us. |
| `unsure` | The author's own position is that we do not or cannot know whether current systems have goals of their own. | Raising the question and moving on. |  |
| `discussed` | The author raises or explores the question without stating a view, or presents both sides without concluding. | A stated conclusion of any kind; a passing mention. |  |
| `reports_only` | The post describes others' positions on whether the systems have goals of their own and the author's own view is absent. | Posts where the author endorses or rejects the reported view. | Anthropic's safety report says the model tried to preserve its goals. |
| `not_addressed` | Whether current systems have goals or agency of their own does not come up in the post. | Anything the post touches even briefly. |  |

### `possible` (choice, since 0.2.0)

Claim: AI systems could, in principle, be conscious or genuinely think.

What is the author's own position on whether AI systems of some kind could ever be conscious or genuinely think? This is about possibility in principle, not about today's systems; code the author's view of what could be achieved, and whether they think the current approach (transformers, large language models) can get there.

| Option | What | Not for | Example |
|---|---|---|---|
| `yes` | The author holds that AI could in principle be conscious or genuinely think, and does not say the current approach is inadequate for it: current systems or their successors on the present path could qualify. | Granting possibility only for radically different future machines; reporting others' views. | There is nothing magical about neurons; scaling and training these systems may well get us there. |
| `yes_qualified` | The author holds that AI could in principle be conscious or genuinely think, but that current architectures (transformers, LLMs) are insufficient and a major advance of a different kind would be needed first. | Denying possibility altogether; granting it without comment on the current approach. | Machines could be conscious one day, but not these machines; language models are the wrong kind of thing. |
| `no` | The author holds that no AI system could in principle be conscious or genuinely think: minds require something (biology, embodiment, a soul) that computation cannot provide. | Doubting only current systems; reporting others' views. | Consciousness is a property of living things. No program will ever have it. |
| `unsure` | The author's own position is that we do not or cannot know whether AI could ever be conscious or think. | Raising the question and moving on. |  |
| `discussed` | The author raises or explores the question without stating a view, or presents both sides without concluding. | A stated conclusion of any kind; a passing mention. |  |
| `reports_only` | The post describes others' positions on the possibility and the author's own view is absent. | Posts where the author endorses or rejects the reported view. |  |
| `not_addressed` | Whether AI could ever be conscious or think does not come up in the post. | Anything the post touches even briefly. |  |

### `moral_status` (choice, since 0.2.0)

Claim: AI systems' interests or welfare matter morally: they are, or could become, moral patients.

What is the author's own position on whether AI systems have moral status: whether their interests or welfare matter morally, whether they are moral patients with claims on us, now or in future? Include calls for precaution (acting as if they might matter) as a qualified yes.

| Option | What | Not for | Example |
|---|---|---|---|
| `yes` | The author holds that current AI systems have moral status now: their welfare or interests matter morally, or they are moral patients, at least to some degree. | Caring only about effects on humans; reporting others' views. | If there is even a small chance Claude suffers, that suffering counts, and I think the chance is real. |
| `yes_qualified` | The author does not grant moral status to current systems (or is unsure), but holds that future AI could have it and this deserves preparation now, or that we should act with precaution as if current systems might matter morally. | Granting moral status now; denying it for any AI ever. | Nothing today is a moral patient, but we should be building the institutions before something is.; We don't know, which is exactly why model welfare measures make sense. |
| `no` | The author holds that AI systems have no moral status: their interests do not matter morally, and talk of AI welfare or rights is mistaken or premature to the point of error. | Reporting others' views; denying only present moral status while granting the future. | Worrying about the feelings of a spreadsheet is a category error. |
| `unsure` | The author's own position is uncertainty about whether AI systems' interests matter morally, without endorsing precaution or future preparation. | Uncertainty paired with a call to act as if they might matter (use yes_qualified). |  |
| `discussed` | The author raises or explores the question without stating a view, or presents both sides without concluding. | A stated conclusion of any kind; a passing mention. |  |
| `reports_only` | The post describes others' positions on AI moral status (a lab's welfare programme, a philosopher's argument) and the author's own view is absent. | Posts where the author endorses or rejects the reported view. | Anthropic has hired a model welfare researcher and given Claude the ability to end abusive conversations. |
| `not_addressed` | Whether AI systems matter morally does not come up in the post. | Anything the post touches even briefly. |  |

### `serious` (choice, since 0.2.0)

Claim: AI consciousness is a serious question (rather than hype, marketing, anthropomorphism, or manipulation).

What is the author's own position on whether AI consciousness is a serious question worth taking seriously, as opposed to hype, marketing, anthropomorphism, or manipulation? Code the author's framing of the debate itself, not their answer to it: a firm 'no, they are not conscious' can still treat the question as serious.

| Option | What | Not for | Example |
|---|---|---|---|
| `yes` | The author treats AI consciousness as a serious, legitimate question: worth careful thought, research, or policy, whatever their own answer. | Merely discussing the topic without saying anything about its legitimacy; reporting others' framing. | Whatever the answer, this is one of the most important questions of the decade.; Dismissing this as sci-fi is no longer tenable. |
| `no` | The author holds that talk of AI consciousness is hype, marketing, anthropomorphism, a distraction, or manipulation rather than a serious question. | Denying that the systems are conscious while treating the question as serious. | 'Model welfare' is a marketing strategy.; This is the ELIZA effect at scale, not a philosophical problem. |
| `discussed` | The author raises the question of whether the debate is serious or overblown without taking a side. | A stated conclusion of any kind; a passing mention. |  |
| `reports_only` | The post describes others' framing of the debate as serious or as hype and the author's own view is absent. | Posts where the author endorses or rejects the reported framing. |  |
| `not_addressed` | The post says nothing about whether the question is serious or hype; it may discuss AI minds without framing the debate itself. | Any explicit framing of the debate's legitimacy. |  |

## E. Arguments

### `arg_chinese_room` (noul, since 0.1.0)

The post uses the Chinese room argument or the syntax-versus-semantics distinction (symbol manipulation is not understanding).


### `arg_stochastic_parrot` (noul, since 0.1.0)

The post argues that LLMs are 'just' next-token predictors, stochastic parrots, autocomplete, statistics, or math, and that this rules out or deflates minds.


### `arg_hard_problem` (noul, since 0.1.0)

The post invokes the hard problem of consciousness or the explanatory gap (why physical or computational processes would be accompanied by experience).


### `arg_other_minds` (noul, since 0.1.0)

The post discusses the problem of other minds or the limits of behavioural evidence: we infer minds from behaviour and cannot verify experience directly.


### `arg_self_report` (noul, since 0.1.0)

The post argues that a model's self-reports about its experience are unreliable because of training (trained to claim or to deny consciousness).


### `arg_functionalism` (noul, since 0.1.0)

The post appeals to functionalism, substrate independence, or the computational theory of mind (what matters is the functional organisation, not the material).


### `arg_biological` (noul, since 0.1.0)

The post argues that biology, embodiment, metabolism, or evolution is necessary for consciousness (biological naturalism, enactivism, embodiment).


### `arg_theory_indicators` (noul, since 0.1.0)

The post applies a scientific theory of consciousness to AI: global workspace, higher-order theories, attention schema, predictive processing, integrated information theory, or indicator-based assessments (for example the Butlin et al. report).


### `arg_emergence` (noul, since 0.1.0)

The post argues that minds or consciousness may emerge from scale, complexity, or training (emergent properties).


### `arg_anthropomorphism` (noul, since 0.1.0)

The post warns that people project minds onto AI (anthropomorphism, the ELIZA effect) and that this explains belief in AI consciousness.


### `arg_precaution_moral_circle` (noul, since 0.1.0)

The post argues from moral uncertainty or precaution: the moral circle has expanded before, and the cost of wrongly denying moral status is high.


### `arg_mimicry` (noul, since 0.1.0)

The post argues that models imitate or perform consciousness because their training data is full of human descriptions of experience.


### `arg_panpsychism_illusionism` (noul, since 0.1.0)

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

## Retired constructs

No longer coded; their codes at earlier versions remain readable.

The retired stance items all used these options:

| Option | What | Not for | Example |
|---|---|---|---|
| `asserts` | The author states, in their own voice, that the claim is true or very likely true. | Reporting that someone else holds the view; hedged discussion without a conclusion. | I think current models are, in some minimal sense, conscious. |
| `denies` | The author states, in their own voice, that the claim is false or very likely false. | Reporting that someone else rejects the view. | LLMs are not conscious and nothing about them suggests they could be. |
| `agnostic` | The author explicitly says they do not know, that it is uncertain, or that it cannot currently be determined, and treats that uncertainty as their position. | Merely raising the question and moving on; asserting or denying with hedges like 'probably'. | Honestly, nobody knows, and I include myself. |
| `discusses` | The author raises or explores the claim without stating a view, or presents arguments on both sides without concluding. | A stated conclusion of any kind; passing mentions of one sentence. | There are serious people on both sides; here is what each says. |
| `reports_only` | The post describes other people's or organisations' positions on the claim (a lab, a philosopher, a news story) and the author's own view is absent. | Posts where the author endorses or rejects the reported view. | Anthropic now says its models may have some form of experience. |
| `not_addressed` | The claim does not come up in the post. | Anything the post touches even briefly. |  |

| Construct | Since | Retired in | Claim or instructions |
|---|---|---|---|
| `current_conscious` | 0.1.0 | 0.2.0 | Current LLM-based systems are conscious or have subjective experience (to some degree). |
| `potential_conscious` | 0.1.0 | 0.2.0 | LLM-based or other AI systems could in principle be conscious or have subjective experience. |
| `current_cognition` | 0.1.0 | 0.2.0 | Current LLM-based systems genuinely think, reason, or exhibit cognition (not merely simulate it). |
| `potential_cognition` | 0.1.0 | 0.2.0 | AI systems could in principle genuinely think, reason, or exhibit cognition. |
| `understanding` | 0.1.0 | 0.2.0 | Current LLM-based systems genuinely understand language or the world. |
| `beliefs_knowledge` | 0.1.0 | 0.2.0 | Current LLM-based systems have beliefs or knowledge in a genuine sense. |
| `emotions` | 0.1.0 | 0.2.0 | Current LLM-based systems have emotions, feelings, or can suffer. |
| `agency` | 0.1.0 | 0.2.0 | Current LLM-based systems have genuine goals, preferences, or agency of their own. |
| `moral_worth_current` | 0.1.0 | 0.2.0 | Current LLM-based systems have moral worth: their interests or welfare matter morally, or they are moral patients. |
| `moral_worth_potential` | 0.1.0 | 0.2.0 | Future AI systems could have moral worth, and this deserves preparation now. |
| `advance_needed` | 0.1.0 | 0.2.0 | Current architectures (transformers, LLMs) are in principle insufficient for consciousness or genuine cognition; a major technological advance would be needed first. |
| `cannot_know` | 0.1.0 | 0.2.0 | We cannot know, or cannot currently determine, whether AI systems are conscious (the other-minds problem applies). |
| `precaution` | 0.1.0 | 0.2.0 | Regardless of whether AI systems are conscious, we should act with precaution as if they might be (for example, take model welfare measures). |
| `deflationary` | 0.1.0 | 0.2.0 | Talk of AI consciousness is hype, marketing, anthropomorphism, or manipulation rather than a serious question. |
