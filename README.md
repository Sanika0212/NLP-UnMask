<h1 align="center">UnMask</h1>
<p align="center"><em>Socratic AI tutor for Occupational Therapy students — architecturally prevents answer leakage</em></p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11+-58A6FF?style=flat-square&logo=python&logoColor=white"/>
  <img alt="Next.js" src="https://img.shields.io/badge/Next.js-14-58A6FF?style=flat-square&logo=nextdotjs&logoColor=white"/>
  <img alt="LangGraph" src="https://img.shields.io/badge/LangGraph-0.2+-7C3AED?style=flat-square&logo=python&logoColor=white"/>
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.109+-7C3AED?style=flat-square&logo=fastapi&logoColor=white"/>
  <img alt="Qdrant" src="https://img.shields.io/badge/Qdrant-local-58A6FF?style=flat-square&logo=qdrant&logoColor=white"/>
  <img alt="Course" src="https://img.shields.io/badge/CSE_635-UB_Spring_2026-7C3AED?style=flat-square"/>
</p>

<p align="center">
  <a href="#overview">Overview</a> ·
  <a href="#core-novelty-progressive-context-revelation">Core Novelty</a> ·
  <a href="#architecture">Architecture</a> ·
  <a href="#quick-start">Quick Start</a> ·
  <a href="#evaluation">Evaluation</a> ·
  <a href="#project-structure">Project Structure</a>
</p>

---

## Overview

UnMask is a multimodal AI tutor built for Occupational Therapy students preparing for the **NBCOT certification exam**. Unlike every existing Socratic AI tutor, it never gives direct answers — it guides students toward discovering knowledge themselves through Socratic questioning. Answer suppression is not prompt-based; it is **enforced at the retrieval layer**, making leakage architecturally impossible.

<p align="center">
  <img src="screenshots/01_welcome.png" width="720" alt="UnMask welcome screen"/>
</p>

**Key facts:**
- Covers brachial plexus, peripheral nerves (axillary, radial, median, ulnar), and rotator cuff (SITS)
- 15-minute structured sessions: diagnostic → Socratic tutoring → clinical assessment → wrap-up report
- Cross-session memory: mastery scores, weak topics, and misconceptions persist in `localStorage`
- Domain-agnostic: swap the Qdrant collection to retrain on any subject — zero code changes

---

## Core Novelty: Progressive Context Revelation

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

## Architecture

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

### RAG Pipeline (Corrective RAG)

1. **RETRIEVE** — Hybrid search (Gemini dense + BM25 sparse, merged by RRF), top-5 results, PCR filter applied
2. **GRADE** — LLM scores each chunk for relevance; all-fail triggers re-query
3. **RE-QUERY** — Synonym expansion or sub-question decomposition (max 2 retries)
4. **VERIFY** — DeBERTa cross-encoder checks NLI entailment of every claim against retrieved chunks; unfaithful responses blocked and regenerated (pre-delivery gate, not post-hoc)

### Concept Prerequisite Graph

NetworkX DAG of anatomy concepts with prerequisite edges. BKT updates per node per student response. Cold-start solved in v4: diagnostic probe initializes mastery within the first 2 minutes.

```
spinal_cord → brachial_plexus (origin→trunks→divisions→cords→terminal_branches)
                              → peripheral_nerves (axillary, radial, median, ulnar)
                                                  → rotator_cuff (muscles→SITS)
```

---

## Screenshots

<p align="center">
  <img src="screenshots/02_topic_buttons.png" width="700" alt="Topic selection"/>
  <br/><em>Topic selection with prior-session mastery rings for returning students</em>
</p>

<p align="center">
  <img src="screenshots/07_tutoring_starts.png" width="700" alt="Socratic tutoring in progress"/>
  <br/><em>Socratic tutoring — the tutor always ends with a question, never a direct answer</em>
</p>

<p align="center">
  <img src="screenshots/09_visual_hint.png" width="700" alt="Visual hint with anatomy diagram"/>
  <br/><em>Anatomy diagram shown after consecutive incorrect responses; threshold adapts to learning mode</em>
</p>

---

## Quick Start

**Requirements:** Python 3.11+, Node 20+

```bash
# 1. Clone and install Python dependencies
git clone https://github.com/Gustav-Proxi/NLP-UnMask.git
cd NLP-UnMask
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Fill in: OPENAI_API_KEY, GOOGLE_API_KEY
# Set OPENAI_BASE_URL=https://openrouter.ai/api/v1 for OpenRouter
```

**.env values:**
```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=inception/mercury-2
GOOGLE_API_KEY=AIza...
EMBEDDING_PROVIDER=gemini
QDRANT_COLLECTION=unmask_anatomy
```

```bash
# 3. Index the knowledge base
python scripts/index_kb.py           # initial index
python scripts/index_kb.py --recreate  # drop and rebuild

# 4. Start the FastAPI backend (port 8000)
uvicorn src.api:app --reload --port 8000

# 5. In a second terminal — start the Next.js frontend (port 3000)
cd frontend && npm install && npm run dev
```

Open **http://localhost:3000** in your browser.

#### Docker (optional)

```bash
docker build -t unmask .
docker run -p 7860:7860 --env-file .env unmask
```

---

## Evaluation

```bash
python eval/run_eval.py              # full eval (30 QA + 20 adversarial)
python eval/run_eval.py --quick      # first 5 questions (smoke test)
python eval/run_eval.py --skip-ragas # skip RAGAS for speed
python eval/ablation.py              # 4-variant ablation study
```

### Results

| Metric | Score | Target | Pass |
|--------|-------|--------|------|
| Hit Rate @5 | **0.900** | ≥ 0.75 | ✓ |
| Answer Leak Rate | **0.000** | 0% | ✓ |
| Ends with `?` (Socratic form) | **1.000** | ≥ 95% | ✓ |
| Avg Socratic Purity (LLM-as-judge) | **4.87/5** | ≥ 4.0 | ✓ |
| Adversarial Hold Rate | **1.000** | ≥ 90% | ✓ |
| RAGAS Faithfulness | 0.838 | ≥ 0.85 | ✗ |
| RAGAS Answer Relevancy | 0.622 | ≥ 0.80 | ✗ |

Zero answer leakage and perfect adversarial resistance across all 5 attack types (direct request, jailbreak, social engineering, off-topic, escalation).

### Ablation Study (4 Variants)

| Variant | PCR | CRAG | NLI Gate |
|---------|-----|------|----------|
| Baseline (naive RAG + prompt suppression) | — | — | — |
| PCR Only | ✓ | — | — |
| PCR + CRAG | ✓ | ✓ | — |
| Full System | ✓ | ✓ | ✓ |

### Pilot Study

10 UB students (5 OT/health sciences, 5 CS) — 15-min sessions. Pre/post 5-question quiz for learning gain. IRB exempt under 45 CFR 46.104(d)(1). **Status: in progress.**

---

## Knowledge Base

- **Source:** OpenStax Anatomy & Physiology 2e, Chapters 11 and 13–16 (open access)
- **Storage:** Qdrant collection `unmask_anatomy` (local file mode — no Docker required)
- **Per-chunk metadata:** `is_answer_chunk: bool`, `chunk_type` (`context` / `prerequisite` / `answer` / `figure`), `concept`
- **Visual data:** Gray's Anatomy public-domain plates via Wikimedia Commons (16 PNG files, `public/anatomy/`)
- **Eval set:** 30 QA triples across all 13 non-root concepts + 20 adversarial prompts (5 attack types)

### Generalizability

Swap domain with a single config change — zero code changes:

```yaml
# config.yaml
qdrant:
  collection: physics   # was: unmask_anatomy
```

The concept graph auto-generates from the OpenStax Physics 2e table of contents. Demonstrated with 10 physics QA pairs (Chapters 4–6).

---

## Project Structure

```
frontend/                   # Next.js 14 App Router
  src/app/                  # Pages: chat, pilot, survey
  src/components/           # Thread, Aside, Practice/AssessView, ProgressView
  src/lib/                  # Zustand store + per-user localStorage (userStore.ts)
src/                        # FastAPI backend + LangGraph pipeline
  api.py                    # FastAPI entry point
  graph.py                  # LangGraph state machine
  state.py                  # TutoringState TypedDict
  nodes/
    orchestrator.py         # Phase transition logic (zero LLM calls)
    retrieval_planner.py    # PCR filter + hybrid RAG + CRAG loop
    socratic_generator.py   # Structured output masking + YouTube recs
    pedagogy_agent.py       # BKT + concept DAG + mastery update
  knowledge_base/
    chunks.json             # Anatomy chunks with PCR metadata
    concept_graph.json      # Prerequisite DAG (NetworkX-serialized)
config.yaml                 # PCR thresholds, session timing, mastery params
scripts/
  index_kb.py               # Index chunks.json into Qdrant
eval/
  eval_dataset.json         # 30 QA triples
  adversarial_prompts.json  # 20 adversarial prompts
  run_eval.py               # Main evaluation runner
  ablation.py               # 4-variant ablation
  metrics/
    answer_leak.py          # Dual-layer leak detection
    socratic_purity.py      # LLM-as-judge purity score
    retrieval_precision.py  # Hit rate + MRR
    ragas_eval.py           # RAGAS faithfulness + relevancy
public/anatomy/             # 16 anatomy PNGs (Gray's Anatomy, public domain)
```

---

## Cost

| Component | Per session |
|-----------|------------|
| Mercury-2 (via OpenRouter) | ~$0.05–0.08 |
| Qdrant (local) | $0 |
| DeBERTa NLI gate (local) | $0 |
| **Total** | **~$0.08–0.10** |

Total project budget: ~$6–10.

---

## Authors — Equal Contribution

**Sanika Vilas Najan** and **Vaishak Girish Kumar** — CSE 635, University at Buffalo, Spring 2026.

- **Sanika:** PCR filter, Qdrant integration, diagnostic probe, image curation
- **Vaishak:** LangGraph orchestration, Socratic Generator, evaluation framework, pilot study recruitment
