# System Generalizability: From Anatomy to Any Subject Domain

## Overview

UnMask is **entirely subject-agnostic**. The system architecture places all domain-specific content in configuration files and external knowledge sources (vector database, concept graphs, assets), not in the core LangGraph reasoning pipeline. This means the same codebase can tutor any subject by swapping knowledge bases.

## Subject-Agnostic Architecture

### Core Components

The LangGraph pipeline (`src/graph.py`) contains **zero anatomy-specific logic**:

- **`supervisor_agent`** (`src/agents/supervisor.py`): Routes based on tutoring phase (rapport → diagnostic → tutoring → assessment → wrapup). No anatomy assumptions.
- **`retrieval_planner`** (`src/nodes/retrieval_planner.py`): Executes semantic search over Qdrant collection specified by `QDRANT_COLLECTION` env var. Works with any domain.
- **`socratic_generator`** (`src/nodes/socratic_generator.py`): Generates Socratic questions from retrieved chunks. Queries are built from the `concept_graph.json` and student responses — no anatomy hardcoding.
- **`pedagogy_agent`** (`src/nodes/pedagogy_agent.py`): Evaluates answers, computes mastery, adjusts routing. Uses only the concept prerequisite graph structure (applies to any DAG).

### Data Sources (Configurable Per Domain)

| Source | Location | Anatomy Use | Generalization |
|--------|----------|-------------|-----------------|
| **Vector DB** | Qdrant, collection name from `QDRANT_COLLECTION` env var | `unmask_anatomy` collection with ingested anatomy textbook excerpts | Swap to `unmask_physics`, `unmask_chemistry`, etc. with domain PDFs |
| **Concept Graph** | `src/knowledge_base/concept_graph.json` | 39 anatomy concepts (spinal cord → nerve injuries, rotator cuff, etc.) in prerequisite DAG | Replace with Physics DAG (mechanics → forces → torque → work-energy, etc.) |
| **Visual Assets** | `public/anatomy/*.{png,html}` | 22 anatomy diagrams (brachial plexus, median nerve, rotator cuff, etc.) | Replace with Physics diagrams (free-body diagrams, lever systems, pulley systems, etc.) |
| **Image Mappings** | `src/anatomy_images.py` — `ANATOMY_DIAGRAMS` dict | Maps concept keys (e.g., `"peripheral_nerves.radial"`) to image files and ASCII fallbacks | Rename to `physics_images.py`, update dict keys to Physics concepts |

---

## Step-by-Step: Migrate from Anatomy to Physics

### Step 1: Update Environment Variables

**File:** `.env`

```bash
# Before (Anatomy)
QDRANT_COLLECTION=unmask_anatomy

# After (Physics)
QDRANT_COLLECTION=unmask_physics
```

### Step 2: Replace the Concept Graph

**File:** `src/knowledge_base/concept_graph.json`

Create a new JSON file mirroring the anatomy structure. Example for a Physics Mechanics module:

```json
{
  "concepts": {
    "kinematics.motion": {
      "label": "Motion and Position",
      "topic": "kinematics",
      "prerequisites": []
    },
    "kinematics.velocity": {
      "label": "Velocity and Speed",
      "topic": "kinematics",
      "prerequisites": ["kinematics.motion"]
    },
    "kinematics.acceleration": {
      "label": "Acceleration",
      "topic": "kinematics",
      "prerequisites": ["kinematics.velocity"]
    },
    "forces.newtons_first": {
      "label": "Newton's First Law: Inertia",
      "topic": "forces",
      "prerequisites": ["kinematics.acceleration"]
    },
    "forces.newtons_second": {
      "label": "Newton's Second Law: F = ma",
      "topic": "forces",
      "prerequisites": ["forces.newtons_first", "kinematics.acceleration"]
    },
    "forces.newtons_third": {
      "label": "Newton's Third Law: Action-Reaction",
      "topic": "forces",
      "prerequisites": ["forces.newtons_first"]
    },
    "work_energy.work": {
      "label": "Work and Force Displacement",
      "topic": "work_energy",
      "prerequisites": ["forces.newtons_second"]
    },
    "work_energy.kinetic_energy": {
      "label": "Kinetic Energy",
      "topic": "work_energy",
      "prerequisites": ["kinematics.velocity", "forces.newtons_second"]
    },
    "work_energy.potential_energy": {
      "label": "Gravitational and Elastic Potential Energy",
      "topic": "work_energy",
      "prerequisites": ["forces.newtons_second"]
    },
    "work_energy.conservation": {
      "label": "Conservation of Energy",
      "topic": "work_energy",
      "prerequisites": ["work_energy.kinetic_energy", "work_energy.potential_energy"]
    },
    "rotational.torque": {
      "label": "Torque and Rotational Motion",
      "topic": "rotational",
      "prerequisites": ["forces.newtons_second"]
    },
    "rotational.angular_momentum": {
      "label": "Angular Momentum",
      "topic": "rotational",
      "prerequisites": ["rotational.torque", "work_energy.conservation"]
    }
  }
}
```

**Key principles:**
- Maintain the hierarchical structure: concepts depend on prerequisites
- Each concept has a `label` (human-readable name), `topic` (grouping), and `prerequisites` (list of concept IDs)
- The pedagogy system will traverse this DAG to sequence learning

### Step 3: Ingest Domain Content into Qdrant

Use the existing ingestion pipeline. Example:

```bash
# Anatomy (original)
python src/ingestion/ingest.py \
  --pdf-dir data/anatomy_textbooks/ \
  --collection unmask_anatomy \
  --chunk-size 500

# Physics (new)
python src/ingestion/ingest.py \
  --pdf-dir data/physics_textbooks/ \
  --collection unmask_physics \
  --chunk-size 500
```

**What happens:**
- PDFs are chunked and embedded using the configured embedding provider (Gemini/OpenAI)
- Chunks are stored in Qdrant under the specified collection
- No code changes needed — the ingestion script is domain-agnostic

### Step 4: Update Asset Mappings

**File:** `src/anatomy_images.py` → rename to `src/domain_images.py` (or keep the name, update contents)

**Before (Anatomy):**
```python
ANATOMY_DIAGRAMS = {
    "peripheral_nerves.median": {
        "caption": "Median nerve — course, motor, sensory and CTS clinical features",
        "image_file": "median_nerve.png",
        "diagram": "..."
    },
    "rotator_cuff.supraspinatus": {
        "caption": "Supraspinatus — initiates abduction, empty can test, impingement",
        "image_file": "shoulder_joint.png",
        "diagram": "..."
    },
    # ... 37 more anatomy concepts
}
```

**After (Physics):**
```python
PHYSICS_DIAGRAMS = {
    "forces.newtons_second": {
        "caption": "Newton's Second Law: F = ma with free-body diagram",
        "image_file": "newtons_second_law.png",
        "diagram": "Free body diagram showing forces and resulting acceleration"
    },
    "rotational.torque": {
        "caption": "Torque: τ = r × F, lever systems",
        "image_file": "torque_lever.png",
        "diagram": "Diagram showing moment arm, fulcrum, and torque vectors"
    },
    # ... more physics concepts
}
```

**Update imports:**
```python
# In src/api.py, src/graph.py, and any node that uses images:
from src.domain_images import PHYSICS_DIAGRAMS as DIAGRAMS  # or anatomy
```

### Step 5: No Changes Needed to Core Logic

The following files require **zero modifications** for a domain swap:

- `src/graph.py` — LangGraph pipeline definition
- `src/agents/supervisor.py` — phase routing logic
- `src/nodes/retrieval_planner.py` — semantic search (works on any Qdrant collection)
- `src/nodes/socratic_generator.py` — Socratic question generation (reads from concept graph)
- `src/nodes/pedagogy_agent.py` — mastery tracking and diagnostic logic
- `src/api.py` — FastAPI endpoints (just swap the image lookup function)

The system reads `QDRANT_COLLECTION`, `concept_graph.json`, and asset mappings at runtime. No recompilation or code redeploy needed.

---

## Minimal Example: Physics Mechanics Module

### File Structure for Physics Deployment

```
unmask-physics/
├── .env (set QDRANT_COLLECTION=unmask_physics)
├── src/knowledge_base/concept_graph.json (Physics DAG)
├── src/physics_images.py (diagrams and captions)
├── public/physics/ (diagrams: newtons_second_law.png, torque_lever.png, etc.)
├── data/physics_textbooks/ (PDFs to ingest)
├── src/ (all other files — UNCHANGED)
└── config.yaml (domain-agnostic tutoring config)
```

### Ingestion

```bash
python src/ingestion/ingest.py \
  --pdf-dir data/physics_textbooks/ \
  --collection unmask_physics \
  --vector-size 1536
```

### Session

```bash
# Client calls (unchanged API):
POST /api/sessions
POST /api/sessions/{session_id}/setup?topic=forces&mode=visual
POST /api/sessions/{session_id}/messages

# Under the hood:
# - supervisor routes via concept_graph.json (Physics DAG)
# - retrieval_planner searches unmask_physics collection
# - socratic_generator pulls from src/physics_images.py
# - pedagogy_agent tracks mastery of force/torque/energy concepts
```

---

## Validation: Proof of Concept

To verify generalizability:

1. **Create a new Qdrant collection** with Physics textbook chunks:
   ```bash
   curl -X PUT http://localhost:6333/collections/unmask_physics \
     -H "Content-Type: application/json" \
     -d '{"vectors": {"size": 1536, "distance": "Cosine"}}'
   ```

2. **Ingest 2–3 Physics textbook chapters** (just to populate the collection):
   ```bash
   python src/ingestion/ingest.py --collection unmask_physics --pdf-dir ./sample_physics_pdfs/
   ```

3. **Start a session with Physics domain:**
   ```bash
   export QDRANT_COLLECTION=unmask_physics
   python -c "from src.graph import make_initial_state; s = make_initial_state(); print(s.to_dict())" 
   ```

4. **Run the Socratic tutor:**
   ```bash
   uvicorn src.api:app --reload
   # POST /api/sessions with topic: "forces" or "torque"
   ```

Result: The tutor adapts to Physics concepts, generates diagnostic questions about forces/torque, and retrieves Physics content from the vector DB — all without touching the reasoning engine.

---

## Summary: Subject-Agnostic Design

| Aspect | Anatomy | Physics | General |
|--------|---------|---------|---------|
| **Reasoning Engine** | `src/graph.py` + nodes | Same | Domain-independent LangGraph |
| **Knowledge Base** | `unmask_anatomy` collection | `unmask_physics` collection | Any Qdrant collection (env var) |
| **Concept DAG** | Spinal cord → Nerves → Injuries | Kinematics → Forces → Energy | JSON prerequisite graph |
| **Diagrams** | `public/anatomy/*.png` | `public/physics/*.png` | Any asset directory |
| **Code Changes** | — | — | Zero in core pipeline |

**Conclusion:** UnMask's curriculum is entirely data-driven. The tutoring logic is universal; only the knowledge base (Qdrant), concept structure (JSON), and visual assets need to be domain-specific. This design enables rapid deployment to new subjects without reimplementation.
