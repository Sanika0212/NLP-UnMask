"""
Pedagogy Agent — mastery updates, concept prerequisite graph, diagnostic probe.

After each student response, this node:
  1. Evaluates if the response was correct (LLM judge using internal_analysis)
  2. Updates mastery scores via simple Bayesian update
  3. Traces prerequisite gaps in the concept graph
  4. Flags weak topics for proactive revisit
  5. Updates coverage_ratio and diagnostic_complete
"""
from __future__ import annotations

import json
import os
from typing import Optional

import networkx as nx
import yaml
from openai import OpenAI

from src.state import TutoringState

with open("config.yaml") as f:
    _cfg = yaml.safe_load(f)

_M = _cfg["mastery"]

# ── Concept graph (loaded once) ───────────────────────────────────────────────

_concept_graph: Optional[nx.DiGraph] = None


def _load_concept_graph() -> nx.DiGraph:
    global _concept_graph
    if _concept_graph is not None:
        return _concept_graph
    path = os.path.join(
        os.path.dirname(__file__), "..", "knowledge_base", "concept_graph.json"
    )
    with open(path) as f:
        data = json.load(f)
    G = nx.DiGraph()
    for concept_id, info in data["concepts"].items():
        G.add_node(concept_id, **{k: v for k, v in info.items() if k != "prerequisites"})
        for prereq in info.get("prerequisites", []):
            G.add_edge(prereq, concept_id)  # prereq → concept
    _concept_graph = G
    return G


# ── Client ────────────────────────────────────────────────────────────────────

_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.getenv("OPENAI_BASE_URL"),
            timeout=30.0,
        )
    return _client


# ── Correctness evaluation ────────────────────────────────────────────────────

def _evaluate_response(
    student_answer: str,
    internal: Optional[dict],
) -> tuple[bool, str]:
    """
    Returns (is_correct, feedback_reason).
    Uses internal_analysis.correct_answer as the gold standard.
    Falls back to heuristic if internal_analysis is not available.
    """
    if internal is None:
        # Rapport phase — no correctness judgment
        return True, "rapport"

    correct_answer = internal.get("correct_answer", "")
    if not correct_answer:
        return True, "no gold answer"

    import time
    client = _get_client()
    prompt = (
        f"Gold answer: {correct_answer}\n"
        f"Student's response: {student_answer}\n\n"
        "Is the student's response substantially correct? "
        "Reply with 'correct' or 'incorrect' followed by one sentence of reason."
    )
    for _attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=_cfg["llm"].get("utility_model", _cfg["llm"]["model"]),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=60,
                temperature=0,
            )
            break
        except Exception as e:
            if _attempt == 2:
                raise
            time.sleep(2 ** _attempt)
    text = (resp.choices[0].message.content or "incorrect").strip().lower()
    is_correct = text.startswith("correct")
    return is_correct, text


# ── Mastery update ────────────────────────────────────────────────────────────

def _update_mastery(current: float, is_correct: bool) -> float:
    if is_correct:
        updated = current + _M["correct_gain"] * (1 - current)
    else:
        updated = current - _M["incorrect_loss"] * current
    return max(0.0, min(1.0, updated))


# ── Coverage ratio ────────────────────────────────────────────────────────────

def _compute_coverage(mastery: dict[str, float], G: nx.DiGraph) -> float:
    if G.number_of_nodes() == 0:
        return 0.0
    mastered = sum(
        1 for node in G.nodes
        if mastery.get(node, _M["default_prior"]) >= _cfg["pcr"]["threshold_high"]
    )
    return mastered / G.number_of_nodes()


# ── Prerequisite gap tracing ──────────────────────────────────────────────────

def _find_prerequisite_gaps(topic: str, mastery: dict, G: nx.DiGraph) -> list[str]:
    """
    Given a topic that the student struggled with, trace back to find
    prerequisite concepts with low mastery — the ROOT CAUSE of the failure.
    """
    if topic not in G:
        return []
    gaps = []
    for prereq in nx.ancestors(G, topic):
        if mastery.get(prereq, _M["default_prior"]) < _M["weak_threshold"]:
            gaps.append(prereq)
    return gaps


# ── Diagnostic probe ──────────────────────────────────────────────────────────

# One entry per major concept. Each has: question, concept, keywords (for scoring), topic (for ordering).
_DIAGNOSTIC_BANK: list[dict] = [
    # brachial_plexus
    {"question": "What spinal cord levels make up the brachial plexus?",
     "concept": "brachial_plexus.origin", "topic": "brachial_plexus",
     "keywords": ["c5", "c6", "c7", "c8", "t1"]},
    {"question": "What are the five terminal branches of the brachial plexus?",
     "concept": "brachial_plexus.terminal_branches", "topic": "brachial_plexus",
     "keywords": ["musculocutaneous", "axillary", "radial", "median", "ulnar"]},
    {"question": "What are the three trunks of the brachial plexus and which roots form each?",
     "concept": "brachial_plexus.trunks", "topic": "brachial_plexus",
     "keywords": ["superior", "middle", "inferior", "c5 c6", "c7", "c8 t1"]},
    {"question": "Which division of the brachial plexus gives rise to the medial cord, and what nerve does it primarily form?",
     "concept": "brachial_plexus.cords", "topic": "brachial_plexus",
     "keywords": ["anterior", "medial cord", "ulnar", "inferior trunk"]},
    # rotator_cuff
    {"question": "Name the four rotator cuff muscles.",
     "concept": "rotator_cuff.muscles", "topic": "rotator_cuff",
     "keywords": ["supraspinatus", "infraspinatus", "teres minor", "subscapularis"]},
    {"question": "What is the function of the supraspinatus and which nerve innervates it?",
     "concept": "rotator_cuff.supraspinatus", "topic": "rotator_cuff",
     "keywords": ["abduction", "suprascapular"]},
    {"question": "Which rotator cuff muscle is responsible for internal rotation of the shoulder?",
     "concept": "rotator_cuff.subscapularis", "topic": "rotator_cuff",
     "keywords": ["subscapularis", "internal rotation", "subscapular"]},
    {"question": "What is the significance of the 'critical zone' of the supraspinatus tendon?",
     "concept": "rotator_cuff.tears", "topic": "rotator_cuff",
     "keywords": ["avascular", "ischemia", "tear", "impingement", "1 cm"]},
    # peripheral_nerves
    {"question": "Which nerve innervates the deltoid, and at what spinal levels?",
     "concept": "peripheral_nerves.axillary", "topic": "peripheral_nerves",
     "keywords": ["axillary", "c5", "c6"]},
    {"question": "What motor and sensory deficits result from a high radial nerve injury?",
     "concept": "peripheral_nerves.radial", "topic": "peripheral_nerves",
     "keywords": ["wrist drop", "finger extension", "dorsum"]},
    {"question": "A patient cannot oppose the thumb and has a flat thenar eminence — which nerve is injured?",
     "concept": "peripheral_nerves.median", "topic": "peripheral_nerves",
     "keywords": ["median", "ape hand", "thenar"]},
    {"question": "What is the ulnar nerve's role in intrinsic hand function?",
     "concept": "peripheral_nerves.ulnar", "topic": "peripheral_nerves",
     "keywords": ["interossei", "hypothenar", "claw", "adduction"]},
    # spinal_cord
    {"question": "At what vertebral level does the spinal cord end, and what continues below?",
     "concept": "spinal_cord.anatomy", "topic": "spinal_cord",
     "keywords": ["l1", "l2", "conus", "cauda equina"]},
    {"question": "What is the difference between the central canal and the subarachnoid space in the spinal cord?",
     "concept": "spinal_cord.meninges", "topic": "spinal_cord",
     "keywords": ["pia", "arachnoid", "dura", "csf", "meninges"]},
    {"question": "Describe the Brown-Séquard syndrome — which tracts are damaged and what are the clinical findings?",
     "concept": "spinal_cord.brown_sequard", "topic": "spinal_cord",
     "keywords": ["hemisection", "ipsilateral", "contralateral", "spinothalamic", "dorsal column"]},
    {"question": "What is the somatotopic organisation of the corticospinal tract within the spinal cord?",
     "concept": "spinal_cord.tracts", "topic": "spinal_cord",
     "keywords": ["lateral", "anterior", "sacral", "cervical", "somatotopic"]},
    # shoulder_joint
    {"question": "What type of joint is the glenohumeral joint, and what structures provide its stability?",
     "concept": "shoulder_joint.glenohumeral", "topic": "shoulder_joint",
     "keywords": ["ball and socket", "labrum", "rotator cuff", "glenohumeral ligament"]},
    {"question": "Which bones articulate at the acromioclavicular joint and why is it clinically important?",
     "concept": "shoulder_joint.ac_joint", "topic": "shoulder_joint",
     "keywords": ["acromion", "clavicle", "separation", "fall"]},
    {"question": "What is the role of the glenoid labrum and what injury is associated with its tear?",
     "concept": "shoulder_joint.labrum", "topic": "shoulder_joint",
     "keywords": ["deepens", "bankart", "slap", "instability", "dislocation"]},
    {"question": "Which shoulder bursa is most commonly inflamed in impingement syndrome?",
     "concept": "shoulder_joint.bursitis", "topic": "shoulder_joint",
     "keywords": ["subacromial", "subdeltoid", "impingement", "supraspinatus"]},
    # elbow_joint
    {"question": "What is the carrying angle of the elbow and which condition alters it?",
     "concept": "elbow_joint.anatomy", "topic": "elbow_joint",
     "keywords": ["valgus", "cubitus valgus", "cubitus varus", "degrees"]},
    {"question": "Where does the ulnar nerve pass at the elbow, and what symptoms result from compression there?",
     "concept": "elbow_joint.cubital_tunnel", "topic": "elbow_joint",
     "keywords": ["cubital tunnel", "medial epicondyle", "ring", "little finger", "tingling"]},
    {"question": "What structures form the medial collateral ligament complex of the elbow?",
     "concept": "elbow_joint.ligaments", "topic": "elbow_joint",
     "keywords": ["anterior bundle", "ulnar collateral", "posterior bundle", "transverse"]},
    {"question": "A pitcher presents with medial elbow pain during acceleration — which structure is most likely injured?",
     "concept": "elbow_joint.ucl_injury", "topic": "elbow_joint",
     "keywords": ["ulnar collateral ligament", "ucl", "valgus stress", "tommy john"]},
    # wrist_hand
    {"question": "Name the two rows of carpal bones in order from radial to ulnar.",
     "concept": "wrist_hand.carpals", "topic": "wrist_hand",
     "keywords": ["scaphoid", "lunate", "triquetrum", "pisiform", "trapezium", "trapezoid", "capitate", "hamate"]},
    {"question": "What muscles form the thenar eminence and what nerve innervates them?",
     "concept": "wrist_hand.intrinsic_muscles", "topic": "wrist_hand",
     "keywords": ["abductor pollicis", "flexor pollicis brevis", "opponens", "median"]},
    {"question": "What is carpal tunnel syndrome — which nerve is compressed and what are the classic symptoms?",
     "concept": "wrist_hand.carpal_tunnel", "topic": "wrist_hand",
     "keywords": ["median", "transverse carpal ligament", "numbness", "thenar wasting", "tinel", "phalen"]},
    {"question": "What is the anatomical snuffbox and why is tenderness there clinically significant?",
     "concept": "wrist_hand.scaphoid", "topic": "wrist_hand",
     "keywords": ["scaphoid", "fracture", "avascular necrosis", "radial artery", "extensor pollicis"]},
    # dermatomes
    {"question": "Which dermatome supplies the thumb, and which supplies the little finger?",
     "concept": "dermatomes.upper_limb", "topic": "dermatomes",
     "keywords": ["c6", "c8", "thumb", "little finger"]},
    {"question": "A patient reports numbness over the lateral forearm — which spinal level is involved?",
     "concept": "dermatomes.clinical", "topic": "dermatomes",
     "keywords": ["c6", "lateral", "musculocutaneous"]},
    {"question": "Which dermatome covers the nipple line, and what is its clinical significance in spinal injury assessment?",
     "concept": "dermatomes.thoracic", "topic": "dermatomes",
     "keywords": ["t4", "t5", "nipple", "sensory level", "incomplete injury"]},
    {"question": "A patient has loss of sensation over the medial arm and medial forearm — which roots are affected?",
     "concept": "dermatomes.medial_arm", "topic": "dermatomes",
     "keywords": ["t1", "c8", "medial cutaneous", "medial brachial"]},
    # nerve_injuries
    {"question": "What is Saturday night palsy and which nerve is involved?",
     "concept": "nerve_injuries.radial", "topic": "nerve_injuries",
     "keywords": ["radial", "spiral groove", "wrist drop", "compression"]},
    {"question": "Describe Erb's palsy — which roots are injured and what is the classic limb posture?",
     "concept": "nerve_injuries.brachial_plexus", "topic": "nerve_injuries",
     "keywords": ["c5", "c6", "waiter's tip", "adduction", "internal rotation"]},
    {"question": "What is Klumpke's palsy — which roots are damaged and what is the characteristic hand deformity?",
     "concept": "nerve_injuries.klumpke", "topic": "nerve_injuries",
     "keywords": ["c8", "t1", "claw hand", "intrinsic", "horner"]},
    {"question": "A patient presents with an ulnar claw hand — at what level is the ulnar nerve most likely injured and why?",
     "concept": "nerve_injuries.ulnar_claw", "topic": "nerve_injuries",
     "keywords": ["distal", "wrist", "intrinsic", "lumbrical", "ring", "little finger"]},
    # upper_limb_muscles
    {"question": "What is the innervation and primary action of the biceps brachii?",
     "concept": "upper_limb_muscles.elbow_flexors", "topic": "upper_limb_muscles",
     "keywords": ["musculocutaneous", "c5", "c6", "flexion", "supination"]},
    {"question": "Which nerve innervates the triceps and at what spinal level?",
     "concept": "upper_limb_muscles.elbow_extensors", "topic": "upper_limb_muscles",
     "keywords": ["radial", "c7", "extension"]},
    {"question": "What is the dual innervation of the flexor digitorum profundus and which digits does each nerve supply?",
     "concept": "upper_limb_muscles.fdp", "topic": "upper_limb_muscles",
     "keywords": ["median", "anterior interosseous", "ulnar", "index", "middle", "ring", "little"]},
    {"question": "Which muscle is the prime mover for shoulder abduction from 0–15 degrees and which takes over from 15–90 degrees?",
     "concept": "upper_limb_muscles.abductors", "topic": "upper_limb_muscles",
     "keywords": ["supraspinatus", "deltoid", "0-15", "15-90", "axillary"]},
]

# topic → bank indices (for priority ordering)
_TOPIC_BANK_MAP: dict[str, list[int]] = {}
for _i, _entry in enumerate(_DIAGNOSTIC_BANK):
    _TOPIC_BANK_MAP.setdefault(_entry["topic"], []).append(_i)

# keyword triggers per topic for focus detection
_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "brachial_plexus": ["brachial", "plexus"],
    "rotator_cuff": ["rotator", "cuff", "supraspinatus", "infraspinatus"],
    "peripheral_nerves": ["nerve", "axillary", "radial", "median", "ulnar", "musculocutaneous"],
    "spinal_cord": ["spinal cord", "spinal", "cord", "conus", "cauda"],
    "shoulder_joint": ["shoulder", "glenohumeral", "ac joint", "acromioclavicular"],
    "elbow_joint": ["elbow", "cubital", "carrying angle"],
    "wrist_hand": ["wrist", "hand", "carpal", "thenar", "hypothenar", "intrinsic"],
    "dermatomes": ["dermatome", "dermatomes", "sensation", "numbness", "sensory level"],
    "nerve_injuries": ["nerve injury", "palsy", "erb", "klumpke", "wrist drop", "claw", "saturday night"],
    "upper_limb_muscles": ["muscle", "biceps", "triceps", "deltoid", "brachialis", "innervation"],
}



# Broad diagnostic sample: one representative question from each topic group.
# Used when no specific topic is mentioned so the diagnostic covers the full curriculum.
_BROAD_DIAGNOSTIC = [
    _TOPIC_BANK_MAP["brachial_plexus"][0],      # plexus origin
    _TOPIC_BANK_MAP["rotator_cuff"][0],          # SITS muscles
    _TOPIC_BANK_MAP["peripheral_nerves"][2],     # median nerve (ape hand)
    _TOPIC_BANK_MAP["shoulder_joint"][0],        # glenohumeral
    _TOPIC_BANK_MAP["elbow_joint"][0],           # carrying angle
    _TOPIC_BANK_MAP["wrist_hand"][0],            # carpal bones
    _TOPIC_BANK_MAP["dermatomes"][0],            # C6/C8 landmarks
    _TOPIC_BANK_MAP["nerve_injuries"][0],        # Saturday night palsy
    _TOPIC_BANK_MAP["upper_limb_muscles"][1],    # biceps innervation
    _TOPIC_BANK_MAP["spinal_cord"][0],           # conus level
]


def get_diagnostic_order(study_focus: str, n: int = 4) -> list[int]:
    """Return bank indices for pre-assessment.

    - "topic:<key>" → all questions for that topic only (up to n)
    - no topic signal → broad sample across topic groups
    - keyword match → questions from matched topics first
    """
    focus = (study_focus or "").strip()

    # Explicit topic selection from onboarding menu
    if focus.startswith("topic:"):
        key = focus[len("topic:"):].strip()
        indices = _TOPIC_BANK_MAP.get(key, [])
        return indices[:n] if indices else _BROAD_DIAGNOSTIC[:n]

    focus_lower = focus.lower()

    # Score each topic by keyword matches
    topic_scores: dict[str, int] = {}
    for topic, kws in _TOPIC_KEYWORDS.items():
        topic_scores[topic] = sum(1 for k in kws if k in focus_lower)

    max_score = max(topic_scores.values(), default=0)

    # No topic signal → broad cross-topic sample
    if max_score == 0:
        return _BROAD_DIAGNOSTIC[:n]

    # Keyword match → all questions for the top-scoring topic(s)
    ordered_topics = sorted(topic_scores, key=lambda t: -topic_scores[t])
    seen: set[int] = set()
    result: list[int] = []
    for topic in ordered_topics:
        for idx in _TOPIC_BANK_MAP.get(topic, []):
            if idx not in seen:
                seen.add(idx)
                result.append(idx)
            if len(result) == n:
                return result

    for idx in _BROAD_DIAGNOSTIC:
        if idx not in seen:
            seen.add(idx)
            result.append(idx)
        if len(result) == n:
            return result

    return result[:n]


def generate_diagnostic_question(bank_idx: int) -> str:
    """Return the diagnostic question for a bank index."""
    if 0 <= bank_idx < len(_DIAGNOSTIC_BANK):
        return _DIAGNOSTIC_BANK[bank_idx]["question"]
    return ""


def get_diagnostic_answer_keywords(bank_idx: int) -> str:
    """Return a comma-separated hint of correct-answer keywords for a bank question."""
    if 0 <= bank_idx < len(_DIAGNOSTIC_BANK):
        return ", ".join(_DIAGNOSTIC_BANK[bank_idx].get("keywords", []))
    return ""


def _init_mastery_from_diagnostic(
    answer: str, bank_idx: int, mastery: dict
) -> dict:
    """Score a diagnostic answer and initialise mastery for its concept."""
    if bank_idx < 0 or bank_idx >= len(_DIAGNOSTIC_BANK):
        return mastery
    entry = _DIAGNOSTIC_BANK[bank_idx]
    ans = answer.lower()
    keywords = entry["keywords"]
    score = sum(1 for k in keywords if k in ans) / max(len(keywords), 1)
    updated = dict(mastery)
    updated[entry["concept"]] = 0.5 if score > 0.5 else 0.1
    return updated


# ── Main node ─────────────────────────────────────────────────────────────────

def pedagogy_agent(state: TutoringState) -> dict:
    """
    Evaluate student response, update mastery, identify weak topics.
    """
    phase = state["phase"]
    topic = state.get("current_topic", "")
    mastery = dict(state.get("mastery_scores", {}))
    internal = state.get("_internal_analysis")
    student_msg = state["student_message"]
    turn = state["turn_count"]
    diagnostic_complete = state.get("diagnostic_complete", False)
    consecutive_correct = state.get("consecutive_correct", 0)
    consecutive_incorrect = state.get("consecutive_incorrect", 0)

    G = _load_concept_graph()

    # ── Rapport: handle diagnostic probe ──────────────────────────────────
    if phase == "rapport":
        # Topic selection now happens via AskActionMessage in on_chat_start (not a graph turn).
        # turn 1 = Q0 answer, turn 2 = Q1 answer, etc.
        display_idx = turn - 1
        sf = state.get("study_focus") or ""
        n_max = _cfg["session"]["diagnostic_questions"]
        order = get_diagnostic_order(sf, n=n_max)
        n_diag = len(order)

        if 0 <= display_idx < n_diag:
            actual_q_id = order[min(display_idx, len(order) - 1)]
            mastery = _init_mastery_from_diagnostic(student_msg, actual_q_id, mastery)

        complete = turn >= n_diag
        return {
            "mastery_scores": mastery,
            "diagnostic_complete": complete,
        }

    # ── Tutoring / Assessment: evaluate and update ─────────────────────────
    # Skip evaluation for synthetic trigger messages (empty or tutoring start prompts)
    if not student_msg or student_msg.startswith("Let's work on"):
        return {"mastery_scores": mastery, "consecutive_correct": consecutive_correct,
                "consecutive_incorrect": consecutive_incorrect}

    if not topic:
        # Try to extract topic from conversation context
        topic = _extract_topic_from_message(student_msg)

    is_correct, _ = _evaluate_response(student_msg, internal)

    if topic:
        current_mastery = mastery.get(topic, _M["default_prior"])
        mastery[topic] = _update_mastery(current_mastery, is_correct)

    if is_correct:
        consecutive_correct += 1
        consecutive_incorrect = 0
    else:
        consecutive_incorrect += 1
        consecutive_correct = 0

    coverage = _compute_coverage(mastery, G)

    # Find weak topics (for proactive revisit after 8 min)
    weak = [
        c for c, m in mastery.items()
        if m < _M["weak_threshold"]
    ]

    # Trace prerequisite gaps if student is struggling
    prereq_gaps = []
    if consecutive_incorrect >= _cfg["mastery"]["consecutive_incorrect_for_hint"] and topic:
        prereq_gaps = _find_prerequisite_gaps(topic, mastery, G)

    # Append to mistake log when student answers incorrectly
    new_mistakes = []
    if not is_correct and topic:
        misconception = (internal or {}).get("student_misconception", "")
        new_mistakes = [{
            "topic": topic,
            "misconception": misconception,
            "turn": turn,
            "elapsed_sec": round(state.get("elapsed_seconds", 0.0), 1),
        }]

    # ── Topic cycling: once current topic is mastered, move to next weakest ──
    next_topic = topic
    if topic and mastery.get(topic, 0) >= _cfg["pcr"]["threshold_high"]:
        # Find weakest concept not yet mastered
        candidates = [
            (c, m) for c, m in mastery.items()
            if m < _cfg["pcr"]["threshold_high"] and c != topic
        ]
        if candidates:
            next_topic = min(candidates, key=lambda x: x[1])[0]

    return {
        "mastery_scores": mastery,
        "consecutive_correct": consecutive_correct,
        "consecutive_incorrect": consecutive_incorrect,
        "coverage_ratio": coverage,
        "weak_topics": weak + prereq_gaps,
        "mistake_log": new_mistakes,   # Annotated[list, operator.add] — appends
        # Clear revisit_scheduled after one use so it doesn't loop indefinitely
        "revisit_scheduled": False,
        # Cycle to next weakest topic once current is mastered
        "current_topic": next_topic,
    }


def _extract_topic_from_message(msg: str) -> str:
    """Heuristic: match message to known concept IDs."""
    msg_lower = msg.lower()
    topic_keywords = {
        "brachial_plexus.origin": ["brachial plexus", "c5", "c6", "t1"],
        "brachial_plexus.trunks": ["trunk", "upper trunk", "lower trunk"],
        "brachial_plexus.cords": ["cord", "posterior cord", "lateral cord"],
        "peripheral_nerves.axillary": ["axillary nerve", "deltoid"],
        "peripheral_nerves.radial": ["radial nerve", "wrist drop"],
        "peripheral_nerves.median": ["median nerve", "carpal tunnel"],
        "peripheral_nerves.ulnar": ["ulnar nerve", "claw hand"],
        "rotator_cuff.muscles": ["rotator cuff", "supraspinatus", "infraspinatus"],
        "rotator_cuff.supraspinatus": ["supraspinatus", "abduction"],
    }
    for concept, keywords in topic_keywords.items():
        if any(kw in msg_lower for kw in keywords):
            return concept
    return ""


