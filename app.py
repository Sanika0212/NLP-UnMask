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
import time
import uuid

import chainlit as cl
import yaml

from src.graph import graph, make_initial_state
from src.nodes.pedagogy_agent import generate_diagnostic_question, get_diagnostic_order
from src.anatomy_images import get_image_for_topic

with open("config.yaml") as f:
    cfg = yaml.safe_load(f)

_DIAGNOSTIC_QUESTIONS = cfg["session"]["diagnostic_questions"]


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
    learning_mode = "visual" if any(w in lower for w in ("diagram", "visual", "image", "picture", "figure")) else "text"

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

    # ── Show loading indicator immediately ──────────────────────────────────
    thinking_msg = cl.Message(content="⏳ *Thinking...*", author="UnMask")
    await thinking_msg.send()

    # Run LangGraph
    config = {"configurable": {"thread_id": state["session_id"]}}
    result = graph.invoke(state, config=config)

    # ── If diagnostic just completed, immediately re-invoke to get first tutoring Q ─
    # (Orchestrator transitions rapport→tutoring only on the *next* invocation,
    #  so we fire a second silent invoke here to avoid leaving the user with a blank.)
    prev_diag_complete = state.get("diagnostic_complete", False)
    just_finished_diag = (not prev_diag_complete) and result.get("diagnostic_complete", False)

    if just_finished_diag:
        # Start tutoring on the topic the student chose at onboarding
        sf = result.get("study_focus") or state.get("study_focus") or ""
        chosen = sf.replace("topic:", "").strip() if sf.startswith("topic:") else ""
        if not chosen:
            mastery = result.get("mastery_scores", {})
            chosen = min(mastery, key=lambda k: mastery[k]) if mastery else "brachial_plexus.origin"
        trigger_msg = f"Let's start tutoring on {chosen.replace('_', ' ').replace('.', ' ')}"
        result["student_message"] = trigger_msg
        result["current_topic"] = chosen
        result["conversation_history"] = []
        result["elapsed_seconds"] = time.time() - start_time
        result = graph.invoke(result, config=config)

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
            # Acknowledge the topic choice
            sf = state.get("study_focus", "")
            topic_key = sf.replace("topic:", "").replace("_", " ").title() if sf.startswith("topic:") else "this topic"
            ack = f"**{topic_key}** — good choice. Let me see what you already know.\n\n"
            q0 = generate_diagnostic_question(order[0])
            q0_block = _fmt_diag_q(0, q0, diag_total, first=True)
            response = ack + q0_block
        else:
            order = cl.user_session.get("diag_order", list(range(_DIAGNOSTIC_QUESTIONS)))
            diag_total = cl.user_session.get("diag_total", len(order))
            if diag_idx < len(order):
                next_q = generate_diagnostic_question(order[diag_idx])
                if next_q:
                    q_block = _fmt_diag_q(diag_idx, next_q, diag_total)
                    response = (response + f"\n\n{q_block}") if response else q_block
                    cl.user_session.set("diag_q_index", diag_idx + 1)

    # Determine author label
    author_map = {
        "wrapup":     "📋 Session Report",
        "assessment": "🧪 Assessment",
        "tutoring":   "📖 Tutor",
    }
    author = author_map.get(phase, "UnMask")

    # Update thinking placeholder with the tutor response first
    if thinking_msg is not None:
        thinking_msg.content = response
        thinking_msg.author = author
        await thinking_msg.update()
    else:
        await cl.Message(content=response, author=author).send()

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

        if img_data:
            elements = []
            image_file = img_data.get("image_file")
            if image_file:
                img_path = os.path.abspath(os.path.join("public", "anatomy", image_file))
                if os.path.exists(img_path):
                    elements.append(cl.Image(path=img_path, name=concept_label, display="inline"))
                    image_file = None  # mark as loaded; skip ASCII fallback
            await cl.Message(
                content=(
                    f"### 🖼️ Visual Reference — {concept_label}\n\n"
                    f"📌 *{img_data['caption']}*\n\n"
                    + ("" if not image_file else f"```\n{img_data['diagram']}\n```\n\n")
                    + "---\n*Study this, then try the question below.*"
                ),
                elements=elements,
                author="🖼️ Visual Aid",
            ).send()
        else:
            await cl.Message(
                content=f"### 🖼️ Reference — {concept_label}\n\n```\n{hint_text}\n```\n\n---\n*Study this, then try again.*",
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
