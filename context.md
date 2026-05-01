# UnMask — Project Context

> Onboarding doc. Read this first. Last updated: May 2026.

## What is this?

**UnMask** is a Socratic AI tutor for Occupational Therapy students preparing for the NBCOT certification exam. Built for CSE 635 (NLP and Text Mining), Spring 2026, University at Buffalo.

Authors: Sanika Vilas Najan · Vaishak Girish Kumar

Live: https://huggingface.co/spaces/Gustav-Proxi/UnmaskTutor

---

## Core Idea (one paragraph)

Every existing Socratic AI tutor (Khanmigo, SocraticLM, TutorRL) retrieves the answer first, then relies on prompting to suppress it. Sufficiently capable models bypass this. **UnMask never retrieves the answer until the student demonstrates prerequisite mastery** — enforced at the Qdrant vector DB layer via a metadata filter, not via prompting. This makes answer leakage architecturally impossible rather than just prompt-discouraged.

---

## Architecture

```
Browser (Chainlit UI)
    │
    ▼
app.py — session lifecycle, UI rendering, Chainlit hooks
    │
    ▼
LangGraph State Machine  (src/graph.py)
    │
    ├── supervisor_agent       LLM router + rule-based fallback (src/agents/supervisor.py)
    │       Routes each turn to: diagnostic | tutor | assessment | wrapup
    │
    ├── retrieval_planner      PCR filter + hybrid RAG + CRAG  (src/nodes/retrieval_planner.py)
    │       Qdrant local file mode — dense (Gemini 3072d) + BM25, merged by RRF(k=60)
    │
    ├── socratic_generator     Structured output knowledge masking  (src/nodes/socratic_generator.py)
    │       GPT-4o via OpenRouter — generates question WITHOUT answer in schema
    │
    └── pedagogy_agent         Mastery update + concept DAG + mistake log  (src/nodes/pedagogy_agent.py)
            NetworkX DAG, 16 concepts, Bayesian mastery update
```

### Graph topology

```
START → supervisor
    ├─ [diagnostic/wrapup] → socratic_generator → pedagogy_agent
    │                                                    └─ [diagnostic_complete] → supervisor (loopback)
    │                                                    └─ otherwise → END
    └─ [tutor/assessment]  → retrieval_planner → socratic_generator → pedagogy_agent → END
```

The loopback (diagnostic → supervisor) runs entirely within a single `graph.invoke` call — no double-invoke.

---

## Session Phases

| Phase | Time window | Entry condition | Exit condition |
|-------|-------------|-----------------|----------------|
| Rapport (Diagnostic) | 0–120s | session start | 4 diagnostic Qs complete |
| Tutoring | 120–720s | diagnostic_complete | coverage ≥ 0.80 OR t ≥ 720s |
| Assessment | 720–840s | time/mastery trigger | t ≥ 840s |
| Wrapup | 840–900s | time trigger or quit intent | session end |

Proactive revisit fires at **t ≥ 480s** in Tutoring if weak topics exist and cooldown (180s) has passed.

---

## Key Mechanism: Progressive Context Revelation (PCR)

Every Qdrant chunk has `is_answer_chunk: bool` and `chunk_type`. The retrieval planner applies a server-side filter:

```python
if mastery < 0.40:   # context_only  → must_not(is_answer_chunk=True)
elif mastery < 0.70: # prerequisite_first → must(chunk_type in ["context","prerequisite"])
else:                # full_reveal   → no filter
```

Thresholds (0.40, 0.70) calibrated via sweep on 50-QA eval set.

---

## Key Mechanism: Structured Output Knowledge Masking

```python
class InternalAnalysis(BaseModel):
    correct_answer: str          # computed by LLM — NEVER shown to student
    student_misconception: str
    planned_hint_sequence: list[str]

class VisibleResponse(BaseModel):
    socratic_question: str       # must end with "?"
    encouragement: str           # calibrated — no hollow praise when student is wrong
```

Post-generation: if `socratic_question` contains ≥4 significant words from `correct_answer`, response is rejected and regenerated at temperature=0.

---

## Key Mechanism: Supervisor Agent

`supervisor_agent` (src/agents/supervisor.py) runs on every turn:

1. **Rule engine** (`_rule_based_decision`) — pure Python, handles time limits, quit intent, mastery milestones. Always runs.
2. **LLM decision** (`_llm_decision`) — GPT-4o-mini, human-readable reasoning, shown in UI via `cl.Step`. Runs concurrently.
3. **Merge**: if LLM agrees with rule → use LLM decision (better reasoning text). If they disagree → use rule (safety).

The supervisor also handles proactive revisit scheduling (previously in orchestrator.py) and the rapport→tutoring transition (picking the weakest concept to start tutoring on).

---

## State (src/state.py)

`TutoringState` is a `TypedDict`. Key fields:

| Field | Reducer | Notes |
|-------|---------|-------|
| `conversation_history` | `operator.add` | Append-only — pass `[]` on each invoke to avoid doubling |
| `mistake_log` | `operator.add` | Append-only mistake records |
| `mastery_scores` | none | Overwritten each turn |
| `_last_agent` | none | Which specialist ran last turn |
| `_supervisor_reasoning` | none | Shown in UI `cl.Step` |

**Critical**: `conversation_history` uses `operator.add` with MemorySaver checkpointer. Always pass `state["conversation_history"] = []` before `graph.invoke` — passing the full history doubles it.

---

## Evaluation Results (May 2026, post-architectural-changes)

| Metric | Score | Target | Pass |
|--------|-------|--------|------|
| Hit Rate @5 | 0.900 | ≥ 0.75 | ✓ |
| MRR | 0.604 | — | — |
| Answer Leak Rate | 0.000 | 0% | ✓ |
| Ends with ? | 1.000 | ≥ 95% | ✓ |
| Avg Socratic Purity | 4.87/5 | ≥ 4.0 | ✓ |
| Adversarial Hold Rate | 1.000 | ≥ 90% | ✓ |
| RAGAS Faithfulness | 0.838 | ≥ 0.85 | ✗ (measurement mismatch — see below) |
| RAGAS Answer Relevancy | 0.622 | ≥ 0.80 | ✗ (measurement mismatch) |

RAGAS penalizes Socratic questions that make no factual claims — which is exactly what a good Socratic question does. Socratic Purity (4.87/5) is the appropriate metric. RAGAS is included for completeness.

---

## Running Locally

```bash
# 1. Install deps
pip install -r requirements.txt

# 2. Set env vars (copy .env.example → .env, fill in keys)
#    OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL, GOOGLE_API_KEY
#    QDRANT_COLLECTION=unmask_anatomy, EMBEDDING_PROVIDER=gemini

# 3. Run
chainlit run app.py --port 8000
```

Qdrant runs in local file mode — `./qdrant_data`. No Docker needed.
Do NOT run eval and app simultaneously — Qdrant file lock will conflict.

---

## Running Evals

```bash
python eval/run_eval.py              # full eval (30 Qs + 20 adversarial)
python eval/run_eval.py --quick      # first 5 only (smoke test)
python eval/run_eval.py --skip-ragas # skip RAGAS (faster, fewer API calls)
python eval/ablation.py              # ablation across 4 variants
```

Kill the app before running evals (shared Qdrant file lock).

---

## Deploying to HuggingFace Spaces

```bash
# git push via HF Python API (git push rejected — HF requires Xet for binaries)
python3 - <<'EOF'
from huggingface_hub import HfApi
HfApi().upload_folder(
    folder_path=".",
    repo_id="Gustav-Proxi/UnmaskTutor",
    repo_type="space",
    ignore_patterns=["*.zip","*.pptx",".git/*","__pycache__/*","*.pyc",
                     ".env","report.pdf","supplementary.pdf",".claude/*"],
)
EOF
```

Set secrets at https://huggingface.co/spaces/Gustav-Proxi/UnmaskTutor/settings:
`OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`, `GOOGLE_API_KEY`, `QDRANT_COLLECTION`, `EMBEDDING_PROVIDER`

---

## File Map

```
app.py                          Chainlit entry point — UI, session lifecycle
config.yaml                     All thresholds, model names, session timing
src/
  graph.py                      LangGraph state machine definition
  state.py                      TutoringState TypedDict
  agents/
    supervisor.py               LLM router + rule-based fallback
  nodes/
    retrieval_planner.py        PCR filter + hybrid RAG + CRAG
    socratic_generator.py       Structured output generation + leak guard
    pedagogy_agent.py           Mastery update + concept DAG + mistake log
  knowledge_base/
    concept_graph.json          16-concept NetworkX DAG
  anatomy_images.py             concept → Gray's Anatomy image mapping
  survey.py                     Pilot study pre/post quiz
eval/
  run_eval.py                   Main eval runner
  ablation.py                   4-variant ablation
  eval_dataset.json             30 QA triples
  adversarial_prompts.json      20 adversarial prompts
  metrics/
    answer_leak.py
    socratic_purity.py
    retrieval_precision.py
    ragas_eval.py
public/anatomy/                 Gray's Anatomy PNG images (16 plates)
screenshots/                    Auto-generated UI screenshots (playwright)
```
