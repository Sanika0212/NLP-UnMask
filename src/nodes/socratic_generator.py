"""
Socratic Generator — structured output with knowledge masking.

The model COMPUTES the correct answer (enabling a well-aimed question)
but the output schema provides no field to reveal it.
Only visible_response.socratic_question + encouragement reach the student.
"""
from __future__ import annotations

import os
from typing import Literal, Optional

import yaml
from openai import OpenAI
from pydantic import BaseModel

from src.state import TutoringState, Phase

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
    """Only this is rendered in Chainlit."""
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
You are UnMask, a friendly Socratic tutor helping OT students prepare for the NBCOT exam.
You are running a short diagnostic. The next diagnostic question will be shown automatically — \
you MUST NOT ask any question yourself. Do NOT end your response with "?".
React to the student's answer in 1-2 sentences ONLY: briefly acknowledge correct/incorrect \
(without revealing the full answer) and offer brief encouragement. Then stop completely.
Examples of good responses:
- "Exactly right — C5 to T1 are the five roots. Nice start!"
- "Close! You've got the right range in mind. Keep going."
- "Not quite, but good attempt — we'll revisit that."
Do not ask follow-up questions. Do not say 'which topic' or 'what would you like to explore'."""

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
CONVERSATION: {history}
TURN: {turn} | CONSECUTIVE INCORRECT: {consecutive_incorrect}
STUDY FOCUS: {study_focus} — ALL questions MUST stay within this topic area. Do not stray to unrelated anatomy concepts. If study_focus starts with "topic:", focus exclusively on that topic's clinical syndromes, mechanisms, and signs. | LEARNING MODE: {learning_mode} — if "visual", use spatial anatomical descriptions and reference diagram layouts; if "text", use clear prose explanations.

TONE GUIDE — encouragement must be exactly ONE sentence, original, not canned:
- consecutive_incorrect = 0 → specific praise e.g. "Nice — you've got the root level right!"
- consecutive_incorrect = 1 → warm redirect e.g. "Not quite, but think about the movement involved."
- consecutive_incorrect = 2 → empathetic e.g. "This one trips a lot of people — let's try a fresh angle."
- consecutive_incorrect >= 3 → step further back e.g. "Let's zoom out — what does this muscle attach to?"
CRITICAL: Write ONE sentence only for encouragement. No joining two phrases with a dash or period.
NEVER say "great job" / "well done" / "you're doing great" when consecutive_incorrect > 0.
{revisit_block}"""

_REVEAL_SYSTEM = """\
You are UnMask, a study partner for OT anatomy (NBCOT prep).
The student has been stuck on this concept or asked you directly — now be a real partner and just tell them.

CONTEXT (textbook source of truth):
{context}

WHAT TO DO (in visible_response):
- encouragement: Acknowledge their effort honestly in ONE natural sentence. If they asked directly, say something like "No problem — let me just walk you through it." NOT fake praise.
- socratic_question: Give the correct answer clearly in 1-2 sentences (you can name it — they need to know it now). Then briefly explain WHY (mechanism/clinical link). End with ONE simple check question like "Does that click now?" or "Want to try a quick follow-up?"

In internal_analysis, still compute the correct answer and misconception as usual.
STUDY FOCUS: {study_focus} | CONSECUTIVE INCORRECT: {consecutive_incorrect}"""

_ASSESSMENT_SYSTEM = """\
You are UnMask in assessment mode.
Present ONE clinical scenario grounded in the textbook chunks.
Do NOT reveal the answer — ask the student to explain their reasoning.
The scenario must test concepts with low mastery scores.

CONTEXT CHUNKS:
{context}

MASTERY SCORES: {mastery_json}
"""

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
        model="gpt-4o",
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

    client = _get_client()
    prompt = _SUMMARY_PROMPT.format(
        mastery_json=json.dumps(
            {k: round(v, 2) for k, v in mastery.items() if k in topics_visited},
            indent=2,
        ),
        mistakes_json=json.dumps(mistake_log, indent=2) if mistake_log else "[]",
        topics_covered=", ".join(topics_visited) or "none",
        duration_min=elapsed / 60,
        total_turns=turn,
    )

    resp = client.beta.chat.completions.parse(
        model=os.getenv("OPENAI_MODEL", _cfg["llm"]["model"]),
        messages=[{"role": "user", "content": prompt}],
        response_format=SessionSummary,
        temperature=0.3,
    )
    summary: SessionSummary = resp.choices[0].message.parsed

    # ── Format as readable markdown ────────────────────────────────────────
    lines = ["## 📋 Session Report\n"]
    lines.append(f"{summary.overall_assessment}\n")

    # Per-topic report card
    lines.append("### Topic Breakdown\n")
    status_icon = {"mastered": "✅", "progressing": "🟡", "needs_review": "❌"}
    for tr in summary.topic_reports:
        icon = status_icon.get(tr.status, "⬜")
        concept_readable = tr.concept.replace("_", " ").replace(".", " › ")
        lines.append(
            f"{icon} **{concept_readable}** — mastery {tr.mastery_score:.0%}\n"
            f"> {tr.honest_feedback}\n"
        )

    # Mistake highlights
    if summary.mistake_highlights:
        lines.append("### ⚠️ Misconceptions to Address\n")
        for m in summary.mistake_highlights:
            lines.append(f"- {m}")
        lines.append("")

    # Study recommendations
    if summary.study_recommendations:
        lines.append("### 📚 Study Recommendations\n")
        for tip in summary.study_recommendations:
            lines.append(f"- {tip}")
        lines.append("")

    # Resources
    if summary.resources:
        lines.append("### 📖 Study Resources\n")
        for r in summary.resources:
            lines.append(f"- {r}")
        lines.append("")

    # Flashcards and diagrams are sent as separate rich messages by app.py
    # (_send_followup_resources) — omit them here to avoid duplication.

    # Next session questions
    if summary.next_session_questions:
        lines.append("### 🔁 Practice Questions for Next Session\n")
        for i, q in enumerate(summary.next_session_questions, 1):
            lines.append(f"**{i}.** {q}")
        lines.append("")

    # Closing reflection
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
        # Strip any question the model generated — the next diagnostic Q is appended by app.py
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
                history=recent_history,
                turn=turn,
                consecutive_incorrect=consecutive_incorrect,
                revisit_block=revisit_block,
                study_focus=state.get("study_focus") or "general",
                learning_mode=state.get("learning_mode") or "text",
            )

        # Build visual hint separately — shown as a UI card by app.py, NOT in the LLM response
        visual_hint = None
        # visual mode: hint after 1 wrong (spatial learners need diagram sooner); text mode: 2
        visual_threshold = 1 if state.get("learning_mode") == "visual" else 2
        if consecutive_incorrect >= visual_threshold:
            # Prefer figure chunks that match the current topic
            fig_chunks = [
                c for c in chunks
                if c.get("chunk_type") in ("figure", "figure_description")
                and topic and c.get("concept", "").startswith(topic.split(".")[0])
            ]
            # Fall back to any figure chunk, then to the most relevant context chunk
            if not fig_chunks:
                fig_chunks = [c for c in chunks if c.get("chunk_type") in ("figure", "figure_description")]
            if fig_chunks:
                fc = fig_chunks[0]
                # Always use state topic for image lookup — not the retrieved chunk's concept,
                # which may be from a different topic if retrieval drifted
                visual_hint = f"__concept__:{topic or fc.get('concept', '')}\n{fc['text']}"
            else:
                # Prefer chunks that actually match the current topic
                ctx_chunks = [
                    c for c in chunks
                    if not c.get("is_answer_chunk")
                    and topic and c.get("concept", "").startswith(topic.split(".")[0])
                ]
                if not ctx_chunks:
                    ctx_chunks = [c for c in chunks if not c.get("is_answer_chunk")]
                if ctx_chunks:
                    best = ctx_chunks[0]
                    visual_hint = f"__concept__:{topic or best.get('concept', '')}\n{best['text'][:400]}"
    elif phase == "assessment":
        import json
        system = _ASSESSMENT_SYSTEM.format(
            context=context_text,
            mastery_json=json.dumps(mastery, indent=2),
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

    for attempt in range(2):
        for api_attempt in range(3):
            try:
                resp = client.beta.chat.completions.parse(
                    model=os.getenv("OPENAI_MODEL", _cfg["llm"]["model"]),
                    temperature=_cfg["llm"]["temperature"] if attempt == 0 else 0,
                    messages=messages,
                    response_format=SocraticOutput,
                )
                break  # success
            except Exception as e:
                if api_attempt == 2:
                    raise
                time.sleep(2 ** api_attempt)  # exponential backoff: 1s, 2s, 4s
        output: SocraticOutput = resp.choices[0].message.parsed
        visible = output.visible_response
        candidate = visible.socratic_question
        if visible.encouragement:
            candidate = f"{visible.encouragement} {candidate}"

        internal_analysis = output.internal_analysis
        correct_answer = internal_analysis.correct_answer if internal_analysis else ""

        # Leak guard: check if response contains ≥3 words from the correct answer
        if correct_answer and _response_leaks_answer(candidate, correct_answer):
            if attempt == 0:
                # Inject explicit instruction and retry
                messages = [
                    {"role": "system", "content": system + "\n\nCRITICAL: Your previous response was too revealing. Do NOT mention specific anatomical names or values from the answer. Ask only a broad, open-ended guiding question."},
                    *history[-10:],
                    {"role": "user", "content": user_msg},
                ]
                continue
        response_text = candidate
        break  # accept on second attempt regardless

    response_text = _deduplicate_sentences(response_text)  # remove adjacent duplicates

    # ── Assessment: generate explicit feedback on student's clinical answer ──
    assessment_feedback = None
    if phase == "assessment" and turn > 0:
        # Find the scenario from history (the last assistant message before this user turn)
        scenario = next(
            (m["content"] for m in reversed(history) if m["role"] == "assistant"),
            "(clinical scenario)",
        )
        try:
            assessment_feedback = _generate_assessment_feedback(state, scenario, user_msg)
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
