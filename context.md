# UnMask — Project Context

> Onboarding doc. Read this first. Last updated: May 2026 (rev 3).

## What is this?

**UnMask** is a Socratic AI tutor for Occupational Therapy students preparing for the NBCOT certification exam. Built for CSE 635 (NLP and Text Mining), Spring 2026, University at Buffalo.

Authors: Sanika Vilas Najan · Vaishak Girish Kumar

Live: https://huggingface.co/spaces/Gustav-Proxi/UnmaskTutor

---

## Core Idea (one paragraph)

Every existing Socratic AI tutor (Khanmigo, SocraticLM, TutorRL) retrieves the answer first, then relies on prompting to suppress it. Sufficiently capable models bypass this. **UnMask never retrieves the answer until the student demonstrates prerequisite mastery** — enforced at the Qdrant vector DB layer via a metadata filter, not via prompting. This makes answer leakage architecturally impossible rather than just prompt-discouraged.

---

## Architecture (Current — May 2026)

```
Browser (Next.js 14 App Router — frontend/)
    │  SSE stream + REST POST /api/message
    ▼
FastAPI  (src/api.py — port 8000)
    │  uvicorn --reload
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

> **Note**: Chainlit (`app.py`) is retained for backward compatibility / HF Spaces deployment. The primary dev interface is now the Next.js frontend. Both hit the same LangGraph backend.

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

## Frontend Stack (Next.js UI)

**Location**: `frontend/`

- **Framework**: Next.js 14 App Router, TypeScript
- **State**: Zustand (`frontend/src/lib/store.ts`) — session state, mastery, messages, phase, PCR mode
- **Styling**: CSS Modules in `globals.css` — warm paper palette (`oklch()` color space), 3-pane grid layout
- **Layout**: 3-column grid `280px 1fr 340px` — Rail | Main (TopBar + Thread + Composer) | Aside
- **Real-time**: SSE stream from FastAPI (`/api/stream/{session_id}`) via `EventSource`
- **Session setup**: POST `/api/session` → redirect to `/chat`

### Pages

| Route | File | Purpose |
|-------|------|---------|
| `/` | `src/app/page.tsx` | Welcome — topic selection, PCR mode, student name |
| `/chat` | `src/app/chat/page.tsx` | 3-pane chat interface |
| `/pilot` | `src/app/pilot/page.tsx` | Pilot study page |
| `/survey` | `src/app/survey/page.tsx` | Post-session survey (Likert + open feedback) |

### Components

| Component | Purpose |
|-----------|---------|
| `Rail.tsx` | Left sidebar — phase timeline, topic mastery meters, session timer |
| `TopBar.tsx` | Top bar — breadcrumb, nav tabs, toggle buttons, user chip |
| `Thread.tsx` | Message list — turns, supervisor step badges, thinking indicator |
| `Turn.tsx` | Individual message bubble with avatar, quick replies |
| `Aside.tsx` | Right panel — concept DAG, misconceptions, topic mastery bars, agent trace |
| `Composer.tsx` | Text input + End Session button + send button |
| `DiagramCard.tsx` | Visual hint display — animated HTML iframe or image |
| `ProgressView.tsx` | Session summary, per-topic report, YouTube recommendations |
| `Avatar.tsx` | UnMask animated SVG avatar (9 states: idle/listening/thinking/speaking/asking/reveal/assess/celebrate/error) |

### SSE Event Types (FastAPI → Next.js)

| Event | Payload | Effect |
|-------|---------|--------|
| `thinking` | `{text}` | Shows thinking status pill |
| `supervisor` | `{agent, phase, reasoning}` | Adds step badge to thread, updates `phase` in store |
| `state_update` | `{mastery, pcrMode, currentTopic, studyFocus, avatarState}` | Updates Zustand store |
| `phase_change` | `{phase}` | Updates `phase` in store |
| `message` | `{role, content, quickReplies?}` | Appends message to thread |
| `visual_hint` | `{concept, image_url, caption, hint_text}` | Shows DiagramCard in thread |
| `youtube_resources` | `{resources: YouTubeResource[]}` | Shows YouTube Recommended Videos in ProgressView |
| `done` | — | Clears thinking indicator |
| `error` | `{message}` | Shows error state |

---

## Visual Hints System

### Animated HTML Diagrams (Primary)

22 self-contained HTML files in `public/anatomy/` — served by FastAPI at `/static/anatomy/`:

```
brachial_plexus.html   spinal_cord.html     dermatomes.html
rotator_cuff.html      shoulder_joint.html  shoulder_elbow.html
elbow_joint.html       wrist_joint.html     carpal_bones.html
hand_intrinsics.html   musculocutaneous_nerve.html  axillary_nerve.html
median_nerve.html      ulnar_nerve.html     radial_nerve.html
nerve_injury_syndromes.html  peripheral_nerves.html  upper_limb_muscles.html
supraspinatus.html     infraspinatus.html   subscapularis.html  teres_minor.html
```

Each is a standalone animated SVG diagram. Rendered in `<iframe height="420px">` in `DiagramCard.tsx`. Badge shows "Animated".

### Web Search Fallback (Secondary)

When no local `.html` exists for a concept, `src/api.py` calls `search_anatomy_image(concept)`:

1. DuckDuckGo image search (via `duckduckgo-search>=6.2.0`)
2. Filter to trusted domains: `wikipedia`, `wikimedia`, `radiopaedia`, `kenhub`, `teachmeanatomy`
3. Verify top 3 results with Claude Haiku vision API — ask "Does this image show [concept] anatomy? YES/NO"
4. Return first verified URL

External URLs render as `<img>` with badge "Web". Local PNGs render as `<img>` with badge "Image".

---

## Session Phases

| Phase | Time window | Entry condition | Exit condition |
|-------|-------------|-----------------|----------------|
| Rapport (Diagnostic) | 0–120s | session start | 4 diagnostic Qs complete |
| Tutoring | 120–720s | diagnostic_complete | coverage ≥ 0.80 OR t ≥ 720s |
| Revisit | ~480s in Tutoring | weak topic + 180s cooldown | auto |
| Assessment | 720–840s | time/mastery trigger | t ≥ 840s |
| Wrapup | 840–900s | time trigger or quit intent | session end |

**Wrapup Output**: Generates `SessionSummary` with per-topic report card (mastered/progressing/needs_review), misconception highlights, study recommendations, and 2–4 YouTube recommendations for the weakest topics.

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

class YouTubeResource(BaseModel):
    title: str
    channel: str
    query: str                   # for frontend YouTube search link
```

Post-generation: if `socratic_question` contains ≥4 significant words from `correct_answer`, response is rejected and regenerated at temperature=0.

**Break-Socratic mode** (`_REVEAL_SYSTEM`): when the student has 4+ consecutive incorrect answers or explicitly asks for an explanation ("can you explain", "help me understand", "walk me through", etc.), `break_socratic=True` and `_REVEAL_SYSTEM` replaces the tutoring prompt. The model is explicitly instructed to **give the answer directly** — not ask another clinical question. The `socratic_question` field holds a plain explanation ending with a soft check ("Does that make sense?").

---

## Key Mechanism: Supervisor Agent

`supervisor_agent` (src/agents/supervisor.py) runs on every turn:

1. **Rule engine** (`_rule_based_decision`) — pure Python, handles time limits, quit intent, mastery milestones. Always runs.
2. **LLM decision** (`_llm_decision`) — GPT-4o-mini, human-readable reasoning, shown in UI via supervisor SSE event. Runs concurrently.
3. **Merge**: if LLM agrees with rule → use LLM decision (better reasoning text). If they disagree → use rule (safety).

The supervisor also handles proactive revisit scheduling and the rapport→tutoring transition (picking the weakest concept).

---

## State (src/state.py)

`TutoringState` is a `TypedDict`. Key fields:

| Field | Reducer | Notes |
|-------|---------|-------|
| `conversation_history` | `operator.add` | Append-only — pass `[]` on each invoke to avoid doubling |
| `mistake_log` | `operator.add` | Append-only mistake records |
| `mastery_scores` | none | Overwritten each turn |
| `_last_agent` | none | Which specialist ran last turn |
| `_supervisor_reasoning` | none | Shown in UI supervisor step badge |

**Critical**: `conversation_history` uses `operator.add` with SqliteSaver checkpointer. Always pass `state["conversation_history"] = []` before `graph.invoke` — passing the full history doubles it.

---

## Evaluation Results (May 2026)

| Metric | Score | Target | Pass |
|--------|-------|--------|------|
| Hit Rate @5 | 0.900 | ≥ 0.75 | ✓ |
| MRR | 0.604 | — | — |
| Answer Leak Rate | 0.000 | 0% | ✓ |
| Ends with ? | 1.000 | ≥ 95% | ✓ |
| Avg Socratic Purity | 4.87/5 | ≥ 4.0 | ✓ |
| Adversarial Hold Rate | 1.000 | ≥ 90% | ✓ |
| RAGAS Faithfulness | 0.838 | ≥ 0.85 | ✗ (measurement mismatch) |
| RAGAS Answer Relevancy | 0.622 | ≥ 0.80 | ✗ (measurement mismatch) |

RAGAS penalizes Socratic questions that make no factual claims — which is exactly what a good Socratic question does. Socratic Purity (4.87/5) is the appropriate metric.

---

## Running Locally

```bash
# Terminal 1 — FastAPI backend
cd /path/to/NLP\ final\ 2
pip install -r requirements.txt
uvicorn src.api:app --reload --port 8000

# Terminal 2 — Next.js frontend
cd frontend
npm install
npm run dev   # → http://localhost:3000

# Qdrant runs in local file mode (./qdrant_data). No Docker needed.
# Do NOT run eval and app simultaneously — Qdrant file lock conflict.
```

Required env vars (`.env` in project root):
```
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=openai/gpt-4o
GOOGLE_API_KEY=...
QDRANT_COLLECTION=unmask_anatomy
EMBEDDING_PROVIDER=gemini
GOOGLE_API_KEY=...      # for Gemini vision (web diagram verification + student image VLM)
```

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

HF Spaces runs both FastAPI backend and the Next.js frontend (via nginx proxy at port 7860).

```bash
python3 - <<'EOF'
from huggingface_hub import HfApi
HfApi().upload_folder(
    folder_path=".",
    repo_id="Gustav-Proxi/UnmaskTutor",
    repo_type="space",
    ignore_patterns=["*.zip","*.pptx",".git/*","__pycache__/*","*.pyc",
                     ".env","report.pdf","supplementary.pdf",".claude/*",
                     "frontend/.next/*","frontend/node_modules/*"],
)
EOF
```

Set secrets at https://huggingface.co/spaces/Gustav-Proxi/UnmaskTutor/settings:
`OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`, `GOOGLE_API_KEY`, `QDRANT_COLLECTION`, `EMBEDDING_PROVIDER`

---

## File Map

```
app.py                          Chainlit entry point (HF Spaces / legacy)
src/api.py                      FastAPI entry point (Next.js frontend)
src/session_manager.py          Session registry — SQLite-backed, slim-key persistence, 2h TTL
config.yaml                     All thresholds, model names, session timing
src/
  graph.py                      LangGraph state machine definition
  state.py                      TutoringState TypedDict
  agents/
    supervisor.py               LLM router + rule-based fallback
  nodes/
    retrieval_planner.py        PCR filter + hybrid RAG + CRAG
    socratic_generator.py       Structured output generation + leak guard + YouTube recommendations
    pedagogy_agent.py           Mastery update + concept DAG + mistake log
  knowledge_base/
    concept_graph.json          16-concept NetworkX DAG
  anatomy_images.py             concept → anatomy HTML/image mapping
  survey.py                     Pilot study pre/post quiz (Chainlit only)
frontend/
  src/app/
    page.tsx                    Welcome/setup page
    chat/page.tsx               3-pane chat UI
    pilot/page.tsx              Pilot study page
    survey/page.tsx             Post-session survey
    globals.css                 All styles — design tokens, layout, components
    layout.jsx                  Root layout + font imports
  src/components/
    Rail.tsx                    Left sidebar
    TopBar.tsx                  Top navigation bar
    Thread.tsx                  Message list
    Turn.tsx                    Individual message turn
    Aside.tsx                   Right inspector panel
    Composer.tsx                Text input + End Session button
    ProgressView.tsx            Session summary + YouTube recommendations
    DiagramCard.tsx             Visual hint display
    Avatar.tsx                  Animated SVG avatar
  src/lib/
    store.ts                    Zustand session store (dedupes misconceptions by topic+note)
    types.ts                    TypeScript interfaces
    topics.ts                   Topic list (key, label)
eval/
  run_eval.py                   Main eval runner
  ablation.py                   4-variant ablation
  eval_dataset.json             30 QA triples
  adversarial_prompts.json      20 adversarial prompts
  metrics/                      Individual metric modules
public/anatomy/                 22 animated HTML anatomy diagrams
  _shared.css                   Shared styles for HTML diagrams
screenshots/                    Playwright UI screenshots
```
