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

    client = _get_client()
    prompt = (
        f"Gold answer: {correct_answer}\n"
        f"Student's response: {student_answer}\n\n"
        "Is the student's response substantially correct? "
        "Reply with 'correct' or 'incorrect' followed by one sentence of reason."
    )
    resp = client.chat.completions.create(
        model=_cfg["llm"]["model"],
        messages=[{"role": "user", "content": prompt}],
        max_tokens=60,
        temperature=0,
    )
    text = resp.choices[0].message.content.strip().lower()
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
    # rotator_cuff
    {"question": "Name the four rotator cuff muscles.",
     "concept": "rotator_cuff.muscles", "topic": "rotator_cuff",
     "keywords": ["supraspinatus", "infraspinatus", "teres minor", "subscapularis"]},
    {"question": "What is the function of the supraspinatus and which nerve innervates it?",
     "concept": "rotator_cuff.supraspinatus", "topic": "rotator_cuff",
     "keywords": ["abduction", "suprascapular"]},
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
    # shoulder_joint
    {"question": "What type of joint is the glenohumeral joint, and what structures provide its stability?",
     "concept": "shoulder_joint.glenohumeral", "topic": "shoulder_joint",
     "keywords": ["ball and socket", "labrum", "rotator cuff", "glenohumeral ligament"]},
    {"question": "Which bones articulate at the acromioclavicular joint and why is it clinically important?",
     "concept": "shoulder_joint.ac_joint", "topic": "shoulder_joint",
     "keywords": ["acromion", "clavicle", "separation", "fall"]},
    # elbow_joint
    {"question": "What is the carrying angle of the elbow and which condition alters it?",
     "concept": "elbow_joint.anatomy", "topic": "elbow_joint",
     "keywords": ["valgus", "cubitus valgus", "cubitus varus", "degrees"]},
    {"question": "Where does the ulnar nerve pass at the elbow, and what symptoms result from compression there?",
     "concept": "elbow_joint.cubital_tunnel", "topic": "elbow_joint",
     "keywords": ["cubital tunnel", "medial epicondyle", "ring", "little finger", "tingling"]},
    # wrist_hand
    {"question": "Name the two rows of carpal bones in order from radial to ulnar.",
     "concept": "wrist_hand.carpals", "topic": "wrist_hand",
     "keywords": ["scaphoid", "lunate", "triquetrum", "pisiform", "trapezium", "trapezoid", "capitate", "hamate"]},
    {"question": "What muscles form the thenar eminence and what nerve innervates them?",
     "concept": "wrist_hand.intrinsic_muscles", "topic": "wrist_hand",
     "keywords": ["abductor pollicis", "flexor pollicis brevis", "opponens", "median"]},
    # dermatomes
    {"question": "Which dermatome supplies the thumb, and which supplies the little finger?",
     "concept": "dermatomes.upper_limb", "topic": "dermatomes",
     "keywords": ["c6", "c8", "thumb", "little finger"]},
    {"question": "A patient reports numbness over the lateral forearm — which spinal level is involved?",
     "concept": "dermatomes.clinical", "topic": "dermatomes",
     "keywords": ["c6", "lateral", "musculocutaneous"]},
    # nerve_injuries
    {"question": "What is Saturday night palsy and which nerve is involved?",
     "concept": "nerve_injuries.radial", "topic": "nerve_injuries",
     "keywords": ["radial", "spiral groove", "wrist drop", "compression"]},
    {"question": "Describe Erb's palsy — which roots are injured and what is the classic limb posture?",
     "concept": "nerve_injuries.brachial_plexus", "topic": "nerve_injuries",
     "keywords": ["c5", "c6", "waiter's tip", "adduction", "internal rotation"]},
    # upper_limb_muscles
    {"question": "What is the innervation and primary action of the biceps brachii?",
     "concept": "upper_limb_muscles.elbow_flexors", "topic": "upper_limb_muscles",
     "keywords": ["musculocutaneous", "c5", "c6", "flexion", "supination"]},
    {"question": "Which nerve innervates the triceps and at what spinal level?",
     "concept": "upper_limb_muscles.elbow_extensors", "topic": "upper_limb_muscles",
     "keywords": ["radial", "c7", "extension"]},
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
    """Return n bank indices prioritised by topics mentioned in study_focus.
    Falls back to a broad cross-topic sample when no topic is detected.
    """
    focus = (study_focus or "").lower()

    # Score each topic by keyword matches
    topic_scores: dict[str, int] = {}
    for topic, kws in _TOPIC_KEYWORDS.items():
        topic_scores[topic] = sum(1 for k in kws if k in focus)

    max_score = max(topic_scores.values(), default=0)

    # No topic signal — return a spread across all topic groups
    if max_score == 0:
        return _BROAD_DIAGNOSTIC[:n]

    # Build ordered list: highest-score topics first
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

    # Fill remaining slots from the broad sample (preserves topic diversity)
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
        # turn 1 = warmup exchange (no anatomy answer), turn 2+ = diagnostic answers
        # display_idx is 0-based position in the diagnostic sequence (0 = first Q shown)
        display_idx = turn - 2
        n_diag = _cfg["session"]["diagnostic_questions"]
        if 0 <= display_idx < n_diag:
            order = get_diagnostic_order(state.get("study_focus") or "", n=n_diag)
            actual_q_id = order[min(display_idx, len(order) - 1)]
            mastery = _init_mastery_from_diagnostic(student_msg, actual_q_id, mastery)

        complete = (turn - 1) >= _cfg["session"]["diagnostic_questions"]
        return {
            "mastery_scores": mastery,
            "diagnostic_complete": complete,
        }

    # ── Tutoring / Assessment: evaluate and update ─────────────────────────
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


