"""
UnMask — Chainlit entry point.

Run:
  chainlit run app.py

The backend panel (visible in Chainlit's "debug" sidebar) shows:
  - Retrieved chunks with PCR mode
  - Mastery scores per concept
  - Current phase and turn count
"""
from __future__ import annotations

import os
import sys
import time
import uuid

import chainlit as cl
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Validate required environment variables
_REQUIRED_ENV = ["OPENAI_API_KEY"]
_missing = [k for k in _REQUIRED_ENV if not os.environ.get(k)]
if _missing:
    print(f"ERROR: Missing required env vars: {_missing}", file=sys.stderr)
    sys.exit(1)

from src.graph import graph, make_initial_state
from src.nodes.pedagogy_agent import generate_diagnostic_question, get_diagnostic_order, get_diagnostic_answer_keywords
from src.anatomy_images import get_image_for_topic
from src.nodes.socratic_generator import analyze_uploaded_image
from src.nodes.retrieval_planner import _load_bm25_corpus

with open("config.yaml") as f:
    cfg = yaml.safe_load(f)

_DIAGNOSTIC_QUESTIONS = cfg["session"]["diagnostic_questions"]

# Pre-initialize BM25 corpus on startup to avoid stalls on first retrieval
try:
    _load_bm25_corpus()
except Exception:
    pass  # Will retry on first retrieval if startup init fails


def _fmt_diag_q(idx: int, question: str, total: int, first: bool = False) -> str:
    prefix = (
        f"---\n\n**Pre-assessment — {total} questions to see what you already know:**\n\n"
        if first else "---\n\n"
    )
    return f"{prefix}**Q{idx + 1} of {total}:** {question}"

# Phase display names and icons
_PHASE_INFO = {
    "rapport":    ("🩺 Diagnostic",  "#3B82F6"),
    "tutoring":   ("📖 Tutoring",    "#10B981"),
    "assessment": ("🧪 Assessment",  "#F59E0B"),
    "wrapup":     ("📋 Session End", "#8B5CF6"),
}

_PHASE_TRANSITION_MSGS = {
    ("rapport",    "tutoring"):    (
        "## 🎓 Diagnostic Complete — Starting Tutoring\n\n"
        "I've calibrated your starting point based on your diagnostic answers. "
        "We'll now dive into the topics that need the most attention using the Socratic method — "
        "I'll guide you with questions rather than answers. Let's go!"
    ),
    ("tutoring",   "assessment"): (
        "## 🧪 Tutoring Complete — Moving to Assessment\n\n"
        "You've covered strong ground in the tutoring phase! "
        "Now let's put your knowledge to the test with a clinical scenario. "
        "I'll present a realistic NBCOT-style case — explain your reasoning out loud."
    ),
    ("assessment", "wrapup"): (
        "## 📋 Assessment Complete — Generating Your Report\n\n"
        "Session complete! Compiling your performance report with personalised "
        "study recommendations and follow-up questions..."
    ),
    ("tutoring",   "wrapup"): (
        "## 📋 Session Time Up — Generating Your Report\n\n"
        "Time's up for today! Compiling your session report with an honest breakdown "
        "of what you've learned and what still needs work..."
    ),
    ("rapport",    "wrapup"): (
        "## 📋 Session Ended\n\nGenerating your session report..."
    ),
}


# Topic menu: display name, topic key, keywords for matching
_TOPIC_MENU = [
    ("Brachial Plexus",                        "brachial_plexus",     ["1", "brachial", "plexus"]),
    ("Rotator Cuff",                            "rotator_cuff",        ["2", "rotator", "cuff", "sits"]),
    ("Peripheral Nerves (median, ulnar, radial)","peripheral_nerves",   ["3", "peripheral", "median", "ulnar", "radial", "axillary"]),
    ("Shoulder Joint",                          "shoulder_joint",      ["4", "shoulder", "glenohumeral", "ac joint"]),
    ("Elbow Joint",                             "elbow_joint",         ["5", "elbow", "cubital", "carrying angle"]),
    ("Wrist & Hand",                            "wrist_hand",          ["6", "wrist", "hand", "carpal", "thenar"]),
    ("Dermatomes (C5–T1)",                      "dermatomes",          ["7", "dermatome", "sensation", "sensory", "numbness"]),
    ("Nerve Injury Syndromes",                  "nerve_injuries",      ["8", "nerve injur", "erb", "klumpke", "wrist drop", "claw", "palsy", "saturday"]),
    ("Upper Limb Muscles",                      "upper_limb_muscles",  ["9", "muscle", "biceps", "triceps", "deltoid"]),
    ("Spinal Cord",                             "spinal_cord",         ["10", "spinal cord", "spinal", "conus", "cauda"]),
]


async def _parse_topic_choice(text: str) -> tuple[str, str]:
    """Extract chosen topic key and learning_mode from the student's first message.
    Returns (topic_key, learning_mode). Falls back to LLM if keyword match fails.
    """
    lower = text.lower().strip()
    _visual_kw = ("diagram", "digram", "diagrams", "visual", "image", "picture", "figure", "draw", "sketch", "chart")
    learning_mode = "visual" if any(w in lower for w in _visual_kw) else "text"

    # Keyword / number matching (fast path)
    for _, key, keywords in _TOPIC_MENU:
        if any(kw in lower for kw in keywords):
            return f"topic:{key}", learning_mode

    # LLM fallback for free-form answers
    import json as _json
    from openai import AsyncOpenAI
    from dotenv import load_dotenv
    load_dotenv()
    topic_list = ", ".join(k for _, k, _ in _TOPIC_MENU)
    try:
        client = AsyncOpenAI()
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=60,
            temperature=0,
            messages=[
                {"role": "system", "content": (
                    f"Pick the single best matching topic key from: {topic_list}. "
                    "Return ONLY the key, nothing else."
                )},
                {"role": "user", "content": text},
            ],
        )
        key = resp.choices[0].message.content.strip().lower().replace(" ", "_")
        valid_keys = {k for _, k, _ in _TOPIC_MENU}
        if key in valid_keys:
            return f"topic:{key}", learning_mode
    except Exception:
        pass

    # Last resort: brachial_plexus (most foundational)
    return "topic:brachial_plexus", learning_mode


# ── Session lifecycle ─────────────────────────────────────────────────────────

@cl.on_chat_start
async def on_chat_start():
    session_id = str(uuid.uuid4())
    state = make_initial_state(session_id)
    cl.user_session.set("state", state)
    cl.user_session.set("session_start", time.time())
    cl.user_session.set("warmup_done", False)    # Track casual warm-up exchange
    cl.user_session.set("diag_q_index", 0)      # Next diagnostic question to inject

    topic_list = "\n".join(
        f"{i+1}. {name}" for i, (name, _, _) in enumerate(_TOPIC_MENU)
    )
    welcome = (
        "# 👋 Welcome to UnMask\n\n"
        "I'm your NBCOT anatomy study companion. I use the **Socratic method** — "
        "I'll ask questions to build real understanding, not just hand you the answers.\n\n"
        "**Which topic do you want to study today?**\n\n"
        f"{topic_list}\n\n"
        "Also — do you prefer **diagrams** or **written explanations**?\n\n"
        "*(Reply with a number, topic name, or just describe what's giving you trouble!)*"
    )

    await cl.Message(content=welcome, author="UnMask").send()


@cl.on_message
async def on_message(message: cl.Message):
    if not message.content or not message.content.strip():
        await cl.Message(content="Please type your answer before submitting.", author="UnMask").send()
        return

    state = cl.user_session.get("state")
    start_time = cl.user_session.get("session_start", time.time())

    prev_phase = state.get("phase", "rapport")

    # Update elapsed time
    state["elapsed_seconds"] = time.time() - start_time
    state["student_message"] = message.content
    # IMPORTANT: Never re-pass accumulated conversation_history to graph.invoke.
    # TutoringState.conversation_history uses operator.add, so passing the full
    # history again would double it on every turn (checkpointer already holds it).
    state["conversation_history"] = []

    # ── Capture topic + learning mode from first message (before graph call) ────
    warmup_already_done = cl.user_session.get("warmup_done", False)
    if not warmup_already_done:
        study_focus, learning_mode = await _parse_topic_choice(message.content)
        state["study_focus"] = study_focus
        state["learning_mode"] = learning_mode

    # ── Check for student-uploaded images (VLM Task 4) ────────────────────────────
    vlm_image_analyzed = False
    if message.elements and any(e.type == "image" for e in message.elements):
        # Student uploaded an anatomical image — use GPT-4o Vision for Socratic analysis
        for elem in message.elements:
            if elem.type == "image" and elem.path:
                try:
                    socratic_q = analyze_uploaded_image(elem.path)
                    state["student_message"] = socratic_q
                    vlm_image_analyzed = True
                    # Replace main message with VLM analysis so graph processes the question
                    break
                except Exception as e:
                    # Log error but continue with original message
                    import traceback
                    traceback.print_exc()

    state["vlm_image_analyzed"] = vlm_image_analyzed

    # ── Show loading indicator immediately ──────────────────────────────────
    thinking_msg = cl.Message(content="⏳ *Thinking...*", author="UnMask")
    await thinking_msg.send()

    # Run LangGraph with error handling
    import asyncio
    config = {"configurable": {"thread_id": state["session_id"]}}
    loop = asyncio.get_running_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: graph.invoke(state, config=config)),
            timeout=90.0,
        )
    except asyncio.TimeoutError:
        await thinking_msg.remove()
        await cl.Message(
            content="The response timed out — please try again.",
            author="UnMask"
        ).send()
        return
    except Exception as e:
        await thinking_msg.remove()
        await cl.Message(
            content=f"I had a technical hiccup — please try again. ({type(e).__name__})",
            author="UnMask"
        ).send()
        return

    # ── If diagnostic just completed, immediately re-invoke to get first tutoring Q ─
    # (Orchestrator transitions rapport→tutoring only on the *next* invocation,
    #  so we fire a second silent invoke here to avoid leaving the user with a blank.)
    prev_diag_complete = state.get("diagnostic_complete", False)
    just_finished_diag = (not prev_diag_complete) and result.get("diagnostic_complete", False)

    if just_finished_diag:
        # Start tutoring on the weakest specific concept within the chosen topic
        sf = result.get("study_focus") or state.get("study_focus") or ""
        chosen_topic = sf.replace("topic:", "").strip() if sf.startswith("topic:") else ""
        mastery = result.get("mastery_scores", {})

        # Pick the weakest concept within the chosen topic (most in need of tutoring)
        from src.nodes.pedagogy_agent import _TOPIC_BANK_MAP, _DIAGNOSTIC_BANK
        topic_concepts = [_DIAGNOSTIC_BANK[i]["concept"] for i in _TOPIC_BANK_MAP.get(chosen_topic, [])]
        if topic_concepts:
            start_concept = min(topic_concepts, key=lambda c: mastery.get(c, 0))
        elif mastery:
            start_concept = min(mastery, key=lambda k: mastery[k])
        else:
            start_concept = chosen_topic or "nerve_injuries.radial"

        trigger_msg = f"Let's work on {start_concept.replace('_', ' ').replace('.', ' ')}"
        result["student_message"] = trigger_msg
        result["current_topic"] = start_concept
        result["conversation_history"] = []
        result["elapsed_seconds"] = time.time() - start_time
        result["consecutive_incorrect"] = 0
        result["consecutive_correct"] = 0
        result["vlm_image_analyzed"] = False
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: graph.invoke(result, config=config)),
                timeout=90.0,
            )
        except Exception as e:
            # If second invoke fails, log but continue with first result
            import traceback
            traceback.print_exc()
        # Reset again after invoke — pedagogy_agent evaluates the synthetic trigger
        # message as "wrong", which would poison the counter for the first real Q
        result["consecutive_incorrect"] = 0
        result["consecutive_correct"] = 0

    # Persist updated state
    cl.user_session.set("state", result)

    phase = result.get("phase", "rapport")
    turn = result.get("turn_count", 0)
    diagnostic_complete = result.get("diagnostic_complete", False)

    # ── Phase transition banner ──────────────────────────────────────────────
    if prev_phase != phase:
        transition_key = (prev_phase, phase)
        transition_msg = _PHASE_TRANSITION_MSGS.get(transition_key)
        if transition_msg:
            # Replace the thinking placeholder with the transition banner
            thinking_msg.content = transition_msg
            thinking_msg.author = "🔄 Phase Transition"
            await thinking_msg.update()
            thinking_msg = None  # send response as a new message below

    # ── Main response ────────────────────────────────────────────────────────
    response = result.get("generated_response", "")
    warmup_done = cl.user_session.get("warmup_done", False)

    # During rapport: first message = topic pick → immediately start pre-assessment
    if phase == "rapport" and not diagnostic_complete:
        diag_idx = cl.user_session.get("diag_q_index", 0)
        if not warmup_done:
            order = get_diagnostic_order(state.get("study_focus") or "", n=_DIAGNOSTIC_QUESTIONS)
            diag_total = len(order)
            cl.user_session.set("diag_order", order)
            cl.user_session.set("diag_total", diag_total)
            cl.user_session.set("warmup_done", True)
            cl.user_session.set("diag_q_index", 1)
            # Acknowledge the topic choice + learning mode
            sf = state.get("study_focus", "")
            lm = state.get("learning_mode", "text")
            topic_key = sf.replace("topic:", "").replace("_", " ").title() if sf.startswith("topic:") else "this topic"
            mode_note = " I'll include diagrams as we go." if lm == "visual" else ""
            ack = f"**{topic_key}** — good choice.{mode_note} Let me see what you already know.\n\n"
            q0 = generate_diagnostic_question(order[0])
            q0_block = _fmt_diag_q(0, q0, diag_total, first=True)
            response = ack + q0_block
            result["current_diagnostic_question"] = q0
            result["current_diagnostic_answer_hint"] = get_diagnostic_answer_keywords(order[0])
        else:
            order = cl.user_session.get("diag_order", list(range(_DIAGNOSTIC_QUESTIONS)))
            diag_total = cl.user_session.get("diag_total", len(order))
            if diag_idx < len(order):
                next_q = generate_diagnostic_question(order[diag_idx])
                if next_q:
                    q_block = _fmt_diag_q(diag_idx, next_q, diag_total)
                    response = (response + f"\n\n{q_block}") if response else q_block
                    result["current_diagnostic_question"] = next_q
                    result["current_diagnostic_answer_hint"] = get_diagnostic_answer_keywords(order[diag_idx])
                    cl.user_session.set("diag_q_index", diag_idx + 1)

    # Determine author label
    author_map = {
        "wrapup":     "📋 Session Report",
        "assessment": "🧪 Assessment",
        "tutoring":   "📖 Tutor",
    }
    author = author_map.get(phase, "UnMask")

    # Update thinking placeholder with the tutor response first
    if response:  # skip send entirely if response is empty (avoids blank duplicate messages)
        if thinking_msg is not None:
            thinking_msg.content = response
            thinking_msg.author = author
            await thinking_msg.update()
            thinking_msg = None
        else:
            await cl.Message(content=response, author=author).send()
    elif thinking_msg is not None:
        await thinking_msg.remove()

    # ── Force visual hint if student explicitly requests a diagram mid-session ──
    _student_msg_lower = (message.content or "").lower()
    _diagram_keywords = ("diagram", "image", "picture", "figure", "visual", "show me", "illustrate")
    if phase == "tutoring" and not result.get("visual_hint") and any(w in _student_msg_lower for w in _diagram_keywords):
        topic_for_img = result.get("current_topic") or state.get("current_topic") or ""
        result["visual_hint"] = f"__concept__:{topic_for_img}\nHere is a diagram for this topic."
        # Also switch to visual mode for remainder of session
        result["learning_mode"] = "visual"
        state["learning_mode"] = "visual"
        cl.user_session.set("state", result)

    # ── Visual hint card — always a fresh send() so cl.Image renders correctly ──
    visual_hint = result.get("visual_hint")
    if visual_hint and phase == "tutoring":
        # Extract concept id embedded in hint text: "__concept__:id\ntext"
        hint_text = visual_hint
        hint_concept = result.get("current_topic") or ""
        if visual_hint.startswith("__concept__:"):
            first_newline = visual_hint.index("\n")
            hint_concept = visual_hint[len("__concept__:"):first_newline].strip()
            hint_text = visual_hint[first_newline + 1:].strip()

        img_data = get_image_for_topic(hint_concept) or get_image_for_topic(result.get("current_topic") or "")

        concept_label = hint_concept.replace("_", " ").replace(".", " › ").title()

        # Build study-guide text from hint_text (figure description from KB)
        # Trim to first 3 sentences so it's scannable, not overwhelming
        import re as _re
        _sentences = _re.split(r'(?<=[.!?])\s+', hint_text.strip())
        _study_notes = " ".join(_sentences[:3]).strip() if _sentences else ""

        if img_data:
            elements = []
            image_file = img_data.get("image_file")
            has_image = False
            if image_file:
                img_path = os.path.abspath(os.path.join("public", "anatomy", image_file))
                if os.path.exists(img_path):
                    elements.append(cl.Image(path=img_path, name=concept_label, display="inline"))
                    has_image = True

            # Build card: image first, then caption, then guided notes
            card_lines = [f"### 🖼️ {concept_label}", ""]
            card_lines.append(f"*{img_data['caption']}*")
            card_lines.append("")
            if not has_image:
                # ASCII fallback only when no real image
                card_lines.append(f"```\n{img_data['diagram']}\n```")
                card_lines.append("")
            if _study_notes:
                card_lines.append("**What to look for:**")
                card_lines.append(f"> {_study_notes}")
                card_lines.append("")
            card_lines.append("---")
            card_lines.append("*Study the diagram above, then try the question again.*")

            await cl.Message(
                content="\n".join(card_lines),
                elements=elements,
                author="🖼️ Visual Aid",
            ).send()
        else:
            # No image data at all — show the KB text as a clean reference block
            card_lines = [f"### 📖 Reference — {concept_label}", ""]
            if _study_notes:
                card_lines.append("**What to know:**")
                card_lines.append(f"> {_study_notes}")
                card_lines.append("")
            card_lines.append("---")
            card_lines.append("*Review this, then try the question again.*")
            await cl.Message(
                content="\n".join(card_lines),
                author="🖼️ Visual Aid",
            ).send()

    if phase == "wrapup":
        await _send_followup_resources(result)

    # ── Assessment feedback (separate styled message) ────────────────────────
    assessment_feedback = result.get("assessment_feedback")
    if assessment_feedback and phase == "assessment":
        await cl.Message(
            content=assessment_feedback,
            author="📝 Assessment Feedback",
        ).send()

    # ── Backend debug panel (instructor-visible metadata) ────────────────────
    mastery = result.get("mastery_scores", {})
    chunks = result.get("retrieved_chunks", [])
    retrieval_mode = result.get("retrieval_mode", "—")

    if chunks or mastery:
        elements = []

        if mastery:
            mastery_lines = "\n".join(
                f"  {'🟢' if v >= 0.7 else '🟡' if v >= 0.4 else '🔴'} {k}: {v:.2f}"
                for k, v in sorted(mastery.items())
            )
            elements.append(
                cl.Text(
                    name="📊 Mastery Scores",
                    content=f"```\n{mastery_lines}\n```",
                    display="side",
                )
            )

        if chunks:
            chunk_summary = f"**PCR Mode: `{retrieval_mode}`** — {len(chunks)} chunks retrieved\n\n"
            for i, c in enumerate(chunks[:5], 1):
                flag = "🔒 ANSWER" if c.get("is_answer_chunk") else f"📄 {c.get('chunk_type','ctx').upper()}"
                chunk_summary += f"**{i}. [{flag}]** `{c.get('concept','?')}`\n> {c['text'][:120]}...\n\n"
            elements.append(
                cl.Text(
                    name="🔍 Retrieved Chunks",
                    content=chunk_summary,
                    display="side",
                )
            )

        # Session state + mistake log + revisit status
        mistake_log = result.get("mistake_log", [])
        revisit_info = ""
        if result.get("revisit_scheduled"):
            rt = result.get("revisit_topic", "")
            revisit_info = f"\n**Revisit scheduled:** {rt.replace('_',' ').replace('.',' › ')}"
        session_info = (
            f"**Phase:** {phase}  |  **Turn:** {turn}  |  "
            f"**Elapsed:** {result.get('elapsed_seconds', 0):.0f}s\n"
            f"**Coverage:** {result.get('coverage_ratio', 0):.0%}  |  "
            f"**Consecutive correct:** {result.get('consecutive_correct', 0)}  |  "
            f"**Consecutive incorrect:** {result.get('consecutive_incorrect', 0)}"
            f"{revisit_info}"
        )
        elements.append(
            cl.Text(name="⚙️ Session State", content=session_info, display="side")
        )

        if mistake_log:
            mistake_text = "\n".join(
                f"Turn {m['turn']} | {m['topic'].replace('_',' ').replace('.',' › ')}: "
                f"{m.get('misconception','—') or '—'}"
                for m in mistake_log
            )
            elements.append(
                cl.Text(
                    name="⚠️ Mistake Log",
                    content=f"```\n{mistake_text}\n```",
                    display="side",
                )
            )

        await cl.Message(content="", elements=elements).send()


async def _send_followup_resources(result: dict) -> None:
    """
    After a wrapup, send a separate flashcard + diagram message from the structured
    SessionSummary stored in _internal_analysis.
    """
    internal = result.get("_internal_analysis")
    if not internal:
        return

    flashcards = internal.get("flashcards", [])
    diagrams = internal.get("diagram_suggestions", [])

    # ── Flashcard message ────────────────────────────────────────────────────
    if flashcards:
        lines = ["## 🃏 Your Session Flashcards\n"]
        lines.append("*Cover the answer, read the question aloud — then reveal. Repeat daily!*\n")
        lines.append("---\n")
        for i, fc in enumerate(flashcards, 1):
            if isinstance(fc, dict):
                concept = fc.get("concept", "").replace("_", " ").replace(".", " › ")
                front = fc.get("front", "")
                back = fc.get("back", "")
            else:
                concept = getattr(fc, "concept", "").replace("_", " ").replace(".", " › ")
                front = getattr(fc, "front", "")
                back = getattr(fc, "back", "")
            lines.append(f"**Card {i}** — `{concept}`")
            lines.append(f"**Q:** {front}")
            lines.append(f"**A:** {back}\n")

        await cl.Message(
            content="\n".join(lines),
            author="🃏 Flashcards",
        ).send()

    # ── Diagram suggestions message ──────────────────────────────────────────
    if diagrams:
        from src.anatomy_images import get_image_for_topic as _get_img
        for d in diagrams:
            # Find the best-matching diagram for this suggestion
            img = None
            for key in [
                "brachial_plexus.terminal_branches", "brachial_plexus.cords",
                "brachial_plexus.trunks", "brachial_plexus",
                "rotator_cuff.supraspinatus", "rotator_cuff.infraspinatus",
                "rotator_cuff.subscapularis", "rotator_cuff",
                "peripheral_nerves.median", "peripheral_nerves.ulnar",
                "peripheral_nerves.radial", "peripheral_nerves.axillary",
                "peripheral_nerves", "shoulder_joint",
                "spinal_cord.anterior_rami", "spinal_cord.anatomy",
            ]:
                if key.replace("_", " ").replace(".", " ") in d.lower() or key.split(".")[-1] in d.lower():
                    img = _get_img(key)
                    if img:
                        break

            if not img:
                continue

            elements = []
            image_file = img.get("image_file")
            has_image = False
            if image_file:
                img_path = os.path.abspath(os.path.join("public", "anatomy", image_file))
                if os.path.exists(img_path):
                    elements.append(cl.Image(path=img_path, name=img["caption"][:50], display="inline"))
                    has_image = True
            body = (
                f"### 🖼️ {d}\n\n"
                f"📌 *{img['caption']}*\n\n"
                + ("" if has_image else f"```\n{img['diagram']}\n```\n\n")
                + "---\n*Tip: Cover and redraw from memory, then check.*"
            )
            await cl.Message(content=body, elements=elements, author="🖼️ Study Diagram").send()
