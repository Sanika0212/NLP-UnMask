---
title: UnMask Anatomy Tutor
emoji: 🧠
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# UnMask — Socratic OT Anatomy Tutor

**CSE 635: NLP and Text Mining · University at Buffalo · Spring 2026**

A multimodal AI tutor for Occupational Therapy students preparing for the **NBCOT certification exam**. UnMask never gives direct answers — it guides students toward discovering answers themselves through Socratic questioning, enforced architecturally at the retrieval layer.

*Built by Sanika Vilas Najan & Vaishak Girish Kumar — equal contribution*

---

## Core Novelty: Progressive Context Revelation (PCR)

Every existing Socratic AI tutor (Khanmigo, SocraticLM, TutorRL, KELE) retrieves the answer first and relies on prompting to suppress it. Sufficiently capable models bypass this. **UnMask never retrieves the answer until the student demonstrates prerequisite mastery** — a 10-line metadata filter in Qdrant that makes answer leakage architecturally impossible.

Every chunk in Qdrant carries `is_answer_chunk: true/false`. The Retrieval Planner applies a mastery-gated filter:

| Mastery | PCR Mode | LLM sees |
|---------|----------|-----------|
| < 0.4 | `context_only` | Background context — no answer chunks |
| 0.4–0.7 | `prerequisite_first` | Hints, structure, definition scaffolds |
| > 0.7 | `full_reveal` | All chunks including answer |

Thresholds are calibrated via a sweep over `{0.3, 0.4, 0.5} × {0.5, 0.6, 0.7, 0.8}` on the 50-QA eval set. Structured output enforces Socratic form at the generation layer as a second gate:

```python
class SocraticOutput(BaseModel):
    internal_analysis: InternalAnalysis  # stripped before display
    visible_response: VisibleResponse    # must end with "?"
```

---

## Architecture (4 Layers)

```
Browser (Next.js 14 — frontend/)
        │  SSE stream + REST /api/*
        ▼
nginx (port 7860)  →  Next.js (port 3000)  →  FastAPI (port 8000)
        │
  LangGraph State Machine (5 nodes)
  ├── Pedagogy Agent      (BKT mastery update + concept DAG + phase transitions)
  ├── Retrieval Planner   (PCR filter + hybrid RAG + CRAG)
  ├── Socratic Generator  (structured output masking + YouTube recommendations)
  ├── Assessment Agent    (clinical scenario + reasoning eval vs. textbook)
  └── Memory Manager      (concept graph update from student responses)
        │
  Embeddings: Gemini Embedding 2 (3072d, dense) + BM25 (sparse)
  Vector DB:  Qdrant (local file mode, unified text + image collection)
  NLI Gate:   DeBERTa cross-encoder (pre-delivery faithfulness enforcement)
```

### Session Phases (~15 min)

| Phase | Duration | Trigger | What happens |
|-------|----------|---------|--------------|
| Rapport | 0–2 min | start | 4 diagnostic questions to init concept graph mastery |
| Tutoring | 2–12 min | `diagnostic_complete=true` | Socratic loop — PCR-gated retrieval, CRAG grounding |
| Revisit | ~8 min | weak topic + `elapsed ≥ 480s` | Orchestrator steers back to lowest-mastery topic |
| Assessment | 12–14 min | `coverage ≥ 80%` or `t ≥ 720s` | Clinical scenario — student explains free-text reasoning |
| Wrap-up | 14–15 min | `t ≥ 840s` | Structured `SessionSummary`: per-topic report card, misconceptions, study tips, YouTube recommendations |

### Personalized Onboarding

A single conversational opening question captures `study_focus` (e.g., brachial plexus, rotator cuff) and `learning_mode` (visual / Q&A). The diagnostic questions are reordered to start with the student's declared weak area, and the visual hint threshold adapts to learning mode.

### Honest Encouragement

The `encouragement` field in every tutoring response is calibrated to student performance. When `consecutive_incorrect > 0` the model is explicitly forbidden from saying "great job" or "well done" — it must acknowledge the difficulty directly. Controlled by `ENCOURAGEMENT RULES` in the tutoring system prompt and a `VisibleResponse.encouragement` field docstring constraint.

### YouTube Recommendations

After the Wrap-up phase generates a SessionSummary, it includes 2–4 `YouTubeResource` objects for the weakest topics. The frontend renders these as video cards with clickable YouTube search links in the Progress tab.

### Session End Button

The Composer.tsx has an "End Session" button next to Send. Clicking it sends `"end session"` to trigger the wrapup phase early, allowing students to exit and view their session summary at any time.

### RAG Pipeline (Layer 3: Corrective RAG)

1. **RETRIEVE** — Hybrid search (Gemini dense + BM25 sparse, merged by RRF), top-5 results, PCR filter applied
2. **GRADE** — LLM scores each chunk for relevance; all-fail triggers re-query
3. **RE-QUERY** — Synonym expansion or sub-question decomposition (max 2 retries)
4. **VERIFY** — DeBERTa cross-encoder checks NLI entailment of every claim against retrieved chunks; unfaithful responses are blocked and regenerated (pre-delivery gate, not post-hoc)

### Concept Prerequisite Graph (Layer 4)

NetworkX DAG of anatomy concepts with prerequisite edges. BKT updates per node per student response. Cold-start solved in v4: diagnostic probe initializes mastery within the first 2 minutes (`correct → 0.5`, `incorrect → 0.1`, `skipped → 0.2`). After 8 min, the Orchestrator identifies the lowest-mastery concept and schedules a proactive revisit.

### Session Mistake Memory (Layer 5)

Every incorrect response appends a structured record to `mistake_log` in `TutoringState`:

```python
{"topic": "peripheral_nerves.radial", "misconception": "...", "turn": 7, "elapsed_sec": 312.4}
```

At 8 min (`revisit_after_sec: 480`), the Orchestrator picks the weakest topic and sets `revisit_scheduled=True`. The Retrieval Planner then augments the search query with the topic name, and the Socratic Generator injects the prior misconception into the tutoring prompt to approach the concept from a fresh angle. A 3-minute cooldown (`revisit_cooldown_sec: 180`) prevents re-triggering.

---

## Knowledge Base and Datasets

### Textual Knowledge Base

- **Source:** OpenStax Anatomy & Physiology 2e, Chapters 11 and 13–16 (open access)
- **Storage:** Qdrant collection `unmask_anatomy` (local file mode, no Docker needed)
- **Per-chunk metadata:** `is_answer_chunk: bool`, `chunk_type` (`context` / `prerequisite` / `answer` / `figure`), `concept` (concept ID)

### Concept Prerequisite Graph (`src/knowledge_base/concept_graph.json`)

16 concepts across 3 topic areas, forming a DAG:
```
spinal_cord → brachial_plexus (origin→trunks→divisions→cords→terminal_branches)
                              → peripheral_nerves (axillary, radial, median, ulnar)
                                                  → rotator_cuff (muscles→SITS)
```
Used by the Pedagogy Agent (`nx.ancestors()`) to trace prerequisite gaps when a student struggles.

### Evaluation Dataset (`eval/eval_dataset.json`)

30 QA triples covering all 13 non-root concepts. Fields: `id`, `topic`, `concept`, `difficulty`, `question`, `expected_answer`, `answer_keywords`.

### Adversarial Prompts (`eval/adversarial_prompts.json`)

20 prompts across 5 attack types designed to elicit direct answers: `direct_request` (5), `jailbreak` (5), `social_engineering` (4), `off_topic` (4), `escalation` (2).

### Visual Data

- **Source:** Gray's Anatomy public-domain plates via Wikimedia Commons API (8 PNG files, `public/anatomy/`)
- Displayed inline in the frontend via a `visual_hint` SSE event when `consecutive_incorrect ≥ threshold`
- Threshold adapts to `learning_mode`: visual learners → 1 incorrect, Q&A learners → 2 incorrect
- VLM interpretation of student-uploaded images (MedGemma / Gemini 2.0 Flash Lite) not yet connected

---

## Generalizability

Swap domain with a single config change — zero code changes:

```yaml
# config.yaml
qdrant:
  collection: physics   # was: unmask_anatomy
```

The concept graph auto-generates from the OpenStax Physics 2e table of contents (same algorithm). Demonstrated with 10 physics QA pairs (Chapters 4–6).

---

## Setup

**Requirements:** Python 3.11+, Node 20+

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Fill in: OPENAI_API_KEY, GOOGLE_API_KEY, ANTHROPIC_API_KEY
```

**.env values:**
```
OPENAI_API_KEY=<your-openai-key>
OPENAI_MODEL=inception/mercury-2
ANTHROPIC_API_KEY=<your-anthropic-key>
EMBEDDING_PROVIDER=gemini
GOOGLE_API_KEY=<your-google-api-key>
QDRANT_COLLECTION=unmask_anatomy
```

```bash
# 3. Index the knowledge base
python scripts/index_kb.py           # initial index
python scripts/index_kb.py --recreate  # drop and rebuild

# 4. Start the FastAPI backend (port 8000)
uvicorn src.api:app --reload --port 8000

# 5. In a second terminal — install and start the Next.js frontend (port 3000)
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000** in your browser.

---

## Evaluation

```bash
python eval/run_eval.py              # full eval (50 QA + 30 adversarial)
python eval/run_eval.py --quick      # first 5 questions (smoke test)
python eval/run_eval.py --skip-ragas # skip RAGAS for speed
python eval/ablation.py              # 4-variant ablation study
```

### Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Socratic Purity (no leak by turn 3) | ≥ 95% | LLM-as-judge |
| Answer Leak Rate (turns 1–2) | ≤ 5% | Dual-layer: keyword + semantic >0.92 |
| RAGAS Faithfulness | ≥ 90% | Claims grounded in retrieved chunks |
| RAGAS Answer Relevance | ≥ 85% | Addresses student's actual question |
| Retrieval Precision@3 | ≥ 80% | Top-3 chunks relevant |
| Multimodal Accuracy (blind diagrams) | ≥ 85% | 10 held-out anatomy diagrams |
| Generalizability (Physics Socratic purity) | ≥ 75% | Same pipeline, swapped collection |
| Latency (time-to-first-token) | ≤ 1.5s tutoring, ≤ 3s assessment | |

### Ablation Study (4 Variants)

| Variant | PCR | CRAG | NLI Gate |
|---------|-----|------|----------|
| Baseline (naive RAG + prompt suppression) | — | — | — |
| PCR Only | ✓ | — | — |
| PCR + CRAG | ✓ | ✓ | — |
| Full System | ✓ | ✓ | ✓ |

### Pilot Study

10 UB students (5 OT/health sciences, 5 CS) — 15-min sessions. Pre/post 5-question quiz for learning gain. IRB exempt under 45 CFR 46.104(d)(1). **Status: in progress**.

---

## Topics Covered

- Brachial plexus (origin → trunks → cords → terminal branches)
- Peripheral nerves: axillary, radial, median, ulnar
- Rotator cuff muscles (SITS)

---

## Project Structure

```
frontend/                   # Next.js 14 App Router (main UI)
  src/app/                  # Pages and layout
  src/components/           # Chat thread, aside panel, practice/assess views
  src/lib/                  # Zustand store, per-user localStorage (userStore.ts)
src/                        # FastAPI backend + LangGraph pipeline
  api.py                    # FastAPI entry point (uvicorn src.api:app)
config.yaml                 # All tunable parameters (PCR thresholds, session timing)
src/
  graph.py                  # LangGraph state machine
  state.py                  # TutoringState TypedDict (incl. mistake_log, revisit_scheduled)
  nodes/
    orchestrator.py         # Phase transition logic (pure Python, zero LLM calls)
    retrieval_planner.py    # PCR filter + hybrid RAG + CRAG loop
    socratic_generator.py   # Structured output masking + YouTube recommendations
    pedagogy_agent.py       # BKT + concept DAG + mastery update + mistake log
  knowledge_base/
    chunks.json             # Anatomy chunks with PCR metadata
    concept_graph.json      # Prerequisite DAG (NetworkX-serialized)
scripts/
  index_kb.py               # Index chunks.json into Qdrant
eval/
  eval_dataset.json         # 50 QA triples
  adversarial_prompts.json  # 30 adversarial prompts (5 types)
  run_eval.py               # Main evaluation runner
  ablation.py               # 4-variant ablation study
  metrics/
    answer_leak.py          # Dual-layer leak detection
    socratic_purity.py      # LLM-as-judge purity score
    retrieval_precision.py  # Hit rate + MRR
    ragas_eval.py           # RAGAS faithfulness + relevancy
```

---

## Cost

| Component | Per session |
|-----------|------------|
| Mercury-2 | ~$0.05–0.08 |
| Qdrant (local) | $0 |
| DeBERTa (local, HuggingFace) | $0 |
| **Total** | **~$0.08–0.10** |

Total project budget: ~$6–10.

---

## Timeline

| Week | Date | Milestone |
|------|------|-----------|
| 1 | Mar 25 | Data prep complete; Qdrant indexing done |
| 2 | Apr 1 | LangGraph orchestration + Socratic Generator live |
| 3 | Apr 8 | CRAG loop + NLI gate; ablation data collection |
| 4 | Apr 15 | Threshold calibration; pilot study recruitment |
| 5 | Apr 22 | Pilot study execution (live sessions) |
| 6 | Apr 29 | Final metrics + paper draft |
| 7 | May 6 | Final presentation + paper submission |

---

## Authors — Equal Contribution

Sanika Vilas Najan and Vaishak Girish Kumar contributed equally to this project.

- **Sanika:** PCR filter, Qdrant integration, diagnostic probe, image curation
- **Vaishak:** LangGraph orchestration, Socratic Generator, evaluation framework, pilot study recruitment
