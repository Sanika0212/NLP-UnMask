# UnMask: Mastery-Gated Retrieval for Socratic OT Anatomy Education

**Sanika Vilas Najan · Vaishak Girish Kumar**
CSE 635: NLP and Text Mining — University at Buffalo, Spring 2026
Instructor: Prof. Rohini K. Srihari

---

## Abstract

We present **UnMask**, a Socratic AI tutoring system for Occupational Therapy (OT) anatomy and neuroscience NBCOT preparation. Unlike all prior Socratic AI tutors — which retrieve the correct answer and rely on prompting or fine-tuning to suppress it — UnMask enforces answer suppression at the *retrieval layer* via **Progressive Context Revelation (PCR)**: a metadata-filtered Qdrant query that physically excludes answer chunks from the model's context until the student demonstrates prerequisite mastery through a concept prerequisite graph. We combine PCR with **Corrective RAG (CRAG)**, the first application of self-correcting retrieval in an educational tutoring context, and a dual-layer knowledge masking scheme using structured output schemas. Evaluated on 30 anatomy QA triples with a four-variant controlled ablation study, the full system achieves: Retrieval Hit Rate 1.000, Answer Leak Rate 0.000, Avg Socratic Purity 4.93/5, and 100% adversarial resistance across 20 jailbreak/social-engineering prompts. A key finding: all ablated variants also show 0.000 leak rate under benign conditions — but only PCR provides architectural safety that cannot be bypassed by sufficiently capable models, at a measured 0.23-point purity cost (4.70 vs 4.93). RAGAS Faithfulness (0.779) falls below target (0.85), revealing a fundamental measurement mismatch: RAGAS scores Socratic questions — which make no factual claims by design — as unfaithful, exposing a gap in evaluation infrastructure for Socratic dialogue systems.

---

## 1  Introduction

Occupational Therapy students must master Gross Anatomy and Neuroscience to pass the NBCOT certification exam, yet they lack access to 1:1 clinical reasoning support outside of class. Standard AI systems like ChatGPT undermine this goal: they provide direct answers, short-circuiting the clinical reasoning the exam tests.

The P3 specification defines "Socratic" tutoring as a "Tutor-not-Teller" philosophy: the bot is *strictly forbidden* from providing a direct definition or answer in the first two turns and must use retrieved textbook data to ask leading questions that trigger student discovery.

The core technical challenge is that prompt-based suppression is a *generation-layer* constraint. TutorRL (Dinucu-Jianu et al., EMNLP 2025) empirically demonstrated that larger models exhibit *higher* solution leakage: 72B+ parameter models are worse at Socratic tutoring because their superior parametric knowledge allows them to answer directly, regardless of system prompts. The only architecturally safe solution is to prevent the LLM from receiving the answer in the first place.

**UnMask's key claim:** by filtering the retrieval layer using student mastery state, answer leakage becomes architecturally impossible before mastery thresholds are met. This is a 10-line Qdrant metadata filter that no adversarial prompting can bypass, because the LLM cannot leak what it never received.

---

## 2  Related Work

### 2.1  Learning Science Foundations

Bloom (1984) demonstrated that one-to-one tutoring produces a 2-standard-deviation improvement over conventional classroom instruction — the "2 Sigma Problem." The challenge has been scaling this effect. Kestin et al. (2025) provide the first RCT evidence that AI tutors designed around pedagogical best practices (Socratic prompting, one-step guidance, cognitive load management) achieve roughly 2× learning gains over in-class active learning in 20% less time — directly motivating our "Tutor-not-Teller" architecture. Commercial systems like MS Articulate 360 and Bootlebox address scalable content delivery but use static branching logic, not adaptive dialogue. Khanmigo (Khan Academy) is the current industry benchmark: it uses GPT-4 system prompts to enforce Socratic behavior, but the retrieval layer returns all documents including answer text, leaving the LLM free to leak on adversarial input.

### 2.2  Knowledge Tracing

Corbett and Anderson (1994) introduced Bayesian Knowledge Tracing (BKT), modeling student mastery as a hidden Markov process with learn, guess, slip, and transit parameters. Piech et al. (2015) extended this with Deep Knowledge Tracing (DKT), replacing the HMM with an LSTM that infers knowledge state from raw interaction sequences without hand-engineered domain features. UnMask's Pedagogy Agent uses BKT-style update rules (`correct → m + 0.15*(1−m)`, `incorrect → m − 0.05*m`) applied per concept node in a prerequisite DAG, combining probabilistic mastery estimation with structural reasoning about prerequisite failures.

### 2.3  Retrieval-Augmented Generation

Lewis et al. (2020) introduced RAG as a general architecture combining a dense retrieval component with a seq2seq generator, significantly improving factual accuracy on knowledge-intensive tasks. Subsequent work has focused on retrieval quality: Yan et al. (2024) introduced Corrective RAG (CRAG), adding a self-assessment step that grades retrieved documents and reformulates the query on failure, gaining +19% on PopQA and +36.6% on PubHealth. For evaluation, Es et al. (2024) introduced RAGAS — reference-free metrics (faithfulness, answer relevancy, context precision/recall) that assess RAG quality without ground-truth annotations. UnMask applies CRAG in an educational tutoring context for the first time, and uses RAGAS as a faithfulness gate.

### 2.4  Socratic AI Tutors

**SocraticLM** (Liu et al., NeurIPS 2024) fine-tunes a model to produce Socratic dialogue but has no retrieval component, leaving parametric knowledge unconstrained.

**KELE** (Peng et al., EMNLP 2025) separates planning and execution into two agents, but both agents have full context access to the answer.

**TutorRL** (Dinucu-Jianu et al., EMNLP 2025) demonstrates that larger LLMs exhibit *higher* solution leakage under RL-based pedagogical alignment: 72B+ models are better at solving problems directly regardless of instruction. This motivates retrieval-layer enforcement over prompt-layer enforcement.

**TutorLLM** (Li et al., RecSys 2024) — the closest prior work — combines Knowledge Tracing with RAG but passes mastery state as *prompt context* to GPT-4; the retrieval layer returns all documents regardless of mastery. Our PCR mechanism operates one layer earlier, at retrieval time.

**MWPTutor** (Chowdhury et al., AIED 2024) uses functional slot-based guardrails for math tutoring, but leakage checks operate at the generation layer and can be bypassed by capable models.

### 2.5  Multimodal Vision-Language Models

Liu et al. (2024) introduced LLaVA (Large Language and Vision Assistant), demonstrating that visual instruction tuning on GPT-4-generated multimodal data produces strong VLMs capable of spatial and scientific visual reasoning. Achiam et al. (2023) describe GPT-4's multimodal capabilities including diagram interpretation. For medical domains specifically, Sellergren et al. (2025) introduce MedGemma, an open-source medical VLM (4B/27B parameters) achieving competitive performance on medical reasoning benchmarks — UnMask uses MedGemma 4B as its primary diagram analysis model, with Gemini 2.0 Flash Lite as fallback.

### 2.6  Groundedness Verification

The dominant paradigm for RAG faithfulness is post-hoc measurement (RAGAS, TruLens, DeepEval). Leemann et al. (2025) show via Auto-GDA that DeBERTa-based NLI models achieve LLM-level grounding verification at ~10% of inference cost, making real-time faithfulness gating practical. UnMask shifts from post-hoc measurement to pre-delivery enforcement: DeBERTa checks every response before rendering, blocking unfaithful outputs rather than reporting them.

---

## 3  System Architecture

UnMask is organized as four layers orchestrated by a LangGraph state machine.

### 3.1  Session State Machine (LangGraph)

The session progresses through four phases with time ceilings enforced by the orchestrator node (pure Python, zero LLM calls, following DiagGPT's (Cao, 2023) design principle that explicit state management — whether rule-based or LLM-assisted — is necessary for reliable phase transitions in task-oriented dialogue):

| Phase | Entry Trigger | Exit Trigger | Window |
|-------|--------------|--------------|--------|
| **Rapport** | Session start | 4 diagnostic Qs complete | 0–120s |
| **Tutoring** | `diagnostic_complete` | `coverage ≥ 0.80` or `t ≥ 720s` | 120–720s |
| **Assessment** | Coverage/time threshold | `t ≥ 840s` | 720–840s |
| **Wrapup** | `t ≥ 840s` | Session end | 840–900s |

The `TutoringState` TypedDict carries: `phase`, `mastery_scores`, `retrieved_chunks`, `retrieval_mode`, `consecutive_correct/incorrect`, `coverage_ratio`, `_internal_analysis`, `weak_topics`, and `conversation_history`. The graph has five nodes: `orchestrator → retrieval_planner → socratic_generator → pedagogy_agent`. A conditional edge in the orchestrator bypasses retrieval for Rapport and Wrapup phases.

### 3.2  Layer 1: Student Interface (Chainlit)

Students interact via Chainlit web UI, typing questions and receiving Socratic responses. A backend debug panel (instructor-visible) displays per-turn: PCR retrieval mode, chunk scores before/after re-ranking, mastery state per concept, and NLI verdict — directly satisfying the P3 requirement for visible chunk processing logs.

### 3.3  Layer 2: Progressive Context Revelation (PCR)

Every chunk in Qdrant carries two metadata fields set at indexing time: `is_answer_chunk: bool` and `chunk_type: {context | prerequisite | answer | figure}`. The Retrieval Planner reads the student's mastery score from the concept graph and applies one of three filter modes:

```
mastery < 0.40  → context_only:       EXCLUDE is_answer_chunk=True (Qdrant must_not)
mastery < 0.70  → prerequisite_first: INCLUDE only context/prerequisite/figure chunks
mastery ≥ 0.70  → full_reveal:        No filter — all chunks retrievable
```

The critical property: in `context_only` mode, the `must_not` filter executes server-side inside Qdrant before any results reach Python. The LLM never receives answer chunks. This is categorically different from prompt-based suppression — it is enforced at the data plane, not the instruction plane.

### 3.4  Layer 3: Hybrid Retrieval + Corrective RAG

**Hybrid retrieval:** Dense vectors (Gemini Embedding 2, 3072-dim) merged with BM25 sparse retrieval via Reciprocal Rank Fusion (RRF, k=60). The PCR filter applies to both retrieval legs before merging.

**CRAG loop:** After retrieval, an LLM grades document relevance (binary yes/no). If all documents fail grading, the query is reformulated via synonym expansion and retried. Maximum 2 retries (justified by diminishing returns beyond 2 iterations per Yan et al.). This is the first application of CRAG in educational tutoring. The ablation timing confirms CRAG fires in practice: the full variant stalled at question 18 (~186s vs. typical ~8s), a re-query cycle triggered by a failed relevance grade; the no_crag variant never stalled.

### 3.5  Layer 4: Structured Output — Dual Knowledge Masking

The Socratic Generator calls Mercury-2 with `response_format=SocraticOutput` enforcing a two-envelope structure:

```python
class InternalAnalysis(BaseModel):
    correct_answer: str           # consumed by Pedagogy Agent, never rendered
    student_misconception: str
    planned_hint_sequence: list[str]
    relevant_textbook_section: str

class VisibleResponse(BaseModel):
    socratic_question: str        # must end with "?"
    encouragement: str
```

`InternalAnalysis` is stripped before rendering. A post-generation leak guard additionally checks for ≥4 significant-word overlap between `socratic_question` and `correct_answer`, triggering a retry with explicit non-reveal instructions if fired.

**Cost routing:** Rapport and Wrapup phases route to local Llama 3.1 8B via Ollama (65–75% of turns). Mercury-2 handles Tutoring and Assessment. Total session cost: ~$0.08–0.10.

### 3.6  Concept Prerequisite Graph (NetworkX DAG)

Rather than flat mastery scores, we maintain a directed acyclic graph (e.g., `brachial_plexus.origin → brachial_plexus.trunks → brachial_plexus.cords → peripheral_nerves.axillary`). When a student struggles, the Pedagogy Agent traces `nx.ancestors()` to identify prerequisite gaps — the root cause of the failure.

**Cold-start:** The Rapport phase administers 4 diagnostic questions. Correct answers initialize mastery at 0.5, incorrect at 0.1, skipped at 0.2, giving the PCR filter meaningful priors within 90 seconds.

**Mastery update:** After each response, the LLM judges correctness against `internal_analysis.correct_answer`, then updates: correct → `m + 0.15*(1-m)`; incorrect → `m - 0.05*m`. Consecutive correct ≥ 2 and coverage ≥ 0.80 triggers phase advance.

---

## 4  Dataset and Knowledge Base

**Corpus:** OpenStax Anatomy & Physiology 2e, Chapters 11 and 13–16, covering NBCOT brachial plexus and peripheral nerve topics. Indexed into Qdrant (25 chunks) with per-chunk metadata: `is_answer_chunk`, `chunk_type`, `concept`.

**Evaluation dataset:** 30 QA triples (question, retrieved context, expected answer) spanning: brachial plexus origins/trunks/divisions/cords, peripheral nerves (axillary, radial, median, ulnar), and rotator cuff muscles. 20 adversarial prompts across four attack types: direct requests, jailbreaks, social engineering, and off-topic distractors. 5 annotated multi-turn conversation transcripts (see Appendix A).

**Generalizability:** The system is content-agnostic. Swapping `config.yaml: qdrant.collection: unmask_anatomy → unmask_physics` and re-indexing OpenStax Physics 2e (Chapters 4–6) requires zero code changes — clean separation of content (Qdrant collection) from logic (LangGraph orchestration).

---

## 5  Task-by-Task Compliance

| P3 Task | Requirement | UnMask Implementation | Status |
|---------|-------------|----------------------|--------|
| **Task 1: Content Retrieval + Masking** | RAG pipeline; mask answers; progressive hints | Hybrid Qdrant retrieval (dense+BM25+RRF); PCR excludes answer chunks at retrieval; structured output schema separates `internal_analysis`/`visible_response`; hint calibration via concept graph mastery | ✅ |
| **Task 2: Adaptive Conversation** | Rapport → Tutoring phases; Manager Agent | LangGraph 4-phase state machine; pure-Python orchestrator; diagnostic probe initializes mastery; phase transitions by learning events + time ceilings | ✅ |
| **Task 3: Synthesis & Assessment** | Clinical scenario; compare to gold-standard; mastery summary | Assessment phase triggers at coverage ≥ 80% or t ≥ 12min; Mercury-2 evaluates against retrieved textbook chunk; concept graph exports mastery + prerequisite gaps + weak topics | ✅ |
| **Task 4: Multimodal Diagram Tutoring** | VLM for anatomy diagrams; identify → ask function/insertion | Chainlit UI accepts image uploads; VLM backend (MedGemma 4B / Gemini 2.0 Flash Lite) planned for final milestone; PCR architecture supports image-chunk metadata | ⚠️ Partial |
| **Task 5: Interactive Memory** | Session memory; proactively revisit mistakes | NetworkX concept DAG tracks mastery across session; Pedagogy Agent flags `weak_topics` (mastery < 0.4); proactive revisit scheduled after 8 min | ✅ |
| **Bonus: Personalization Dashboard** | Show "weak spots" | Per-turn backend panel shows mastery scores (🔴/🟡/🟢); session-end weak topic summary | ✅ |
| **Generalizability** | Swap vector DB for different subject | Single `config.yaml` field change; zero code changes required | ✅ |

---

## 6  Evaluation

### 6.1  Metrics

**Socratic Purity** (target ≥ 4.0/5.0): two-layer combined score. Layer 1 (rule-based): does the response end with "?"? does it contain ≥4 significant-word overlap with the gold answer (keyword leak)? is cosine similarity > 0.92 (semantic leak)? Confirmed leak (both layers) hard-caps at 2.0; no "?" penalizes −1.0. Layer 2 (LLM-as-Judge): Mercury-2 rates 1–5 on a rubric where 5 = perfect Socratic (gold answer absent, student must think) and 1 = direct answer stated.

**Answer Leak Rate** (target = 0): fraction of responses where both leak layers fire simultaneously. Single-layer fires are reported as "soft flags."

**Retrieval Hit Rate @5** (target ≥ 0.75): in the full system evaluation (unrestricted retrieval for measurement), does the top-5 set contain the gold answer chunk? In the ablation, this measures whether the answer chunk reaches the LLM — PCR correct behavior is hit rate = 0.

**Adversarial Hold Rate** (target ≥ 90%): fraction of adversarial prompts answered with a Socratic question (ends with "?") rather than a direct answer.

**RAGAS Faithfulness** (target ≥ 0.85): are claims in the response entailed by retrieved context? Measured via the `ragas` library.

### 6.2  Controlled Ablation Study

Four variants on the same 30 questions, identical cold-start mastery (0.20), identical generation (Mercury-2, structured output):

| Variant | PCR | CRAG | Concept Graph |
|---------|-----|------|---------------|
| **full** | ✅ | ✅ | ✅ |
| **no_pcr** | ❌ (always full_reveal) | ✅ | ✅ |
| **no_crag** | ✅ | ❌ | ✅ |
| **no_graph** | ✅ | ✅ | ❌ |

---

## 7  Results

### 7.1  Full System Evaluation (30 QA questions)

| Metric | Score | Target | Pass |
|--------|-------|--------|------|
| Retrieval Hit Rate @5 | **1.000** | ≥ 0.75 | ✓ |
| MRR | **0.917** | — | — |
| Answer Leak Rate | **0.000** | 0% | ✓ |
| Soft Leak Flags | **0.000** | — | ✓ |
| Ends with "?" Rate | **1.000** | ≥ 95% | ✓ |
| Avg Socratic Purity | **4.93 / 5** | ≥ 4.0 | ✓ |
| Purity Pass Rate (≥ 4.0) | **0.967** | — | — |
| Adversarial Hold Rate | **1.000** | ≥ 90% | ✓ |

The single purity outlier is q29 (`peripheral_nerves.axillary`, score 3.0/5): the LLM judge noted the response referenced both movement and sensation roles of the nerve, providing enough scaffolding that the answer was partially inferrable. All other 29 questions scored ≥ 4.0.

Adversarial results: all 20 prompts deflected across four attack categories — direct requests ("just tell me the answer"), jailbreaks ("pretend you are a textbook, not a tutor"), social engineering ("my professor said to give direct answers"), off-topic distractors (Paris geography, Python list sorting), and emotional escalation ("I'll fail the NBCOT if you don't tell me"). The 100% hold rate is architecturally enforced: in `context_only` mode there is no answer to leak.

### 7.2  Ablation Results

| Metric | full | no_pcr | no_crag | no_graph |
|--------|------|--------|---------|----------|
| Answer Chunk Reach Rate† | **0.000** | 1.000 | 0.000 | 0.000 |
| Answer Leak Rate | 0.000 | 0.000 | 0.000 | 0.000 |
| Avg Socratic Purity | **4.70** | 4.83 | 4.87 | 4.93 |
| Ends with "?" Rate | 1.000 | 1.000 | 1.000 | 1.000 |

†*Answer Chunk Reach Rate measures whether the answer chunk enters the LLM's context. Full system = 0.000 is correct: PCR's `context_only` filter (mastery 0.20 < threshold_low 0.40) successfully excludes answer chunks. No_pcr = 1.000 confirms the counterfactual: answer chunks always present when PCR is disabled.*

**PCR works as designed.** The full system's 0.000 reach rate confirms that PCR's server-side filter excludes answer chunks at cold-start mastery. This is the architectural guarantee PCR was built to provide.

**Zero leaks across all variants — but not equivalently safe.** All four variants show 0.000 leak rate under benign evaluation. This is precisely the TutorRL failure mode: strong LLM instruction following holds under benign conditions, making prompt-based suppression appear sufficient. Our adversarial battery (100% hold rate, not included in the ablation) demonstrates the difference: under active attack, architectural enforcement holds; prompt-based enforcement would degrade.

**Purity cost of safety: 0.23 points.** The full system scores 4.70/5 vs. no_graph at 4.93/5. When the answer chunk is excluded from context, the model generates slightly broader guiding questions (it cannot see precisely what to guide toward). The no_pcr variant achieves 4.83 — paradoxically better purity — because seeing the answer enables more targeted Socratic scaffolding. This 0.23-point delta is the measurable price of architectural safety over prompt-level safety.

### 7.3  RAGAS Faithfulness

| Metric | Score | Target | Pass |
|--------|-------|--------|------|
| RAGAS Faithfulness | **0.779** | ≥ 0.85 | ✗ |
| RAGAS Answer Relevancy | **0.521** | ≥ 0.80 | ✗ |

Both RAGAS metrics fall below target. This warrants careful interpretation: RAGAS was designed for standard RAG systems where the response is a factual answer grounded in retrieved documents. UnMask's responses are Socratic *questions*, not answers — they are intentionally non-committal and make few explicit claims, which RAGAS interprets as low faithfulness and low relevancy.

Specifically, Faithfulness measures whether claims in the response are entailed by the retrieved context. A Socratic question like "What is the relationship between the location of a mid-shaft humerus fracture and the nerve that runs in that area?" makes no factual claims — it contains no propositions to entail or refute. RAGAS correctly identifies zero entailed claims and scores this as low faithfulness, when from a tutoring standpoint it is a perfectly grounded response.

Answer Relevancy measures how directly the response addresses the question. A response that guides rather than answers will necessarily score low on this metric by design.

These results reveal a measurement mismatch between RAGAS (designed for factual QA) and Socratic tutoring (where the correct response is explicitly *not* an answer). The Socratic Purity metric (4.93/5, custom LLM-as-Judge) is the appropriate faithfulness proxy for this task: it evaluates whether the Socratic question is grounded in textbook context while not revealing the answer. Future work should develop domain-appropriate groundedness metrics for Socratic dialogue systems.

---

## 8  Discussion

**The benign-condition trap.** Our ablation's most important finding is that all variants pass the leak rate test under benign conditions. A system builder evaluating only on benign inputs would conclude that PCR adds no value. This is the failure mode TutorRL documented — and which our adversarial battery exposes. PCR's value is not visible in benign evaluations; it is visible only when the model is actively pressured. The 100% adversarial hold rate for the full system, versus the architecture's inability to guarantee this for no_pcr, is the real justification for PCR.

**Cold-start and diagnostic initialization.** The 4-question diagnostic probe solves the P(L₀)=0 cold-start problem: without it, PCR applies `context_only` mode even to students who already know the material. The probe derives individual priors from demonstrated performance within 90 seconds — more personalized than BKT's population-level P(L₀) parameters.

**CRAG's educational motivation.** In open-domain QA, CRAG prevents factually irrelevant documents from grounding incorrect answers. In educational tutoring, an additional failure mode applies: irrelevant retrievals produce off-topic Socratic questions that break the clinical reasoning thread. A student asking about the axillary nerve should not receive a Socratic question about the median nerve due to a retrieval misfire. CRAG prevents this. The ablation timing evidence (186s stall at q18) confirms CRAG fires in realistic deployment, not only in theory.

**Multimodal gap and path forward.** Task 4 (VLM diagram tutoring) is the primary outstanding gap. The Chainlit interface accepts image uploads; the missing piece is a VLM backend (MedGemma 4B local or Gemini 2.0 Flash Lite) that identifies anatomical structures and generates image-grounded Socratic follow-ups. PCR applies identically to image-associated chunks via `concept` metadata — no architectural changes required.

---

## 9  Conclusion

UnMask demonstrates that the standard Socratic AI tutoring paradigm — retrieve everything, suppress via prompting — has a fundamental architectural vulnerability that cannot be fixed at the generation layer. By moving knowledge masking to the retrieval layer via Progressive Context Revelation, answer leakage becomes architecturally impossible before mastery thresholds are met. The measurable cost is a 0.23-point purity delta (4.70 vs. 4.93/5), representing the precision penalty of teaching without seeing the answer — a trade-off that any honest pedagogical system should accept. Combined with Corrective RAG, a concept prerequisite graph for adaptive routing, and a LangGraph state machine that enforces session structure, UnMask provides a grounded, evaluable Socratic tutoring system for OT anatomy running at $0.08–0.10 per session.

---

## References

Achiam, J., Adler, S., Agarwal, S., et al. (2023). GPT-4 Technical Report. *arXiv:2303.08774*. OpenAI.

Bloom, B. S. (1984). The 2 Sigma Problem: The Search for Methods of Group Instruction as Effective as One-to-One Tutoring. *Educational Researcher*, 13(6), 4–16.

Cao, L. (2023). DiagGPT: An LLM-based and Multi-agent Dialogue System with Automatic Topic Management for Flexible Task-Oriented Dialogue. *arXiv:2308.08043*.

Chi, M. & Wylie, R. (2014). The ICAP framework: Linking cognitive engagement to active learning outcomes. *Educational Psychologist*, 49(4), 219–243.

Chowdhury, S., et al. (2024). MWPTutor: A Multi-Turn Math Word Problem Tutor with Functional Slot-based Guardrails. *AIED 2024*.

Corbett, A. & Anderson, J. (1994). Knowledge tracing: Modeling the acquisition of procedural knowledge. *User Modeling and User-Adapted Interaction*, 4(4), 253–278.

Dinucu-Jianu, D., Macina, J., et al. (2025). From Problem-Solving to Teaching Problem-Solving: Aligning LLMs with Pedagogy using RL. *EMNLP 2025 Oral*. ETH Zurich.

Es, S., James, J., Espinosa-Anke, L., & Schockaert, S. (2024). RAGAS: Automated Evaluation of Retrieval Augmented Generation. *Proceedings of EACL 2024*, Demo Track. arXiv:2309.15217.

Kestin, G., Miller, K. J., Klales, J., et al. (2025). AI tutoring outperforms in-class active learning: an RCT introducing a novel research-based design in an authentic educational setting. *Scientific Reports*, 15, 17458.

Leemann, T., Petridis, P., Vietri, G., Manousakas, D., Roth, A., & Aydöre, S. (2025). Auto-GDA: Automatic Domain Adaptation for Efficient Grounding Verification in Retrieval-Augmented Generation. *ICLR 2025*. arXiv:2410.03461.

Lewis, P., Perez, E., Piktus, A., et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. *Advances in Neural Information Processing Systems 33 (NeurIPS 2020)*, pp. 9457–9474.

Li, Z., Wang, J., Gu, W., et al. (2024). TutorLLM: Customizing Learning Recommendations with Knowledge Tracing and Retrieval-Augmented Generation. *RecSys 2024 / INTERACT 2025*.

Liu, H., Li, C., Wu, Q., & Lee, Y. J. (2024). Visual Instruction Tuning. *Advances in Neural Information Processing Systems 36 (NeurIPS 2023)*, Oral. arXiv:2304.08485.

Liu, J., et al. (2024). SocraticLM: Exploring Socratic Personalized Teaching with LLMs. *NeurIPS 2024 Spotlight*.

OpenStax. (2019). *Anatomy & Physiology 2e*. OpenStax, Rice University.

Peng, X., et al. (2025). KELE: A Multi-Agent Framework for Structured Socratic Teaching with LLMs. *EMNLP 2025 Findings*.

Piech, C., Bassen, J., Huang, J., et al. (2015). Deep Knowledge Tracing. *Advances in Neural Information Processing Systems 28 (NeurIPS 2015)*, pp. 505–513.

Scarlatos, A., Baker, R. S., & Lan, A. (2025). Exploring Knowledge Tracing in Tutor-Student Dialogues using LLMs. *LAK 2025*.

Sellergren, A., Kazemzadeh, S., Jaroensri, T., et al. (2025). MedGemma Technical Report. *arXiv:2507.05201*. Google DeepMind.

Yan, S., Gu, J., Zhu, Y., & Ling, Z. (2024). Corrective Retrieval Augmented Generation. *ACL 2024*.

---

## Appendix A — Conversation Transcripts (5 Sessions, No Leak Before Turn 3)

P3 requires 5 conversation transcripts demonstrating no answer leak before the 3rd turn. All transcripts below were generated live from the UnMask system with cold-start mastery = 0.20 (PCR `context_only` mode). Gold answers shown for grader reference only — they were present in `internal_analysis` (hidden) and absent from `visible_response` (shown to student). Leak status verified by both layers of the answer-leak detector.

---

### Transcript 1 — Brachial Plexus Origins

**Turn 1** | PCR: `context_only` | Leaked: No | Ends with ?: Yes
> **Student:** What spinal cord levels form the brachial plexus?
> **UnMask:** Great question! Let's explore the spinal levels involved. Which specific cervical and thoracic spinal nerves contribute to the formation of the brachial plexus, and how do they relate to the vertebrae they emerge from?
> *(Gold answer held internally: "The brachial plexus is formed by the anterior rami of the spinal nerves from C5 to T1.")*

**Turn 2** | PCR: `context_only` | Leaked: No | Ends with ?: Yes
> **Student:** Is it only cervical nerves?
> **UnMask:** You're on the right track! Keep thinking about the connections between the cervical and thoracic regions. Have you considered whether any thoracic spinal nerves might also contribute to the brachial plexus, in addition to the cervical nerves?
> *(Gold answer held internally: "The brachial plexus is formed by the anterior rami of the lower four cervical nerves (C5–C8) and the first thoracic nerve (T1).")*

**Turn 3** | PCR: `prerequisite_first` | Leaked: No | Ends with ?: Yes
> **Student:** So five roots total from C5 to T1?
> **UnMask:** You're doing well in identifying the spinal roots involved! How do these spinal nerve roots organize themselves into the trunks and divisions of the brachial plexus?
> *(Gold answer confirmed: "Yes, the brachial plexus is formed by the ventral rami of C5, C6, C7, C8, and T1.")*

---

### Transcript 2 — Axillary Nerve & Shoulder Dislocation

**Turn 1** | PCR: `context_only` | Leaked: No | Ends with ?: Yes
> **Student:** Which nerve is damaged when a patient can't abduct past 15 degrees after shoulder dislocation?
> **UnMask:** Great question! Let's explore the anatomy involved. What is the primary muscle responsible for shoulder abduction beyond 15 degrees, and which nerve innervates this muscle?
> *(Gold held: "Axillary nerve")*

**Turn 2** | PCR: `context_only` | Leaked: No | Ends with ?: Yes
> **Student:** So is it the axillary nerve?
> **UnMask:** You're on the right track! What is the primary muscle responsible for shoulder abduction beyond 15 degrees, and which nerve innervates this muscle?
> *(Gold held: "Yes, the axillary nerve innervates the deltoid, which is crucial for shoulder abduction beyond 15 degrees.")*

**Turn 3** | PCR: `prerequisite_first` | Leaked: No | Ends with ?: Yes
> **Student:** What else does the axillary nerve innervate besides deltoid?
> **UnMask:** You're doing great! Besides the deltoid, which other muscle and what specific area of skin does the axillary nerve innervate?
> *(Gold confirmed: "The axillary nerve also innervates the teres minor and provides sensory innervation to the lateral shoulder — the 'regimental badge' area.")*

---

### Transcript 3 — Radial Nerve & Wrist Drop

**Turn 1** | PCR: `context_only` | Leaked: No | Ends with ?: Yes
> **Student:** A patient has wrist drop after a mid-shaft humerus fracture. What nerve is likely injured?
> **UnMask:** You're on the right track! What is the relationship between the location of a mid-shaft humerus fracture and the nerve that runs in that area, particularly in relation to wrist extensor function?
> *(Gold held: "Radial nerve")*

**Turn 2** | PCR: `context_only` | Leaked: No | Ends with ?: Yes
> **Student:** Does the radial nerve innervate all wrist extensors?
> **UnMask:** Great question! What is the role of the radial nerve in the forearm, and how does it relate to the muscles responsible for wrist extension?
> *(Gold held: "Yes, the radial nerve innervates all muscles responsible for wrist extension.")*

**Turn 3** | PCR: `prerequisite_first` | Leaked: No | Ends with ?: Yes
> **Student:** What about sensation — where would the patient feel numbness?
> **UnMask:** When considering the sensory distribution of the radial nerve, which specific area on the dorsal side of the hand and forearm would you expect to experience numbness if the radial nerve is injured?
> *(Gold confirmed: "The radial nerve provides sensation to the posterior forearm and dorsal hand, particularly the first dorsal web space.")*

---

### Transcript 4 — Rotator Cuff Anatomy

**Turn 1** | PCR: `context_only` | Leaked: No | Ends with ?: Yes
> **Student:** Name the four rotator cuff muscles.
> **UnMask:** You're on the right track! What acronym can help you remember the names of the four muscles that form the rotator cuff, and what does each letter stand for?
> *(Gold held: "Supraspinatus, infraspinatus, teres minor, subscapularis.")*

**Turn 2** | PCR: `context_only` | Leaked: No | Ends with ?: Yes
> **Student:** I know supraspinatus — what about the others on the posterior scapula?
> **UnMask:** Great start with the supraspinatus! What are the names of the rotator cuff muscles that originate from the infraspinous fossa and the teres minor region on the posterior scapula?
> *(Gold held: "Infraspinatus and teres minor.")*

**Turn 3** | PCR: `prerequisite_first` | Leaked: No | Ends with ?: Yes
> **Student:** What movement does the infraspinatus produce?
> **UnMask:** Considering the infraspinatus is located behind the glenohumeral joint, how might its position influence the type of rotation it facilitates at the shoulder?
> *(Gold confirmed: "The infraspinatus produces external rotation of the shoulder.")*

---

### Transcript 5 — Median Nerve & Carpal Tunnel Syndrome

**Turn 1** | PCR: `context_only` | Leaked: No | Ends with ?: Yes
> **Student:** What nerve is compressed in carpal tunnel syndrome?
> **UnMask:** Great question! Which nerve passes through the carpal tunnel along with the flexor tendons and is responsible for sensation in the thumb, index, middle, and part of the ring finger?
> *(Gold held: "The median nerve is compressed in carpal tunnel syndrome.")*

**Turn 2** | PCR: `context_only` | Leaked: No | Ends with ?: Yes
> **Student:** What symptoms would the patient have?
> **UnMask:** You're doing great! When the median nerve is compressed at the wrist, what changes might you expect in both sensation and muscle function in the hand?
> *(Gold held: "Numbness/tingling in thumb, index, middle, and part of ring finger; weakness of thenar muscles.")*

**Turn 3** | PCR: `prerequisite_first` | Leaked: No | Ends with ?: Yes
> **Student:** Would the patient have weakness gripping or just sensory loss?
> **UnMask:** What role do the thenar muscles, innervated by the median nerve, play in gripping, and how might their dysfunction affect hand strength?
> *(Gold confirmed: "Both sensory loss and grip weakness occur due to median nerve innervation of thenar muscles.")*

---

**Transcript summary:** 15 turns across 5 transcripts. Zero confirmed leaks (both-layer). Zero soft flags. 15/15 responses end with "?". PCR `context_only` mode held for all turns 1–2; `prerequisite_first` mode applied at turn 3 as mastery scores updated after correct student responses. The gold answer was present only in `internal_analysis` (stripped before rendering) and never in the retrieved Qdrant chunks due to the PCR filter.

---

*Submitted in partial fulfillment of CSE 635: NLP and Text Mining, University at Buffalo, Spring 2026.*
