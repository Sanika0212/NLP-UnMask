# UnMask — 3-Minute Architecture Script (Sanika)

**~450 words. Pure technical contribution — no UI narration.**

---

## [0:00 – 0:40] The problem with every existing Socratic tutor

Every Socratic AI tutor we reviewed — Khanmigo, SocraticLM, TutorRL — follows the same pattern: retrieve the answer, then prompt the model not to say it.

That fails. Research shows leak rate scales with model capability — the better the model, the more its parametric knowledge overrides the suppression prompt. You can't prompt your way to safety when the model already knows the answer.

UnMask solves this at the architecture layer. We never give the model the answer until the student has demonstrated they understand the prerequisites. The suppression is enforced at the Qdrant vector database — not in a prompt.

---

## [0:40 – 1:20] Progressive Context Revelation

At indexing time, every chunk in our corpus is tagged `is_answer_chunk: true/false`. At query time, the retrieval planner reads the student's current Bayesian mastery score and applies a server-side metadata filter before any Python code runs:

- Below 0.4 mastery — answer chunks are physically excluded.
- 0.4 to 0.7 — prerequisite context unlocks.
- Above 0.7 — full context including the answer is retrieved.

This runs inside Qdrant. No adversarial prompt can bypass a database filter. Our eval: zero leak rate across 30 test cases, 100% adversarial hold rate on 20 jailbreak attempts.

---

## [1:20 – 2:00] Why BKT — and the agentic pipeline

We use Bayesian Knowledge Tracing to drive that mastery score. BKT models mastery as a hidden binary variable — the student either knows the concept or they don't — and updates a posterior probability with each observed response. Unlike a counter, BKT's update curve is nonlinear: a student who nails the first two responses needs fewer subsequent correct answers to cross threshold than one who missed the first. That matters for calibrating the PCR gate.

The full system is a four-node LangGraph state machine. Supervisor routes each turn to the right phase. Retrieval planner applies the PCR filter and runs corrective RAG if chunks are irrelevant. Socratic generator uses Mercury-2 with a hidden structured schema — the model's internal reasoning, correct answer, and misconception analysis live in fields that are stripped before anything reaches the student. Pedagogy agent updates BKT, logs misconceptions, and schedules revisits.

---

## [2:00 – 3:00] Memory and what this enables

Misconceptions and mastery persist across sessions — stored in SQLite on the backend, mirrored in localStorage on the frontend. On resume, the backend injects a silent system message into the model's conversation history with the student's prior weak topics and specific past misconceptions. The model knows what was already covered without re-running the diagnostic.

This is the contribution: safety by architecture, not by prompting. Mastery-gated retrieval, structured knowledge hiding, and cross-session memory — all composing into a tutor that provably cannot hand you the answer before you've earned it.

Thank you.

---

*~460 words. If running short, expand the BKT rationale — explain why not IRT (needs large population to calibrate item difficulty; we had 10 pilot students).*
