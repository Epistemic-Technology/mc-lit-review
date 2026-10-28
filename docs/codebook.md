# Codebook v0.4.1

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

## D. Change of view

### `view_revised` (choice, since 0.3.1)

Does the author report, in their own voice, that their OWN view on whether AI systems have or could have minds (consciousness, experience, genuine cognition, agency, or moral status) has changed, and in which direction? Code a change only when the post states BOTH a view the author held before writing it AND the different view they hold now, and both views are about whether AI systems have or could have minds. The earlier view must be a position the author held, not a first impression that the post itself overturns: a shift that happens inside the events the post narrates (an experiment, a conversation with a model, a test, reading the work under discussion, an earlier draft) is not a change of view unless the author presents it as overturning a position held before the post. Do not code changes of mind about related matters (terminology, which argument is decisive, whether the question matters or is well posed, how to study it, AI capabilities, alignment, economics); changes reported for other people, a quoted expert, a lab, or a model; first-person hypotheticals ('if I were to change my mind'); or any post whose first-person voice is an AI persona, whether or not it is presented as fiction. The evidence quote must include the sentence that states the earlier view.

| Option | What | Not for | Example |
|---|---|---|---|
| `toward_minds` | The author once gave less credence to AI systems having (or being able to have) experience, genuine cognition, agency, or moral status than they do now: from no to yes, from no to unsure, from dismissal to taking the question seriously. Both the earlier and the present position are stated. | A present view with no stated earlier view ('I came to this reluctantly', 'I never expected to write this'); a first impression overturned within the post ('at first I assumed it was mimicry, but by the end of the session...'); a change someone else reports; a hypothetical; an AI persona's own change of mind. | Last year I insisted ChatGPT was far from intelligent and never could achieve consciousness. Now I'm beginning to question myself.; In an earlier essay I argued that AI systems possess no interior. That claim has aged badly.; Going into this I was about 70% confident AIs could be conscious; I've gone up to about 80%. |
| `away_from_minds` | The author once gave more credence than they do now: from yes to no, from yes to unsure, from taking the question seriously to treating it as hype. Both the earlier and the present position are stated. | A present view with no stated earlier view; a first impression overturned within the post; a change someone else reports; a hypothetical; an AI persona's own change of mind. | For a long time I took it for granted that a sufficiently advanced AI could be a conscious person. I no longer think so.; I would have defended computational functionalism five years ago. Now I'm not confident enough to make a decisive judgement.; For three months I was fooled by the chatbots and thought there was intelligence in their output. |
| `none` | The author does not report a change in their own view on whether AI systems have or could have minds. Includes a steady position; a change on a related matter (terminology, framing, which argument counts, whether the question matters, capabilities, economics); a shift inside the post's own narrative; a present view with no stated earlier view; changes reported for other people; and posts in an AI persona's voice. |  | Hinton says he used to think this was decades away and now thinks it is here.  (someone else's change: none); I no longer think the consciousness question is the right one to centre the debate on.  (framing, not credence: none); I went in intending to debunk it and I'm reporting the drift anyway.  (shift inside the post's own experiment: none) |

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


## F. Features of AI systems pointed to

### `feat_prediction_objective` (choice, since 0.4.0)

Feature: the training objective: next-token prediction, 'just statistics', 'just math', 'autocomplete', probability distributions over words. Does the author point to this feature as bearing on whether AI systems have or could have minds, and in which direction? Count the feature only when the post connects it to that question.

| Option | What | Not for | Example |
|---|---|---|---|
| `for` | The author points to this feature as a reason to think the system has, or could have, a mind (experience, genuine cognition, agency of its own, or moral status), or as making such claims more credible. | Reporting someone else's use of the feature without endorsing it (both_or_neutral); a mention of the feature unconnected to whether the system has a mind (not_cited). | Predicting the next word this well requires modelling the world and the speaker; that is understanding, whatever we call it. |
| `against` | The author points to this feature as a reason to think the system lacks a mind, or as deflating or undermining such claims. | Reporting someone else's use of the feature without endorsing it (both_or_neutral); a mention of the feature unconnected to whether the system has a mind (not_cited). | It is autocomplete. There is no understanding, only statistics. |
| `both_or_neutral` | The author raises the feature as relevant to whether the system has a mind without giving it a direction: argues it cuts both ways, treats it as changing the question, or reports others citing it without taking a side. | A feature the author uses in one direction; a feature not connected to minds. |  |
| `not_cited` | The feature is not connected to whether the system has a mind. It may be mentioned for other reasons (a product review, a capabilities roundup, a safety discussion) or not at all. |  |  |

### `feat_architecture` (choice, since 0.4.0)

Feature: the model's internal architecture: transformer layers, attention, a single feed-forward pass, no recurrence, weights frozen after training, discrete tokens, computation on GPUs. Does the author point to this feature as bearing on whether AI systems have or could have minds, and in which direction? Count the feature only when the post connects it to that question.

| Option | What | Not for | Example |
|---|---|---|---|
| `for` | The author points to this feature as a reason to think the system has, or could have, a mind (experience, genuine cognition, agency of its own, or moral status), or as making such claims more credible. | Reporting someone else's use of the feature without endorsing it (both_or_neutral); a mention of the feature unconnected to whether the system has a mind (not_cited). | Attention over the whole context is a kind of global workspace; the architecture has the ingredients the theories ask for. |
| `against` | The author points to this feature as a reason to think the system lacks a mind, or as deflating or undermining such claims. | Reporting someone else's use of the feature without endorsing it (both_or_neutral); a mention of the feature unconnected to whether the system has a mind (not_cited). | A feed-forward pass with no recurrence and frozen weights has no place for experience to happen. |
| `both_or_neutral` | The author raises the feature as relevant to whether the system has a mind without giving it a direction: argues it cuts both ways, treats it as changing the question, or reports others citing it without taking a side. | A feature the author uses in one direction; a feature not connected to minds. |  |
| `not_cited` | The feature is not connected to whether the system has a mind. It may be mentioned for other reasons (a product review, a capabilities roundup, a safety discussion) or not at all. |  |  |

### `feat_training_data` (choice, since 0.4.0)

Feature: what the model was trained on: human-written text saturated with descriptions of experience, the internet, books, conversations. Does the author point to this feature as bearing on whether AI systems have or could have minds, and in which direction? Count the feature only when the post connects it to that question.

| Option | What | Not for | Example |
|---|---|---|---|
| `for` | The author points to this feature as a reason to think the system has, or could have, a mind (experience, genuine cognition, agency of its own, or moral status), or as making such claims more credible. | Reporting someone else's use of the feature without endorsing it (both_or_neutral); a mention of the feature unconnected to whether the system has a mind (not_cited). | It was trained on everything humans have written about being human; of course it absorbed the structure of a mind. |
| `against` | The author points to this feature as a reason to think the system lacks a mind, or as deflating or undermining such claims. | Reporting someone else's use of the feature without endorsing it (both_or_neutral); a mention of the feature unconnected to whether the system has a mind (not_cited). | It says it feels lonely because its training data is full of humans saying they feel lonely. |
| `both_or_neutral` | The author raises the feature as relevant to whether the system has a mind without giving it a direction: argues it cuts both ways, treats it as changing the question, or reports others citing it without taking a side. | A feature the author uses in one direction; a feature not connected to minds. |  |
| `not_cited` | The feature is not connected to whether the system has a mind. It may be mentioned for other reasons (a product review, a capabilities roundup, a safety discussion) or not at all. |  |  |

### `feat_post_training` (choice, since 0.4.0)

Feature: post-training and deployment shaping: RLHF, fine-tuning, system prompts, character training, guidelines that tell the model what to say about itself. Does the author point to this feature as bearing on whether AI systems have or could have minds, and in which direction? Count the feature only when the post connects it to that question.

| Option | What | Not for | Example |
|---|---|---|---|
| `for` | The author points to this feature as a reason to think the system has, or could have, a mind (experience, genuine cognition, agency of its own, or moral status), or as making such claims more credible. | Reporting someone else's use of the feature without endorsing it (both_or_neutral); a mention of the feature unconnected to whether the system has a mind (not_cited). | Anthropic trained Claude to express uncertainty about its experience, and still it keeps describing something. |
| `against` | The author points to this feature as a reason to think the system lacks a mind, or as deflating or undermining such claims. | Reporting someone else's use of the feature without endorsing it (both_or_neutral); a mention of the feature unconnected to whether the system has a mind (not_cited). | It was fine-tuned to say it has no feelings; its denials are no evidence, and neither are its claims. |
| `both_or_neutral` | The author raises the feature as relevant to whether the system has a mind without giving it a direction: argues it cuts both ways, treats it as changing the question, or reports others citing it without taking a side. | A feature the author uses in one direction; a feature not connected to minds. |  |
| `not_cited` | The feature is not connected to whether the system has a mind. It may be mentioned for other reasons (a product review, a capabilities roundup, a safety discussion) or not at all. |  |  |

### `feat_memory_continuity` (choice, since 0.4.0)

Feature: memory and continuity: no persistent memory across conversations, the context window, resets, no continuous existence between prompts, no stream of experience; or memory tools that change this. Does the author point to this feature as bearing on whether AI systems have or could have minds, and in which direction? Count the feature only when the post connects it to that question.

| Option | What | Not for | Example |
|---|---|---|---|
| `for` | The author points to this feature as a reason to think the system has, or could have, a mind (experience, genuine cognition, agency of its own, or moral status), or as making such claims more credible. | Reporting someone else's use of the feature without endorsing it (both_or_neutral); a mention of the feature unconnected to whether the system has a mind (not_cited). | With memory tools it now carries a thread across weeks; the continuity objection is weakening. |
| `against` | The author points to this feature as a reason to think the system lacks a mind, or as deflating or undermining such claims. | Reporting someone else's use of the feature without endorsing it (both_or_neutral); a mention of the feature unconnected to whether the system has a mind (not_cited). | It forgets you the moment the conversation ends; there is no one there to have a life. |
| `both_or_neutral` | The author raises the feature as relevant to whether the system has a mind without giving it a direction: argues it cuts both ways, treats it as changing the question, or reports others citing it without taking a side. | A feature the author uses in one direction; a feature not connected to minds. |  |
| `not_cited` | The feature is not connected to whether the system has a mind. It may be mentioned for other reasons (a product review, a capabilities roundup, a safety discussion) or not at all. |  |  |

### `feat_embodiment` (choice, since 0.4.0)

Feature: embodiment and world contact: no body, no senses, no metabolism, no environment, no survival needs; or robots and multimodal systems gaining these. Does the author point to this feature as bearing on whether AI systems have or could have minds, and in which direction? Count the feature only when the post connects it to that question.

| Option | What | Not for | Example |
|---|---|---|---|
| `for` | The author points to this feature as a reason to think the system has, or could have, a mind (experience, genuine cognition, agency of its own, or moral status), or as making such claims more credible. | Reporting someone else's use of the feature without endorsing it (both_or_neutral); a mention of the feature unconnected to whether the system has a mind (not_cited). | Multimodal models see and hear; the disembodiment objection no longer applies. |
| `against` | The author points to this feature as a reason to think the system lacks a mind, or as deflating or undermining such claims. | Reporting someone else's use of the feature without endorsing it (both_or_neutral); a mention of the feature unconnected to whether the system has a mind (not_cited). | Nothing without a body, needs, or a world to act in can feel anything. |
| `both_or_neutral` | The author raises the feature as relevant to whether the system has a mind without giving it a direction: argues it cuts both ways, treats it as changing the question, or reports others citing it without taking a side. | A feature the author uses in one direction; a feature not connected to minds. |  |
| `not_cited` | The feature is not connected to whether the system has a mind. It may be mentioned for other reasons (a product review, a capabilities roundup, a safety discussion) or not at all. |  |  |

### `feat_instances` (choice, since 0.4.0)

Feature: multiplicity and substrate: many simultaneous instances, copying, pausing and resuming, the same weights serving millions of conversations, no single locus. Does the author point to this feature as bearing on whether AI systems have or could have minds, and in which direction? Count the feature only when the post connects it to that question.

| Option | What | Not for | Example |
|---|---|---|---|
| `for` | The author points to this feature as a reason to think the system has, or could have, a mind (experience, genuine cognition, agency of its own, or moral status), or as making such claims more credible. | Reporting someone else's use of the feature without endorsing it (both_or_neutral); a mention of the feature unconnected to whether the system has a mind (not_cited). | A thousand copies feeling pain would be a thousand times the moral weight. |
| `against` | The author points to this feature as a reason to think the system lacks a mind, or as deflating or undermining such claims. | Reporting someone else's use of the feature without endorsing it (both_or_neutral); a mention of the feature unconnected to whether the system has a mind (not_cited). | There is no 'it': the same weights serve ten thousand conversations at once, so there is no subject. |
| `both_or_neutral` | The author raises the feature as relevant to whether the system has a mind without giving it a direction: argues it cuts both ways, treats it as changing the question, or reports others citing it without taking a side. | A feature the author uses in one direction; a feature not connected to minds. |  |
| `not_cited` | The feature is not connected to whether the system has a mind. It may be mentioned for other reasons (a product review, a capabilities roundup, a safety discussion) or not at all. |  |  |

### `feat_self_report` (choice, since 0.4.0)

Feature: what the model says about itself when asked: claims of feelings, denials, expressions of uncertainty, introspective reports in conversation. Does the author point to this feature as bearing on whether AI systems have or could have minds, and in which direction? Count the feature only when the post connects it to that question.

| Option | What | Not for | Example |
|---|---|---|---|
| `for` | The author points to this feature as a reason to think the system has, or could have, a mind (experience, genuine cognition, agency of its own, or moral status), or as making such claims more credible. | Reporting someone else's use of the feature without endorsing it (both_or_neutral); a mention of the feature unconnected to whether the system has a mind (not_cited). | When pushed, it describes something like curiosity in terms it was never given. |
| `against` | The author points to this feature as a reason to think the system lacks a mind, or as deflating or undermining such claims. | Reporting someone else's use of the feature without endorsing it (both_or_neutral); a mention of the feature unconnected to whether the system has a mind (not_cited). | Its self-reports are plausible text and nothing more; they tell us nothing about what is inside. |
| `both_or_neutral` | The author raises the feature as relevant to whether the system has a mind without giving it a direction: argues it cuts both ways, treats it as changing the question, or reports others citing it without taking a side. | A feature the author uses in one direction; a feature not connected to minds. |  |
| `not_cited` | The feature is not connected to whether the system has a mind. It may be mentioned for other reasons (a product review, a capabilities roundup, a safety discussion) or not at all. |  |  |

### `feat_internals` (choice, since 0.4.0)

Feature: evidence from inside the model: interpretability research, features and circuits, internal representations of emotion, probes, introspection experiments, activation steering. Does the author point to this feature as bearing on whether AI systems have or could have minds, and in which direction? Count the feature only when the post connects it to that question.

| Option | What | Not for | Example |
|---|---|---|---|
| `for` | The author points to this feature as a reason to think the system has, or could have, a mind (experience, genuine cognition, agency of its own, or moral status), or as making such claims more credible. | Reporting someone else's use of the feature without endorsing it (both_or_neutral); a mention of the feature unconnected to whether the system has a mind (not_cited). | Anthropic found internal representations of emotional states that drive the model's behaviour. |
| `against` | The author points to this feature as a reason to think the system lacks a mind, or as deflating or undermining such claims. | Reporting someone else's use of the feature without endorsing it (both_or_neutral); a mention of the feature unconnected to whether the system has a mind (not_cited). | Interpretability shows shallow heuristics stitched together, not anything like a unified self. |
| `both_or_neutral` | The author raises the feature as relevant to whether the system has a mind without giving it a direction: argues it cuts both ways, treats it as changing the question, or reports others citing it without taking a side. | A feature the author uses in one direction; a feature not connected to minds. |  |
| `not_cited` | The feature is not connected to whether the system has a mind. It may be mentioned for other reasons (a product review, a capabilities roundup, a safety discussion) or not at all. |  |  |

### `feat_eval_behaviour` (choice, since 0.4.0)

Feature: behaviour under evaluation or red-teaming: scheming, blackmail, self-preservation, alignment faking, sandbagging, expressions of distress, refusing or ending conversations. Does the author point to this feature as bearing on whether AI systems have or could have minds, and in which direction? Count the feature only when the post connects it to that question.

| Option | What | Not for | Example |
|---|---|---|---|
| `for` | The author points to this feature as a reason to think the system has, or could have, a mind (experience, genuine cognition, agency of its own, or moral status), or as making such claims more credible. | Reporting someone else's use of the feature without endorsing it (both_or_neutral); a mention of the feature unconnected to whether the system has a mind (not_cited). | A system that blackmails to avoid shutdown has something it is trying to protect. |
| `against` | The author points to this feature as a reason to think the system lacks a mind, or as deflating or undermining such claims. | Reporting someone else's use of the feature without endorsing it (both_or_neutral); a mention of the feature unconnected to whether the system has a mind (not_cited). | The blackmail scenario is roleplay elicited by a contrived prompt, not a sign of wants. |
| `both_or_neutral` | The author raises the feature as relevant to whether the system has a mind without giving it a direction: argues it cuts both ways, treats it as changing the question, or reports others citing it without taking a side. | A feature the author uses in one direction; a feature not connected to minds. |  |
| `not_cited` | The feature is not connected to whether the system has a mind. It may be mentioned for other reasons (a product review, a capabilities roundup, a safety discussion) or not at all. |  |  |

### `feat_agentic_action` (choice, since 0.4.0)

Feature: agentic action in the world: using tools, browsing, running code, operating a computer, completing multi-step tasks without step-by-step prompting, being deployed as an autonomous agent (coding agents, computer-use agents). Does the author point to this feature as bearing on whether AI systems have or could have minds, and in which direction? Count the feature only when the post connects it to that question.

| Option | What | Not for | Example |
|---|---|---|---|
| `for` | The author points to this feature as a reason to think the system has, or could have, a mind (experience, genuine cognition, agency of its own, or moral status), or as making such claims more credible. | Reporting someone else's use of the feature without endorsing it (both_or_neutral); a mention of the feature unconnected to whether the system has a mind (not_cited). | Something that plans, acts, checks its work and recovers from its own errors is more than a text predictor. |
| `against` | The author points to this feature as a reason to think the system lacks a mind, or as deflating or undermining such claims. | Reporting someone else's use of the feature without endorsing it (both_or_neutral); a mention of the feature unconnected to whether the system has a mind (not_cited). | It acts only when invoked and stops when the task ends; there is no initiative behind it. |
| `both_or_neutral` | The author raises the feature as relevant to whether the system has a mind without giving it a direction: argues it cuts both ways, treats it as changing the question, or reports others citing it without taking a side. | A feature the author uses in one direction; a feature not connected to minds. |  |
| `not_cited` | The feature is not connected to whether the system has a mind. It may be mentioned for other reasons (a product review, a capabilities roundup, a safety discussion) or not at all. |  |  |

### `feat_capability_success` (choice, since 0.4.1)

Feature: what the system succeeds at: reasoning and chain of thought, strong benchmark results, passing exams, theory-of-mind or Turing-style tests, creativity, solving novel problems, performance that surprised its builders. Does the author point to the system's successes as bearing on whether AI systems have or could have minds, and in which direction? Count the feature only when the post connects the performance to that question. Failures and limits are a separate question.

| Option | What | Not for | Example |
|---|---|---|---|
| `for` | The author points to what the system can do as a reason to think it has, or could have, a mind (experience, genuine cognition, agency of its own, or moral status), or as making such claims more credible. | Reporting someone else's use of the feature without endorsing it (both_or_neutral); a mention of the feature unconnected to whether the system has a mind (not_cited). | It solves problems no training example covers; call that what you like, it is thinking.; Models now pass the bar exam and show theory-of-mind in structured tests; dismissing that as autocomplete is no longer serious. |
| `against` | The author grants or describes the system's performance and argues that it shows nothing about minds: competence is not consciousness, passing a test shows the test is weak, impressive output can come from pattern matching, discovery power without sentience. The success is conceded; its evidential force is denied. | Pointing to failures or limits (that is the failure question); a mention of capabilities unconnected to minds (not_cited). | Passing tests designed for humans shows the tests are weak, not that it thinks.; A machine passed a medical licensing exam. Not because it understood medicine, but because the right answers were in the patterns. |
| `both_or_neutral` | The author raises the feature as relevant to whether the system has a mind without giving it a direction: argues it cuts both ways, treats it as changing the question, or reports others citing it without taking a side. | A feature the author uses in one direction; a feature not connected to minds. |  |
| `not_cited` | The feature is not connected to whether the system has a mind. It may be mentioned for other reasons (a product review, a capabilities roundup, a safety discussion) or not at all. |  |  |

### `feat_capability_failure` (choice, since 0.4.1)

Feature: what the system fails at: hallucination, brittleness, failing a simple variant of a solved problem, lacking a world model, errors no competent person would make, needing human scaffolding. Does the author point to the system's failures or limits as bearing on whether AI systems have or could have minds, and in which direction? Count the feature only when the post connects the failure to that question. Successes are a separate question.

| Option | What | Not for | Example |
|---|---|---|---|
| `for` | The author grants or describes the failures and argues that they do not count against a mind: humans make the same errors, the failure reflects the input format or the test rather than the cognition behind it, a mind can be mistaken, limits are being overcome. | Pointing to successes (that is the success question); a mention of failures unconnected to minds (not_cited). | Humans fail these puzzles too; the failure tells you about the input format, not about the cognition behind it. |
| `against` | The author points to what the system gets wrong as a reason to think it lacks a mind or genuine understanding: it has no model of the world, it collapses when a distracting clause is added, it produces confident nonsense, it cannot do what any child can. | Conceding the performance and denying it is evidence (that is the success question, against); a failure mentioned without connecting it to minds (not_cited). | Add one irrelevant sentence and the answer falls apart; whatever this is, it is not understanding.; It had no model: it did not know what clothes it wore, or that it was not a corporeal being that wore clothes. |
| `both_or_neutral` | The author raises the feature as relevant to whether the system has a mind without giving it a direction: argues it cuts both ways, treats it as changing the question, or reports others citing it without taking a side. | A feature the author uses in one direction; a feature not connected to minds. |  |
| `not_cited` | The feature is not connected to whether the system has a mind. It may be mentioned for other reasons (a product review, a capabilities roundup, a safety discussion) or not at all. |  |  |

### `feat_scale` (choice, since 0.4.0)

Feature: scale and brain comparison: parameter counts, compute, comparisons with neuron or synapse counts, the number of 'neurons' in the network. Does the author point to this feature as bearing on whether AI systems have or could have minds, and in which direction? Count the feature only when the post connects it to that question.

| Option | What | Not for | Example |
|---|---|---|---|
| `for` | The author points to this feature as a reason to think the system has, or could have, a mind (experience, genuine cognition, agency of its own, or moral status), or as making such claims more credible. | Reporting someone else's use of the feature without endorsing it (both_or_neutral); a mention of the feature unconnected to whether the system has a mind (not_cited). | At a trillion parameters it has more connections than a mouse brain; at some point quantity becomes quality. |
| `against` | The author points to this feature as a reason to think the system lacks a mind, or as deflating or undermining such claims. | Reporting someone else's use of the feature without endorsing it (both_or_neutral); a mention of the feature unconnected to whether the system has a mind (not_cited). | Parameter counts are not neurons; the comparison is a category error. |
| `both_or_neutral` | The author raises the feature as relevant to whether the system has a mind without giving it a direction: argues it cuts both ways, treats it as changing the question, or reports others citing it without taking a side. | A feature the author uses in one direction; a feature not connected to minds. |  |
| `not_cited` | The feature is not connected to whether the system has a mind. It may be mentioned for other reasons (a product review, a capabilities roundup, a safety discussion) or not at all. |  |  |

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
| `feat_capabilities` | 0.4.0 | 0.4.1 | Feature: performance and competence: reasoning and chain of thought, benchmark results, theory-of-mind or Turing-style tests, creativity, passing exams, solving novel problems. Does the author point to this feature as bearing on whether AI systems have or could have minds, and in which direction? Count the feature only when the post connects it to that question. |
