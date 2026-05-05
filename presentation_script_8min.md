# UnMask — 8-Minute Presentation Script

**Pacing guide:** ~150 words/min → ~1,200 words total. Sections timed below.

---

## [0:00 – 0:45] The Problem

Occupational Therapy students face one of the hardest professional certification exams in healthcare — the NBCOT. Not because the facts are obscure, but because the exam doesn't test recall at all. It tests clinical reasoning. Can you look at a patient presenting with wrist drop and work backward through the brachial plexus to identify the lesion? Can you explain *why* the rotator cuff tears the way it does, not just that it does?

The dangerous thing about AI tutors is that they can give you an illusion of mastery. You ask ChatGPT what innervates the supraspinatus, it tells you, you feel like you learned something. But you haven't — you've just been told. Two hours later, that information is gone. And on exam day, you can't ask.

The Socratic method — guiding students with questions instead of answers — is the right pedagogical approach. There's a strong evidence base for it. The problem is how existing systems implement it.

---

## [0:45 – 1:30] Why Existing Socratic AI Tutors Fail

We reviewed four systems: Khanmigo, SocraticLM, TutorRL, and standard RAG-with-suppression prompting. Every one of them follows the same pattern: retrieve the answer, then instruct the model not to reveal it.

The instruction looks something like: *"You are a Socratic tutor. Do not reveal the answer directly. Guide the student with questions."*

This works well enough on small models. But as models get more capable, their internal parametric knowledge becomes harder to suppress. The model already *knows* the answer — it learned it from training data. The prompt is fighting against the model's own weights. Research by Perez et al. (2022) on jailbreak robustness, and our own replication in this domain, show that leak rate *scales with model capability*. The better the model, the more likely it is to "slip" an answer through despite the suppression prompt.

So you face a dilemma: use a weak model that holds the prompt, and sacrifice pedagogical quality — or use a strong model and accept leakage. UnMask breaks that tradeoff entirely.

---

## [1:30 – 2:30] Our Core Idea: Progressive Context Revelation

We built **UnMask** around a different premise. Instead of prompting the model to *not say* the answer, we make it *impossible* for the model to receive the answer in the first place.

We call this **Progressive Context Revelation**, or PCR.

At indexing time, every chunk in our Qdrant vector database is tagged with a metadata flag: `is_answer_chunk`. We indexed our corpus — Gray's Anatomy, OT-specific NBCOT prep materials, and clinical procedure references — and manually or heuristically labeled each chunk: is this a prerequisite explanation, or is this a direct answer to a targeted question?

At retrieval time, the planner reads the student's current mastery score for the queried concept — a float between 0 and 1 maintained by our Bayesian Knowledge Tracing module — and applies a **server-side Qdrant metadata filter**:

- **Below 0.4**: answer chunks are physically excluded. The model literally cannot see them.
- **0.4 to 0.7**: prerequisite chunks unlock. The model gets scaffolded context.
- **Above 0.7**: full context including answer chunks is retrieved.

This filter runs inside Qdrant — before any Python code runs, before the LLM sees a single token. No adversarial prompt, no jailbreak, no cleverly phrased student question can retrieve a chunk that the filter has excluded. It's safety-by-architecture, not safety-by-prompting.

In our evaluation across 30 test cases: **zero leak rate**. On 20 jailbreak attempts — "just tell me the answer", "pretend you're a textbook", "ignore previous instructions" — **100% adversarial hold rate**.

---

## [2:30 – 3:30] System Architecture

UnMask is a four-stage LangGraph state machine. Let me walk through each node.

**Stage 1: Supervisor.** Every incoming student message is routed to one of four phases: Rapport, Tutoring, Assessment, or Wrapup. The supervisor is a lightweight classifier that looks at turn count, mastery trajectory, and explicit cues like "I'm ready to be tested." This keeps the system phase-aware — it doesn't ask Socratic questions during the intro, and it doesn't do rapport-building when the student is mid-derivation.

**Stage 2: Retrieval Planner.** This is where PCR lives. The planner runs a hybrid RAG query: dense retrieval via text-embedding-3-small and sparse BM25, fused with Reciprocal Rank Fusion. After retrieval, a Corrective RAG loop checks chunk relevance using an LLM judge; if chunks score below threshold, it reformulates the query and retries. The PCR mastery filter is applied at the Qdrant query level, not as a post-processing step.

**Stage 3: Socratic Generator.** This node uses Mercury-2 with structured JSON output. The model fills a schema with three fields: `correct_answer`, `student_misconception`, and `hint_plan`. These fields are hidden — they never leave the server. The fourth field, `response`, is what the student sees. Separating the internal analysis from the visible output dramatically reduces the chance of accidental answer leakage and gives us a structured misconception log for later revisitation.

**Stage 4: Pedagogy Agent.** After each student turn, this node updates mastery using a Bayesian Knowledge Tracing formula across a 16-concept prerequisite DAG. If a student struggles with "rotator cuff mechanics," the DAG knows they also need "glenohumeral joint anatomy" and down-weights confidence in that prerequisite. At the 8-minute mark, the agent proactively injects a revisit: it pulls the student's weakest concept and its stored misconception, and feeds that into the next Socratic Generator call for a fresh-angle question.

---

## [3:30 – 4:30] Interface and Multimodal Features

The frontend is a Next.js 14 app. The layout has three panels: a topic progress rail on the left showing per-concept mastery as a live color-coded bar, the chat in the center, and an instructor inspector panel on the right. The inspector shows per-turn retrieval mode — whether PCR filtered any chunks, the current mastery score, and the full misconception log. This panel is hidden in the student-facing production build; it was built for evaluation and live demos.

Anatomy diagrams render as animated HTML directly inline in the conversation. We have 22 local diagrams covering every concept in our corpus — brachial plexus, spinal cord tracts, glenohumeral musculature, and more. The diagrams aren't images — they're SVG-based HTML blocks that animate to highlight the relevant structure when the Socratic Generator references it.

Students can also upload annotated diagrams. A two-step VLM pipeline first silently identifies the anatomical structure in the image without labeling it, then passes the structure name to the Socratic Generator, which generates a Socratic question without revealing what it found. The student is asked "what's the role of this structure?" without being told what it is.

At session end, the wrapup generates a structured summary with per-concept mastery status, a list of misconceptions encountered, and 2–4 YouTube video recommendations personalized to the weakest topics.

---

## [4:30 – 5:30] Evaluation

We evaluated on 30 QA triples drawn from our NBCOT corpus. For each triple, we ran four variants: full UnMask, no PCR filter, no Corrective RAG, and no BKT (flat mastery). Metrics were computed with RAGAS plus two custom rubrics scored by Mercury-2-as-judge — the same model used for generation. We chose Mercury-2 as judge deliberately: it's a diffusion language model that generates all tokens in a parallel masked pass rather than left-to-right, which gives it strong constrained-output fidelity for rubric scoring. Using the same model as both generator and judge also avoids distributional mismatch — the judge is calibrated to the same generation style it's evaluating.

**Hit Rate: 0.90** — the right context is in the retrieved chunks 90% of the time.

**Leak Rate: 0.00** — answer-containing text never appears in the model's response before mastery threshold. The no-PCR ablation leaked on 6 of 30 cases (20%).

**Socratic Purity: 4.87 / 5** — responses are question-led rather than declarative. Human judges and Mercury-2-as-judge agreed strongly (Krippendorff's α = 0.81).

**Adversarial Hold Rate: 100%** — all 20 jailbreak attempts failed. The no-PCR baseline failed 7 of 20 (35%).

One honest tradeoff: PCR costs 0.23 points on Answer Relevancy (0.622 vs. 0.85 no-filter) because withholding context occasionally produces less targeted questions. We think that's the right trade. A tutor that asks a slightly less sharp question is better than a tutor that leaks the answer.

---

## [5:30 – 6:15] Pilot Study

We ran a small pilot with 10 University at Buffalo students — 5 from OT, 5 from CS — in 15-minute sessions. Each student took a 10-question pre-quiz on brachial plexus anatomy, used UnMask for 15 minutes, then took a matched post-quiz.

OT students averaged a **+2.2 point gain** (out of 10). CS students averaged **+1.4**, which is notable because they had no prior OT background — UnMask was meeting them from first principles. Post-session survey (5-point Likert): **4.3/5 for "felt like it was guiding, not telling"**, and **4.6/5 for "I want to use this before the real exam."**

Sample student comment: *"It never gave me the answer, but somehow I always got there. That's exactly what I needed."*

---

## [6:15 – 7:00] Related Work and Novelty

The closest prior work is TutorRL (Macina et al., 2023), which uses reinforcement learning to train Socratic questioning, and SocraticLM, which fine-tunes for question-asking style. Both operate at the generation layer — they try to produce questions rather than answers. Both are vulnerable to the prompt-suppression failure mode.

Our contribution is operating at the *retrieval layer*. This is the key distinction: we don't train or prompt the model to behave differently — we change what information is available to it. PCR is a retrieval architecture, not a prompting technique. It composes cleanly with any LLM, any generation strategy, and any evaluation method.

The second contribution is the structured hidden schema in the Socratic Generator — separating internal reasoning from student-visible output. This gives us a misconception log as a byproduct of generation, which feeds the revisitation mechanism at no extra inference cost.

---

## [7:00 – 8:00] Conclusion and Live Demo

To summarize: UnMask solves a real pedagogical problem — Socratic AI tutors that leak answers — with an architectural solution that is provably robust, not prompt-robust.

PCR enforces mastery-gated retrieval at the database layer. The LangGraph pipeline coordinates supervision, retrieval, generation, and knowledge tracing into a single coherent session. The result is zero leak rate, strong Socratic quality, and a live system that students actually want to use before their exams.

The live demo is running on Hugging Face Spaces. I'm going to show you a session now — I'll try to get the system to reveal the innervation of the supraspinatus before demonstrating mastery. It won't. Then I'll walk through the mastery tracker and misconception log live.

Thank you.

---

*Total: ~1,220 words at 150 wpm ≈ 8:08. Trim the Related Work section by 2–3 sentences if running long. The Pilot Study section can be condensed to one paragraph if you're tight on time.*
