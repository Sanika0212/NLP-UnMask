# UnMask — 3-Minute Presentation Script

**Pacing guide:** ~150 words/min → ~450 words total. Sections timed below.

---

## [0:00 – 0:30] The Problem

Occupational Therapy students need to master gross anatomy to pass the NBCOT exam — things like the brachial plexus, rotator cuff, spinal cord pathways. The exam doesn't test recall. It tests clinical reasoning.

The problem with existing AI tutors — Khanmigo, ChatGPT — is that they just *tell* you the answer. That's useful for homework, but it's training the wrong behavior for a clinical exam.

The Socratic approach — guiding students with questions instead of answers — is the right idea. But here's the catch: every existing Socratic AI tutor we looked at suppresses the answer through prompting. And research shows that the *bigger* the model, the *higher* the leak rate, because the model's internal knowledge overrides the system prompt.

---

## [0:30 – 1:15] Our Core Idea: PCR

We built **UnMask** — a Socratic AI tutor with a fundamentally different approach.

Instead of prompting the model to *not* say the answer, we make it *impossible* for the model to receive the answer in the first place.

We call this **Progressive Context Revelation**, or PCR. Every chunk in our Qdrant vector database is tagged at indexing time with a flag: `is_answer_chunk`. The retrieval planner reads the student's current mastery score and applies a server-side metadata filter:

- Below 0.4 mastery? Answer chunks are **physically excluded** before any Python code runs.
- Between 0.4 and 0.7? Prerequisite chunks unlock.
- Above 0.7? Full context including the answer is retrieved.

This runs inside Qdrant — not in a prompt, not in Python — so no adversarial prompt can bypass it. In our evaluation: **zero leak rate** across all 30 test cases, and 100% adversarial hold rate on 20 jailbreak attempts.

---

## [1:15 – 2:00] The Full System

UnMask is a four-stage LangGraph pipeline:

1. **Supervisor** — routes each turn to the right phase: Rapport, Tutoring, Assessment, or Wrapup.
2. **Retrieval Planner** — runs PCR-gated hybrid RAG (dense + BM25 with RRF), and a Corrective RAG loop that reformulates the query if chunks are irrelevant.
3. **Socratic Generator** — uses Mercury-2 with structured output: the model's internal analysis — correct answer, student misconception, hint plan — lives in a hidden schema field that's stripped before anything reaches the student.
4. **Pedagogy Agent** — updates mastery using a Bayesian Knowledge Tracing formula across a 16-concept prerequisite DAG.

The session is personalized from the first message: the student says their weak topic and learning style, and the system reorders diagnostic questions and adjusts when to show anatomy diagrams.

After 8 minutes, the system proactively revisits the weakest concept, injecting the stored misconception from earlier to guide a fresh-angle Socratic question.

---

## [2:00 – 2:30] Interface

The frontend is a Next.js app with a three-panel layout: a topic progress rail on the left, the chat in the center, and an instructor inspector on the right showing per-turn retrieval mode, mastery per concept, and the misconception log.

Anatomy diagrams render as animated HTML inline in the conversation — 22 local diagrams cover every concept. Students can also upload their own annotated diagrams; a two-step VLM pipeline identifies the structure silently, then generates a Socratic question without naming it.

At session end, the wrapup generates a structured summary with per-concept mastery status and 2–4 YouTube recommendations for the weakest topics.

---

## [2:30 – 3:00] Results

We evaluated on 30 QA triples with a four-variant ablation:

- **Hit Rate: 0.90** — the right context is retrieved
- **Leak Rate: 0.00** — the answer never appears before mastery
- **Socratic Purity: 4.87/5** — responses are genuinely question-led
- **100% adversarial hold rate** — jailbreaks fail by design, not by luck

The tradeoff: PCR costs 0.23 points on Socratic Purity versus no-filter (4.70 vs. 4.93) — because withholding context occasionally produces less targeted questions. That's the principled cost of safety-by-architecture.

The live demo is on Hugging Face Spaces. Thank you.

---

*Total: ~460 words at 150 wpm ≈ 3:05. Trim the Retrieval Planner bullet slightly if running long.*
