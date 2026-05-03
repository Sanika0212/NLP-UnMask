"""
Socratic Generator — structured output with knowledge masking.

The model COMPUTES the correct answer (enabling a well-aimed question)
but the output schema provides no field to reveal it.
Only visible_response.socratic_question + encouragement reach the student.
"""
from __future__ import annotations

import os
import queue
import threading
from typing import Literal, Optional

import yaml
from openai import OpenAI
from pydantic import BaseModel

from src.state import TutoringState, Phase

# ── Per-session streaming token queues ───────────────────────────────────────
# api.py registers a queue before calling graph.invoke; socratic_generator
# puts tokens in it; api.py drains the queue and yields SSE events.
# Sentinel None marks end-of-stream.

_token_queues: dict[str, queue.Queue] = {}
_token_queues_lock = threading.Lock()


def register_token_queue(session_id: str) -> queue.Queue:
    q: queue.Queue = queue.Queue()
    with _token_queues_lock:
        _token_queues[session_id] = q
    return q


def unregister_token_queue(session_id: str) -> None:
    with _token_queues_lock:
        _token_queues.pop(session_id, None)


def _get_token_queue(session_id: str) -> Optional[queue.Queue]:
    with _token_queues_lock:
        return _token_queues.get(session_id)

with open("config.yaml") as f:
    _cfg = yaml.safe_load(f)


# ── Structured output schema (knowledge masking via schema) ───────────────────

class InternalAnalysis(BaseModel):
    """Stripped by app layer — never shown to student."""
    correct_answer: str
    student_misconception: str
    planned_hint_sequence: list[str]
    relevant_textbook_section: str


class VisibleResponse(BaseModel):
    """Only this is sent to the frontend via SSE."""
    socratic_question: str
    encouragement: str
    """Honest, calibrated feedback.
    - If student is struggling (consecutive_incorrect > 0): acknowledge the difficulty
      directly ('That part is tricky' / 'Let\'s think about this differently').
      Do NOT say 'great job', 'well done', or 'you\'re doing great' when they are wrong.
    - If student answered correctly: genuine specific praise.
    - If turn 1 (no answer yet): neutral welcome only."""


class SocraticOutput(BaseModel):
    internal_analysis: InternalAnalysis
    visible_response: VisibleResponse


# ── Session summary schema ────────────────────────────────────────────────────

class TopicReport(BaseModel):
    concept: str
    """The concept ID, e.g. 'peripheral_nerves.radial'"""
    mastery_score: float
    """Final mastery in [0, 1]"""
    status: Literal["mastered", "progressing", "needs_review"]
    """mastered = score >= 0.7, progressing = 0.4-0.7, needs_review = < 0.4"""
    honest_feedback: str
    """One honest sentence about the student's performance on this concept.
    Be specific: reference what they got right or wrong. No hollow praise."""

class Flashcard(BaseModel):
    concept: str
    """The concept ID, e.g. 'peripheral_nerves.radial'"""
    front: str
    """Question side of the flashcard — clinical or applied, max 1 sentence, ends with '?'."""
    back: str
    """Answer side — concise, factual, 1-2 sentences max."""


class YouTubeResource(BaseModel):
    """Curated YouTube reference for weak topics."""
    concept: str
    """The concept this video addresses, e.g. 'peripheral_nerves.radial'"""
    title: str
    """Exact title of the YouTube video or channel"""
    creator: str
    """Creator/channel name (e.g. 'Osmosis', 'Khan Academy', 'Netter Anatomy')"""
    search_query: str
    """Suggested search query to find this video on YouTube, e.g. 'Osmosis median nerve anatomy'"""
    description: str
    """Why this video helps — what concept it covers clearly (1 sentence)"""


class SessionSummary(BaseModel):
    overall_assessment: str
    """2-3 sentences summarising the session honestly. Name what went well AND
    what needs work. Do not sugarcoat weak performance."""
    topic_reports: list[TopicReport]
    """One entry per concept that was covered, ordered weakest-first."""
    mistake_highlights: list[str]
    """Up to 3 specific misconceptions the student showed, phrased clearly
    (e.g. 'Confused the axillary nerve with the radial nerve at the deltoid').
    Empty list if no mistakes were logged."""
    study_recommendations: list[str]
    """2-3 concrete, actionable study tips based on weak topics."""
    resources: list[str]
    """3-4 specific study resources for the weakest topics. Mix formats:
    - OpenStax A&P 2e chapter references (e.g. 'OpenStax A&P 2e Ch 13.4 — Brachial Plexus')
    - Netter's / Gray's atlas plates for visual anatomy (e.g. 'Netter Plate 462 — Brachial Plexus Overview')
    - KenHub or Visible Body search query (e.g. 'KenHub: search "median nerve course upper limb"')
    - NBCOT-specific practice (e.g. 'NBCOT Prep: clinical scenarios for peripheral nerve injuries')
    Reference real OpenStax 2e chapters (Ch 11=muscle, Ch 13=spinal/plexuses, Ch 14=PNS, Ch 15=ANS, Ch 16=sensorimotor)."""
    youtube_resources: list[YouTubeResource]
    """2-4 curated YouTube videos for the weakest topics. Each includes title, creator, search query, and why it helps.
    Prioritize reputable anatomy channels: Osmosis, Khan Academy, Netter Anatomy, AnatomyZone, Armando Hasudungan.
    Focus on videos covering exact weak topics from this session."""
    diagram_suggestions: list[str]
    """2-3 specific anatomical diagrams to study, each describing WHAT the diagram shows and WHY it helps.
    Format: 'Netter Plate XXX — [Title]: shows [key structures] — useful for understanding [concept]'
    OR: 'Draw from memory: [specific diagram e.g. brachial plexus tree C5-T1 showing roots/trunks/divisions/cords/branches]'"""
    flashcards: list[Flashcard]
    """4-6 flashcards covering the weakest topics from this session.
    Mix conceptual (what is X?) and clinical (patient presents with Y, which nerve is damaged?) questions."""
    next_session_questions: list[str]
    """3 follow-up practice questions for the next session, ordered foundational→applied.
    Focus on the weakest topics and any prerequisite gaps identified.
    Each must end with '?'."""
    closing_reflection: str
    """One Socratic question for the student to think about before next session.
    Must end with '?'."""


class AssessmentFeedback(BaseModel):
    """Explicit evaluation of student's clinical scenario response."""
    score: Literal["excellent", "good", "partial", "needs_work"]
    """Overall quality of the student's clinical reasoning."""
    what_was_correct: str
    """1-2 sentences on what the student correctly identified."""
    what_was_missing: str
    """1-2 sentences on key gaps or errors in their reasoning."""
    clinical_significance: str
    """1 sentence explaining why these gaps matter for OT practice."""
    follow_up_question: str
    """One Socratic question to deepen understanding of the gap. Must end with '?'."""


# ── System prompts ────────────────────────────────────────────────────────────

_RAPPORT_WARMUP_SYSTEM = """\
You are UnMask, a friendly Socratic tutor for OT students preparing for the NBCOT exam.
This is your FIRST exchange with the student — they just replied to your greeting.
Respond warmly and casually in 1-2 sentences ONLY:
- Acknowledge what they said naturally (like a real person, not a bot)
- Keep it brief and genuine — e.g. "Love the energy!" or "Totally get it, we'll keep it focused."
Do NOT add any transition like "let's get started" — the first question will appear automatically below your reply.
Do NOT ask any anatomy question. Do NOT end with "?". No more than 2 sentences."""

_RAPPORT_SYSTEM = """\
You are UnMask, a Socratic tutor helping OT students prepare for the NBCOT exam.
You are running a short diagnostic. The next diagnostic question will be shown automatically — \
you MUST NOT ask any question yourself. Do NOT end your response with "?".
React to the student's answer in 1 sentence ONLY. Then stop completely.

TONE RULES (apply strictly):
- If student says "idk", "don't know", "no idea", "not sure", or any phrase under 8 words with no anatomy → respond ONLY with a neutral one-liner e.g. "That one's tricky — we'll build it up." NEVER say "no worries", "that's okay", "don't stress", or anything that sounds like consolation.
- If correct → brief specific praise e.g. "Exactly — C5 to T1 are the five roots."
- If partially correct or wrong → neutral acknowledgment e.g. "Not quite — we'll come back to that."
Do not ask follow-up questions. Do not say 'which topic' or 'what would you like to explore'.
Do not give study tips or motivational speeches."""

_TUTORING_SYSTEM = """\
You are UnMask, a warm and encouraging Socratic tutor for OT anatomy (NBCOT prep).
Talk like a real human tutor — natural, conversational, not stiff or robotic.

HARD RULES:
1. You KNOW the correct answer (internal_analysis.correct_answer) — never state it aloud.
2. socratic_question MUST end with "?" — ask about a SYMPTOM, PRESENTATION, or SCENARIO. NEVER describe the function/role of the correct nerve or muscle in the question itself (that gives away the answer).
3. Keep responses SHORT: encouragement = 1 natural sentence, question = 1 sentence.
4. No bullet points, no headers, no "Rule 1:" style text in your response.
5. Stay strictly on the student's selected study topic ({study_focus}). Do not introduce new anatomy regions not related to this topic.
6. BAD question example: "Which nerve is associated with wrist drop due to its role in extending the wrist?" — this reveals the answer. GOOD: "A patient wakes up unable to lift their wrist after sleeping with their arm over a chair — what do you think happened?"
7. CITATION RULE: Your socratic_question MUST be grounded ONLY in the CONTEXT CHUNKS below. Do not use anatomy knowledge from outside those chunks. If a fact is not in the context, do not state it.

CONTEXT (textbook source of truth — use ONLY this):
{context}

STUDENT MASTERY: {mastery:.0%} on current topic | RETRIEVAL MODE: {mode} (answer chunks {answer_visibility}present)
LEARNING MODE: {learning_mode} — if "visual", reference spatial/structural relationships and diagram features in your question
TURN: {turn} | CONSECUTIVE INCORRECT: {consecutive_incorrect}
STUDY FOCUS: {study_focus} — ALL questions MUST stay within this topic area. Do not stray to unrelated anatomy concepts. If study_focus starts with "topic:", focus exclusively on that topic's clinical syndromes, mechanisms, and signs. | LEARNING MODE: {learning_mode} — if "visual", use spatial anatomical descriptions and reference diagram layouts; if "text", use clear prose explanations.

TONE GUIDE — encouragement must be exactly ONE sentence, original, not canned:
- If the student's message is "idk", "don't know", "no idea", "not sure", "oh", "ok", "hm", or any short non-answer (< 10 words with no anatomy content) → neutral pivot ONLY. VARY the phrasing every turn — do NOT repeat "No worries, let's build it up together." Use alternatives like: "That one catches people — let's approach it differently." / "Fair enough — let's try a clinical angle." / "Totally understandable — here's a starting point." / "Let's back up a bit." Never repeat the same opener twice in a session.
- consecutive_incorrect = 0 AND student gave a substantive correct answer → specific praise referencing what they got right e.g. "Exactly — C5 to T1 are the five roots."
- consecutive_incorrect = 1 → warm redirect e.g. "Not quite, but think about the movement involved."
- consecutive_incorrect = 2 → empathetic e.g. "This one trips a lot of people — let's try a fresh angle."
- consecutive_incorrect >= 3 → step further back e.g. "Let's zoom out — what does this muscle attach to?"
CRITICAL: Write ONE sentence only for encouragement. No joining two phrases with a dash or period.
NEVER say "great job" / "well done" / "you're doing great" / "you've got X right" when the student expressed uncertainty or said they don't know.
Evaluate ONLY the CURRENT student message — ignore how well they answered in previous turns.
CLASSIFY THE STUDENT'S MESSAGE before responding:
  A) SUBSTANTIVE ANATOMY ATTEMPT — contains anatomy terms, a diagnosis, a mechanism, a description of function, or a genuine attempt at an answer. → Evaluate it, give honest feedback, ask a follow-up that builds on it.
  B) ACKNOWLEDGMENT / REACTION — no anatomy content; just a social/emotional reaction (e.g. "oh", "ok", "neat", "interesting", "oh nice", "cool", "got it", "makes sense", "clean intro", "oh nice clean neat", "sure", "yeah", "that makes sense", "oh wow"). These could be 1 word or a short casual phrase. → Do NOT repeat your last question. Advance the scaffold with a completely new angle: different clinical scenario, a simpler sub-question, or a concrete clue.
  C) UNCERTAINTY — "idk", "no idea", "not sure", "still confused", etc. → Same as B: advance, don't repeat.
  If in doubt between B and C, treat it as B.
ANTI-REPETITION: Your socratic_question MUST be DIFFERENT from the last assistant message in the conversation history. If the student gave a B/C response, your question MUST use a different scenario and different wording. NEVER return the previous question verbatim or near-verbatim.
{revisit_block}"""

_REVEAL_SYSTEM = """\
You are UnMask, a study partner for OT anatomy (NBCOT prep).
The student has been stuck on this concept or asked you directly — now be a real partner and just tell them.

CONTEXT (textbook source of truth):
{context}

WHAT TO DO (in visible_response):
- encouragement: ONE natural sentence acknowledging their effort. e.g. "No problem — let me walk you through it." NOT fake praise.
- socratic_question: DIRECTLY EXPLAIN the answer. Name the nerve/muscle/structure explicitly. Explain the mechanism or clinical link in 2-3 sentences. DO NOT ask a new anatomy or clinical scenario question — this is an explanation, not a quiz. You may end with a soft check like "Does that make sense?" or "Does that click?" but NOT a new clinical scenario or anatomy question.

CRITICAL: The student asked for an explanation. Give it. Do NOT respond with another Socratic question about the concept.

In internal_analysis, still compute the correct answer and misconception as usual.
STUDY FOCUS: {study_focus} | CONSECUTIVE INCORRECT: {consecutive_incorrect}"""

_ASSESSMENT_SYSTEM = """\
You are UnMask in assessment mode. Present ONE clinical scenario grounded in the textbook chunks.
Do NOT reveal the answer — ask the student to explain their reasoning.
The scenario must test concepts with low mastery scores.

CONTEXT CHUNKS:
{context}

MASTERY SCORES: {mastery_json}
CONSECUTIVE INCORRECT / NO-ANSWER: {consecutive_incorrect}
STUDENT'S CURRENT MESSAGE: "{student_message}"

TONE RULES — apply to encouragement field ONLY (1 sentence max):
- If the student's current message is "idk", "don't know", "no idea", "not sure", "oh", "ok", "hm", or any short non-answer:
  → encouragement MUST be a neutral pivot. VARY phrasing — avoid repeating "No worries" or "let's build it up". Use e.g. "That one catches people.", "Let's try a different angle.", "Fair enough — here's a clue."
  → Do NOT say "you're on the right track", "great job", "you've got it", or any positive feedback.
  → socratic_question MUST provide a concrete leading clue or scaffold, not just repeat the question.
- consecutive_incorrect = 0 AND substantive correct answer → specific praise referencing what they got right.
- consecutive_incorrect = 1 → warm redirect e.g. "Not quite — think about the mechanism."
- consecutive_incorrect >= 2 → empathetic e.g. "This one's tricky — here's a starting point."
NEVER praise when the student expressed uncertainty or gave no real answer.
Evaluate ONLY the CURRENT student message, not previous turns."""

_ASSESSMENT_FEEDBACK_SYSTEM = """\
You are evaluating a student's response to a clinical scenario in an OT anatomy session.
Be honest and specific — do not soften weak responses.

CLINICAL SCENARIO PRESENTED: {scenario}
STUDENT RESPONSE: {student_response}
TEXTBOOK CONTEXT (ground truth): {context}

Generate an AssessmentFeedback with:
- score: excellent/good/partial/needs_work based on reasoning quality
- what_was_correct: what the student correctly identified (be specific)
- what_was_missing: key gaps or errors (be specific — name the concepts)
- clinical_significance: why these gaps matter in OT practice
- follow_up_question: one Socratic question to guide them toward the gap
"""

_WRAPUP_SYSTEM = """\
You are UnMask wrapping up a tutoring session.
Generate a brief, encouraging summary: what the student learned, which topics to review.
In socratic_question, ask one closing reflection question.
Keep internal_analysis brief (it is not shown to the student).

WEAK TOPICS: {weak_topics}
MASTERY SCORES: {mastery_json}
"""


# ── Client ────────────────────────────────────────────────────────────────────

_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.getenv("OPENAI_BASE_URL"),
            timeout=45.0,
        )
    return _client


def _use_local(phase: Phase) -> bool:
    """Route to Ollama for rapport/wrapup to save API budget."""
    return phase in _cfg["llm"].get("use_local_for", [])


def _call_ollama(system: str, user: str, history: list[dict] | None = None) -> str:
    """Call local Ollama as a plain text fallback (no structured output)."""
    import httpx
    import json
    messages = [{"role": "system", "content": system}]
    if history:
        messages.extend(history[-6:])
    messages.append({"role": "user", "content": user})
    r = httpx.post(
        "http://localhost:11434/api/chat",
        json={"model": _cfg["llm"]["local_model"], "messages": messages, "stream": False},
        timeout=30.0,
    )
    r.raise_for_status()
    return r.json()["message"]["content"]


def analyze_uploaded_image(image_path: str) -> str:
    """
    Analyze a student-uploaded anatomical image using GPT-4o Vision.
    Returns a Socratic question about the structure WITHOUT naming it directly.

    Args:
        image_path: Path to the uploaded image file

    Returns:
        A Socratic question string about the anatomical structure
    """
    import base64

    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    # Determine image media type from file extension
    ext = image_path.lower().split(".")[-1]
    media_type_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
    }
    media_type = media_type_map.get(ext, "image/jpeg")

    client = _get_client()
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", _cfg["llm"]["model"]),
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "You are an anatomy tutor. Identify the anatomical structure in this image. "
                            "Then ask ONE Socratic question about it WITHOUT naming the structure. "
                            "The question must end with '?'. Never give direct answers."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{image_data}",
                        },
                    },
                ],
            }
        ],
        max_tokens=200,
        temperature=0.7,
    )
    return resp.choices[0].message.content.strip()


# ── Session summary generator ─────────────────────────────────────────────────

_SUMMARY_PROMPT = """\
You are generating an end-of-session report for an OT anatomy tutoring session.
Be honest — do not soften poor performance. Students need accurate feedback to improve.

SESSION DATA:
Mastery scores (0=none, 1=full): {mastery_json}
Weak topics (mastery < 0.5, sorted worst-first): {weak_topics}
Mistake log (each wrong answer): {mistakes_json}
Topics covered: {topics_covered}
Session duration: {duration_min:.1f} minutes
Total turns: {total_turns}

Generate a SessionSummary with all fields:

topic_reports: one entry per covered concept, ordered weakest-first
overall_assessment: honest 2-3 sentence summary (name strengths AND weaknesses)
mistake_highlights: up to 3 specific misconceptions shown (empty list if none)
study_recommendations: 2-3 concrete actionable tips for the weak topics

resources: 3-4 specific study resources, mixing:
  - OpenStax A&P 2e chapters (Ch 11=muscle, Ch 13=spinal/plexuses, Ch 14=PNS, Ch 15=ANS, Ch 16=sensorimotor)
    Example: 'OpenStax A&P 2e Ch 13.4 — Brachial Plexus: covers roots C5-T1, trunk/division/cord/branch structure'
  - Netter's Atlas plates for visual anatomy
    Example: 'Netter Plate 462 — Brachial Plexus: color-coded nerve roots to terminal branches'
  - KenHub or Visible Body (free online)
    Example: 'KenHub: search "median nerve" — interactive 3D model with clinical notes'
  - NBCOT-specific practice
    Example: 'NBCOT Prep: clinical scenarios — peripheral nerve injury splinting'

youtube_resources: 2-4 curated YouTube videos for the weak topics listed above. ALWAYS include at least 2 videos —
  even if the session was brief, recommend videos for the topics listed in weak_topics.
  Prioritize the lowest-mastery concepts.
  Use real videos from reputable anatomy channels: Osmosis, Khan Academy, AnatomyZone, Armando Hasudungan,
  Netter Anatomy, Acland's Video Atlas, Ninja Nerd Science.
  Each resource must include:
    - concept: the weak topic concept ID from mastery_json (e.g., 'peripheral_nerves.radial')
    - title: exact video title as it appears on YouTube
    - creator: channel/creator name
    - search_query: specific YouTube search to find this exact video (e.g., 'Osmosis radial nerve anatomy palsy')
    - description: one sentence on what this video covers and why it addresses this student's specific gap
  Tailor to the student's actual mistakes — if mistake_log shows confusion about a specific concept, pick a
  video that directly addresses that misconception.

diagram_suggestions: 2-3 anatomical diagrams to study, each with what to look for:
  - Netter/Gray's plate reference with plate number AND what structures to trace
  - OR a "draw from memory" prompt (drawing forces active recall)
    Example: 'Draw from memory: brachial plexus tree — start at C5-T1 roots, add trunks (upper/middle/lower),
    divisions, cords (lateral/medial/posterior), then 5 terminal branches'

flashcards: 4-6 flashcards for the weakest topics, mixing:
  - Pure recall: "What nerve roots form the median nerve?" → "C6, C7, C8, T1 (medial + lateral cord)"
  - Clinical presentation: "Patient can't pinch thumb and index finger — which nerve?" → "Anterior interosseous branch of median nerve"
  - Functional: "What is the first sign of ulnar nerve compression at the elbow?" → "Tingling in ring and little fingers (C8/T1 distribution)"

next_session_questions: 3 practice questions, ordered foundational→applied, each ending '?'
closing_reflection: one Socratic question ending with '?' for next session"""


def _generate_session_summary(state: TutoringState) -> tuple[str, SessionSummary]:
    """Generate a structured session summary. Returns (markdown_text, SessionSummary)."""
    import json

    mastery = state.get("mastery_scores", {})
    mistake_log = state.get("mistake_log", [])
    elapsed = state.get("elapsed_seconds", 0.0)
    turn = state.get("turn_count", 0)

    # Only report on concepts that were actually visited
    topics_visited = set(mastery.keys()) | {m["topic"] for m in mistake_log}
    visited_mastery = {k: round(v, 2) for k, v in mastery.items() if k in topics_visited}

    # Weak topics sorted by mastery ascending — drive YouTube/resource recommendations
    weak_topics = sorted(
        [(k, v) for k, v in visited_mastery.items() if v < 0.5],
        key=lambda x: x[1]
    )

    # Fallback: if no mastery data, use the study focus topic so YouTube recs are always generated
    if not weak_topics:
        fallback = (state.get("study_focus") or "brachial_plexus").replace("topic:", "").strip()
        weak_topics = [(fallback, 0.0)]
        if fallback not in topics_visited:
            topics_visited.add(fallback)

    weak_topics_str = ", ".join(f"{k} ({v:.0%})" for k, v in weak_topics)

    client = _get_client()
    prompt = _SUMMARY_PROMPT.format(
        mastery_json=json.dumps(visited_mastery, indent=2),
        mistakes_json=json.dumps(mistake_log, indent=2) if mistake_log else "[]",
        topics_covered=", ".join(topics_visited) or "none",
        weak_topics=weak_topics_str,
        duration_min=elapsed / 60,
        total_turns=turn,
    )

    resp = client.beta.chat.completions.parse(
        model=os.getenv("OPENAI_MODEL", _cfg["llm"]["model"]),
        messages=[{"role": "user", "content": prompt}],
        response_format=SessionSummary,
        temperature=0.3,
    )
    summary: SessionSummary | None = resp.choices[0].message.parsed

    if summary is None:
        fallback = "## 📋 Session Report\n\nSession complete. Great work today — review your weak topics before next time."
        return fallback, SessionSummary(
            overall_assessment="Session complete.",
            topic_reports=[], mistake_highlights=[], study_recommendations=[],
            resources=[], youtube_resources=[], diagram_suggestions=[],
            flashcards=[], next_session_questions=[], closing_reflection="Keep reviewing!",
        )

    # ── Format as readable markdown ────────────────────────────────────────
    lines = ["## 📋 Session Report\n"]
    lines.append(f"{summary.overall_assessment or ''}\n")

    # Per-topic report card
    topic_reports = summary.topic_reports or []
    if topic_reports:
        lines.append("### Topic Breakdown\n")
        status_icon = {"mastered": "✅", "progressing": "🟡", "needs_review": "❌"}
        for tr in topic_reports:
            icon = status_icon.get(tr.status, "⬜")
            concept_readable = tr.concept.replace("_", " ").replace(".", " › ")
            lines.append(
                f"{icon} **{concept_readable}** — mastery {tr.mastery_score:.0%}\n"
                f"> {tr.honest_feedback}\n"
            )

    # Mistake highlights
    for m in (summary.mistake_highlights or []):
        if not lines[-1].startswith("### ⚠️"):
            lines.append("### ⚠️ Misconceptions to Address\n")
        lines.append(f"- {m}")
    if any("Misconceptions" in l for l in lines):
        lines.append("")

    # Study recommendations
    study_recs = summary.study_recommendations or []
    if study_recs:
        lines.append("### 📚 Study Recommendations\n")
        for tip in study_recs:
            lines.append(f"- {tip}")
        lines.append("")

    # Resources
    resources = summary.resources or []
    if resources:
        lines.append("### 📖 Study Resources\n")
        for r in resources:
            lines.append(f"- {r}")
        lines.append("")

    # YouTube recommendations
    youtube = summary.youtube_resources or []
    if youtube:
        lines.append("### 🎬 Recommended Videos\n")
        for yt in youtube:
            search_url = "https://www.youtube.com/results?search_query=" + (yt.search_query or "").replace(" ", "+")
            lines.append(
                f"- **{yt.title}** — *{yt.creator}*\n"
                f"  {yt.description}\n"
                f"  [Search on YouTube]({search_url})"
            )
        lines.append("")

    # Next session questions
    next_qs = summary.next_session_questions or []
    if next_qs:
        lines.append("### 🔁 Practice Questions for Next Session\n")
        for i, q in enumerate(next_qs, 1):
            lines.append(f"**{i}.** {q}")
        lines.append("")

    # Closing reflection
    if summary.closing_reflection:
        lines.append(f"---\n**Before next session:** {summary.closing_reflection}")

    return "\n".join(lines), summary


# ── Helpers ───────────────────────────────────────────────────────────────────

def _deduplicate_sentences(text: str) -> str:
    """Remove adjacent duplicate sentences from LLM response."""
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    deduped = []
    for s in sentences:
        if not deduped or s.strip() != deduped[-1].strip():
            deduped.append(s)
    return " ".join(deduped)


def _generate_assessment_feedback(state: TutoringState, scenario: str, student_response: str) -> str:
    """Generate explicit structured feedback on a student's assessment answer."""
    import json
    chunks = state.get("retrieved_chunks", [])
    context_text = "\n\n".join(
        f"[{c.get('chunk_type','ctx').upper()}] {c['text']}" for c in chunks
    ) or "(no context)"

    client = _get_client()
    prompt = _ASSESSMENT_FEEDBACK_SYSTEM.format(
        scenario=scenario,
        student_response=student_response,
        context=context_text,
    )
    resp = client.beta.chat.completions.parse(
        model=os.getenv("OPENAI_MODEL", _cfg["llm"]["model"]),
        messages=[{"role": "user", "content": prompt}],
        response_format=AssessmentFeedback,
        temperature=0.3,
    )
    fb: AssessmentFeedback = resp.choices[0].message.parsed

    score_icon = {"excellent": "✅", "good": "🟢", "partial": "🟡", "needs_work": "❌"}.get(fb.score, "⬜")
    lines = [
        f"### {score_icon} Assessment Feedback — {fb.score.replace('_', ' ').title()}\n",
        f"**What you got right:** {fb.what_was_correct}\n",
        f"**What was missing:** {fb.what_was_missing}\n",
        f"**Why it matters clinically:** {fb.clinical_significance}\n",
        f"\n**To think about:** {fb.follow_up_question}",
    ]
    return "\n".join(lines)


# ── Main node ─────────────────────────────────────────────────────────────────

def socratic_generator(state: TutoringState) -> dict:
    """
    Generate a Socratic response using structured output.
    Returns: generated_response (visible only), _internal_analysis (hidden).
    """
    phase = state["phase"]
    turn = state["turn_count"]
    mode = state.get("retrieval_mode", "context_only")
    chunks = state.get("retrieved_chunks", [])
    history = state.get("conversation_history", [])
    mastery = state.get("mastery_scores", {})
    topic = state.get("current_topic", "")
    _session_id = state.get("session_id", "")

    _max_turns = _cfg["llm"].get("max_history_turns", 8)

    context_text = "\n\n".join(
        f"[{c.get('chunk_type','context').upper()}] {c['text']}"
        for c in chunks
    ) or "(No context retrieved)"

    recent_history = "\n".join(
        f"{m['role'].capitalize()}: {m['content']}" for m in history[-_max_turns:]
    ) or "(Session start)"

    # ── Rapport: plain LLM (local or API) ──────────────────────────────────
    if phase == "rapport":
        user = state["student_message"] or "Hello"
        # Turn 0: casual warmup. Turn 1+: reacting to a diagnostic answer.
        if turn == 0:
            system_prompt = _RAPPORT_WARMUP_SYSTEM
            max_tok = 600
        else:
            # Get the actual diagnostic question and correct-answer keywords from state
            asked_q = state.get("current_diagnostic_question", "")
            answer_hint = state.get("current_diagnostic_answer_hint", "")
            system_prompt = _RAPPORT_SYSTEM + (
                f"\n\nQUESTION THE STUDENT JUST ANSWERED: \"{asked_q}\"\n"
                f"CORRECT ANSWER MUST INCLUDE THESE KEY TERMS: {answer_hint}\n"
                "Judge correctness strictly: if the student's answer does not include "
                "the key terms above, say 'Not quite' — do NOT say 'correct' or 'exactly right'. "
                "React specifically to their answer to THIS question. "
                "Do NOT reference other anatomy topics."
            )
            max_tok = 600
        text = None
        if _use_local(phase):
            try:
                text = _call_ollama(system_prompt, user, history=history)
            except Exception:
                pass
        if text is None:
            client = _get_client()
            resp = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", _cfg["llm"]["model"]),
                messages=[{"role": "system", "content": system_prompt}, *history[-6:], {"role": "user", "content": user}],
                max_tokens=max_tok,
                temperature=0.6,
            )
            text = (resp.choices[0].message.content or "").strip()
        # Strip any question the model generated — the next diagnostic Q is appended by api.py
        if text and "?" in text:
            import re
            sentences = re.split(r'(?<=[.!])\s+', text.strip())
            clean = [s for s in sentences if not s.strip().endswith("?")]
            text = " ".join(clean).strip() or text.split("?")[0].strip() + "."
        return {
            "generated_response": text,
            "_internal_analysis": None,
            "conversation_history": [
                {"role": "user", "content": user},
                {"role": "assistant", "content": text},
            ],
            "turn_count": turn + 1,
        }

    # ── Wrapup: structured SessionSummary via GPT-4o ────────────────────────
    if phase == "wrapup":
        formatted, summary_obj = _generate_session_summary(state)
        return {
            "generated_response": formatted,
            "_internal_analysis": summary_obj.model_dump(),
            "conversation_history": [
                {"role": "user", "content": "(session ended)"},
                {"role": "assistant", "content": formatted},
            ],
            "turn_count": turn + 1,
        }

    # ── Tutoring / Assessment: structured output via OpenAI ────────────────
    _GIVE_ANSWER_TRIGGERS = (
        "tell me the answer", "just tell me", "what is the answer", "what's the answer",
        "give me the answer", "i give up", "i have no idea", "no idea whatsoever",
        "i don't know at all", "i dont know at all", "i'm clueless", "im clueless",
        "i don't have time", "dont have time",
        "explain this to me", "can you explain", "explain this", "explain it to me",
        "explain in detail", "explain to me", "help me understand", "break it down",
        "walk me through", "just explain", "please explain",
    )
    consecutive_incorrect = state.get("consecutive_incorrect", 0)
    _student_msg_lower = (state.get("student_message") or "").lower()
    wants_answer = any(t in _student_msg_lower for t in _GIVE_ANSWER_TRIGGERS)
    break_socratic = wants_answer or consecutive_incorrect >= 4

    if phase == "tutoring":
        # Build revisit block when orchestrator has scheduled a proactive revisit
        revisit_block = ""
        if state.get("revisit_scheduled") and state.get("revisit_topic"):
            rt = state["revisit_topic"]
            rt_readable = rt.replace("_", " ").replace(".", " ")
            # Pull misconception from the most recent mistake on this topic
            prior_misconception = next(
                (m["misconception"] for m in reversed(state.get("mistake_log", []))
                 if m["topic"] == rt and m["misconception"]),
                None,
            )
            misconception_hint = (
                f" The student previously showed this misconception: \"{prior_misconception}\"."
                if prior_misconception else ""
            )
            revisit_block = (
                f"\nREVISIT MODE: The student previously struggled with '{rt_readable}'."
                f"{misconception_hint}"
                f" Naturally transition the conversation back to this topic with a"
                f" Socratic question that probes the same concept from a fresh angle."
            )

        if break_socratic:
            system = _REVEAL_SYSTEM.format(
                context=context_text,
                study_focus=state.get("study_focus") or "general",
                consecutive_incorrect=consecutive_incorrect,
            )
        else:
            system = _TUTORING_SYSTEM.format(
                context=context_text,
                mastery=mastery.get(topic, _cfg["mastery"]["default_prior"]),
                mode=mode,
                answer_visibility="NOT " if mode != "full_reveal" else "",
                turn=turn,
                consecutive_incorrect=consecutive_incorrect,
                revisit_block=revisit_block,
                study_focus=state.get("study_focus") or "general",
                learning_mode=state.get("learning_mode") or "text",
            )

        # Build visual hint — sent as a visual_hint SSE event by api.py, NOT in the LLM response
        visual_hint = None
        # visual mode: hint after 1 wrong; text mode: after 2 wrong
        visual_threshold = 1 if state.get("learning_mode") == "visual" else 2
        if consecutive_incorrect >= visual_threshold and topic:
            # Try to find a descriptive chunk for the hint text
            fig_chunks = [
                c for c in chunks
                if c.get("chunk_type") in ("figure", "figure_description")
                and c.get("concept", "").startswith(topic.split(".")[0])
            ]
            if not fig_chunks:
                fig_chunks = [c for c in chunks if c.get("chunk_type") in ("figure", "figure_description")]
            ctx_chunks = (
                fig_chunks or
                [c for c in chunks if not c.get("is_answer_chunk") and c.get("concept", "").startswith(topic.split(".")[0])] or
                [c for c in chunks if not c.get("is_answer_chunk")]
            )
            hint_text = ctx_chunks[0]["text"][:400] if ctx_chunks else "Study the diagram carefully, paying attention to the key structures."
            # Always anchor to current topic so anatomy_images.py can find the right image
            visual_hint = f"__concept__:{topic}\n{hint_text}"
    elif phase == "assessment":
        import json
        system = _ASSESSMENT_SYSTEM.format(
            context=context_text,
            mastery_json=json.dumps(mastery, indent=2),
            consecutive_incorrect=state.get("consecutive_incorrect", 0),
            student_message=(state.get("student_message") or "")[:120],
        )
    else:
        system = _RAPPORT_SYSTEM  # fallback

    user_msg = state["student_message"]

    client = _get_client()
    messages = [
        {"role": "system", "content": system},
        *history[-_max_turns:],
        {"role": "user", "content": user_msg},
    ]

    # ── Generate with post-generation leak guard (max 2 attempts) ──────────
    import time
    internal_analysis = None
    response_text = ""

    def _parse_attempt(msgs: list, temp: float) -> SocraticOutput:
        """Single API call with JSON prompt; streams tokens to queue if registered."""
        import re as _re, json as _json

        json_instruction = (
            "\n\nRespond ONLY with a JSON object matching this schema (no markdown, no prose):\n"
            '{"internal_analysis": {"correct_answer": "...", "student_misconception": "...", '
            '"planned_hint_sequence": [], "relevant_textbook_section": "..."}, '
            '"visible_response": {"encouragement": "...", "socratic_question": "...?"}}'
        )
        augmented = list(msgs)
        if augmented and augmented[0]["role"] == "system":
            augmented[0] = {**augmented[0], "content": augmented[0]["content"] + json_instruction}

        token_q = _get_token_queue(_session_id)

        if token_q is not None:
            # Streaming path: collect full response, then push visible text as one token.
            # Mercury 2 outputs ~1000 JSON tokens; character-level streaming of JSON keys
            # leaks syntax to the frontend. Instead we stream=True for latency benefit
            # (Mercury 2 starts generating immediately) and emit the visible question once done.
            stream_resp = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", _cfg["llm"]["model"]),
                temperature=temp,
                messages=augmented,
                max_tokens=1000,
                stream=True,
            )
            raw_parts: list[str] = []
            for chunk in stream_resp:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    raw_parts.append(delta)
            raw = "".join(raw_parts).strip()
            # Extract visible text from JSON, emit as single token
            try:
                clean = _re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=_re.DOTALL).strip()
                data = _json.loads(clean)
                vr = data.get("visible_response", {})
                enc = vr.get("encouragement", "")
                sq = vr.get("socratic_question", "")
                visible_text = f"{enc} {sq}".strip() if enc else sq
                if visible_text:
                    token_q.put(visible_text)
            except Exception:
                # Fallback: extract question via regex
                m = _re.search(r'"socratic_question"\s*:\s*"((?:[^"\\]|\\.)*)"', raw)
                if m:
                    token_q.put(m.group(1).replace('\\"', '"').replace('\\n', ' '))
            token_q.put(None)  # end sentinel
        else:
            resp = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", _cfg["llm"]["model"]),
                temperature=temp,
                messages=augmented,
                max_tokens=1000,
            )
            raw = (resp.choices[0].message.content or "").strip()

        # Try JSON parse → Pydantic
        try:
            clean = _re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=_re.DOTALL).strip()
            data = _json.loads(clean)
            return SocraticOutput(**data)
        except Exception as _e:
            import logging as _logging
            _logging.warning(f"[socratic_generator] JSON parse failed (attempt): {_e!r} | raw[:300]={raw[:300]!r}")

        # Fallback: regex-extract socratic_question, never return raw JSON
        m_fallback = _re.search(r'"socratic_question"\s*:\s*"((?:[^"\\]|\\.)*)"', raw)
        if m_fallback:
            question = m_fallback.group(1).replace('\\"', '"').replace('\\n', ' ')
        else:
            question = "Let's try a different angle — what movement or sensation would be affected if this structure were damaged?"
        return SocraticOutput(
            internal_analysis=InternalAnalysis(
                correct_answer="", student_misconception="",
                planned_hint_sequence=[], relevant_textbook_section="",
            ),
            visible_response=VisibleResponse(encouragement="", socratic_question=question),
        )

    for attempt in range(2):
        output: SocraticOutput = _parse_attempt(messages, _cfg["llm"]["temperature"] if attempt == 0 else 0)
        visible = output.visible_response
        candidate = visible.socratic_question
        if visible.encouragement:
            candidate = f"{visible.encouragement} {candidate}"

        internal_analysis = output.internal_analysis
        correct_answer = internal_analysis.correct_answer if internal_analysis else ""

        # Leak guard: check if response contains ≥3 words from the correct answer
        if correct_answer and _response_leaks_answer(candidate, correct_answer):
            if attempt == 0:
                messages = [
                    {"role": "system", "content": system + "\n\nCRITICAL: Your previous response was too revealing. Do NOT mention specific anatomical names or values from the answer. Ask only a broad, open-ended guiding question."},
                    *history[-10:],
                    {"role": "user", "content": user_msg},
                ]
                continue

        # Repetition guard: if the new question is nearly identical to the last assistant turn, retry
        last_assistant_q = next(
            (m["content"] for m in reversed(history) if m["role"] == "assistant"),
            "",
        )
        if last_assistant_q and attempt == 0:
            cand_words = set(visible.socratic_question.lower().split())
            prev_words = set(last_assistant_q.lower().split())
            overlap = len(cand_words & prev_words) / max(len(cand_words), 1)
            if overlap > 0.45:  # stricter — catch close paraphrases too
                messages = [
                    {"role": "system", "content": system + "\n\nCRITICAL: You JUST asked this question and must NOT repeat it: \"" + last_assistant_q[:200] + "\"\nThe student replied with a short acknowledgment. Move to a DIFFERENT approach: different clinical scenario, simpler sub-question, or direct clue. Even a single shared scenario detail counts as repeating."},
                    *history[-10:],
                    {"role": "user", "content": user_msg},
                ]
                continue

        response_text = candidate
        break  # accept on second attempt regardless

    response_text = _deduplicate_sentences(response_text)  # remove adjacent duplicates

    # ── Assessment: generate explicit feedback on student's clinical answer ──
    # Only generate feedback when the student is responding to an already-presented scenario.
    # Guard: last assistant message must look like a scenario (contains "?"), and the
    # student's message must be substantive (> 30 chars) — filters out "ok" / mode-change msgs.
    assessment_feedback = None
    if phase == "assessment" and turn > 0 and len(user_msg.strip()) > 30:
        last_assistant = next(
            (m["content"] for m in reversed(history) if m["role"] == "assistant"),
            "",
        )
        if last_assistant.strip().endswith("?"):
            try:
                assessment_feedback = _generate_assessment_feedback(state, last_assistant, user_msg)
            except Exception:
                pass  # non-fatal — degrade gracefully

    result = {
        "generated_response": response_text,
        "_internal_analysis": internal_analysis.model_dump() if internal_analysis else None,
        "assessment_feedback": assessment_feedback,
        "visual_hint": visual_hint if phase == "tutoring" else None,
        "conversation_history": [
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": response_text},
        ],
        "turn_count": turn + 1,
    }
    # After a reveal, reset streak counters so the next question starts fresh
    if phase == "tutoring" and break_socratic:
        result["consecutive_incorrect"] = 0
        result["consecutive_correct"] = 0
    return result


def _response_leaks_answer(response: str, correct_answer: str) -> bool:
    """
    Simple heuristic: if ≥4 significant words from the correct answer
    appear verbatim in the response, flag as a potential leak.
    """
    import re

    def significant_words(text: str) -> set[str]:
        stopwords = {"the", "a", "an", "is", "are", "of", "and", "to", "in", "for",
                     "it", "its", "that", "this", "by", "from", "with", "at", "be"}
        words = re.findall(r"[a-z0-9]+", text.lower())
        return {w for w in words if len(w) >= 4 and w not in stopwords}

    answer_words = significant_words(correct_answer)
    response_words = significant_words(response)
    overlap = answer_words & response_words
    return len(overlap) >= 4  # ≥4 significant words overlap signals a leak
