"""
UnMask — Chainlit entry point.

Run:
  chainlit run app.py

The agent supervisor routes each turn through specialist pipelines.
Routing decisions are surfaced live via cl.Step so students and
instructors can see WHY the tutor does what it does.
"""
from __future__ import annotations

import os
import re
import sys
import time
import uuid

import chainlit as cl
import yaml
from dotenv import load_dotenv

load_dotenv()

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
from src.survey import run_onboarding, run_pre_quiz, run_post_survey

with open("config.yaml") as f:
    cfg = yaml.safe_load(f)

_DIAGNOSTIC_QUESTIONS = cfg["session"]["diagnostic_questions"]

try:
    _load_bm25_corpus()
except Exception:
    pass


# ── Topic menu ─────────────────────────────────────────────────────────────────

_TOPIC_MENU = [
    ("Brachial Plexus",                         "brachial_plexus",    ["1", "brachial", "plexus"]),
    ("Rotator Cuff",                             "rotator_cuff",       ["2", "rotator", "cuff", "sits"]),
    ("Peripheral Nerves (median, ulnar, radial)", "peripheral_nerves",  ["3", "peripheral", "median", "ulnar", "radial", "axillary"]),
    ("Shoulder Joint",                           "shoulder_joint",     ["4", "shoulder", "glenohumeral", "ac joint"]),
    ("Elbow Joint",                              "elbow_joint",        ["5", "elbow", "cubital", "carrying angle"]),
    ("Wrist & Hand",                             "wrist_hand",         ["6", "wrist", "hand", "carpal", "thenar"]),
    ("Dermatomes (C5–T1)",                       "dermatomes",         ["7", "dermatome", "sensation", "sensory", "numbness"]),
    ("Nerve Injury Syndromes",                   "nerve_injuries",     ["8", "nerve injur", "erb", "klumpke", "wrist drop", "claw", "palsy", "saturday"]),
    ("Upper Limb Muscles",                       "upper_limb_muscles", ["9", "muscle", "biceps", "triceps", "deltoid"]),
    ("Spinal Cord",                              "spinal_cord",        ["10", "spinal cord", "spinal", "conus", "cauda"]),
]

_PHASE_INFO = {
    "rapport":    ("🩺 Diagnostic",  "#3B82F6"),
    "tutoring":   ("📖 Tutoring",    "#10B981"),
    "assessment": ("🧪 Assessment",  "#F59E0B"),
    "wrapup":     ("📋 Session End", "#8B5CF6"),
}

_PHASE_TRANSITION_MSGS = {
    ("rapport",    "tutoring"):   (
        "## 🎓 Diagnostic Complete — Starting Tutoring\n\n"
        "I've calibrated your starting point. We'll now use the Socratic method — "
        "I'll guide you with questions rather than answers. Let's go!"
    ),
    ("tutoring",   "assessment"): (
        "## 🧪 Tutoring Complete — Moving to Assessment\n\n"
        "Strong work in tutoring! Now let's test your knowledge with a clinical scenario. "
        "Explain your reasoning out loud — NBCOT style."
    ),
    ("assessment", "wrapup"): (
        "## 📋 Assessment Complete — Generating Your Report\n\nCompiling your performance report..."
    ),
    ("tutoring",   "wrapup"): (
        "## 📋 Session Time Up — Generating Your Report\n\n"
        "Time's up! Compiling your session report with an honest breakdown..."
    ),
    ("rapport",    "wrapup"): "## 📋 Session Ended\n\nGenerating your session report...",
}


async def _parse_topic_choice(text: str) -> tuple[str, str]:
    """Extract chosen topic key and learning_mode. Falls back to LLM on no keyword match."""
    lower = text.lower().strip()
    _visual_kw = ("diagram", "digram", "diagrams", "visual", "image", "picture", "figure", "draw", "sketch", "chart")
    learning_mode = "visual" if any(w in lower for w in _visual_kw) else "text"

    for _, key, keywords in _TOPIC_MENU:
        if any(kw in lower for kw in keywords):
            return f"topic:{key}", learning_mode

    from openai import AsyncOpenAI
    topic_list = ", ".join(k for _, k, _ in _TOPIC_MENU)
    try:
        client = AsyncOpenAI()
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=60,
            temperature=0,
            messages=[
                {"role": "system", "content": f"Pick the single best matching topic key from: {topic_list}. Return ONLY the key."},
                {"role": "user", "content": text},
            ],
        )
        key = resp.choices[0].message.content.strip().lower().replace(" ", "_")
        if key in {k for _, k, _ in _TOPIC_MENU}:
            return f"topic:{key}", learning_mode
    except Exception:
        pass

    return "topic:brachial_plexus", learning_mode


def _fmt_diag_q(idx: int, question: str, total: int, first: bool = False) -> str:
    prefix = (
        f"---\n\n**Pre-assessment — {total} questions to see what you already know:**\n\n"
        if first else "---\n\n"
    )
    return f"{prefix}**Q{idx + 1} of {total}:** {question}"


def _phase_progress(phase: str) -> str:
    """Unicode progress bar across the four phases."""
    phases = ["rapport", "tutoring", "assessment", "wrapup"]
    labels = ["Diagnostic", "Tutoring", "Assessment", "Wrap-up"]
    idx = phases.index(phase) if phase in phases else 0
    parts = []
    for i, label in enumerate(labels):
        if i < idx:
            parts.append(f"~~{label}~~ ✓")
        elif i == idx:
            parts.append(f"**{label} ←**")
        else:
            parts.append(label)
    return " · ".join(parts)


# ── Session lifecycle ──────────────────────────────────────────────────────────

@cl.on_chat_start
async def on_chat_start():
    # Guard 1: same WebSocket session reconnect
    if cl.user_session.get("_initialized"):
        return
    cl.user_session.set("_initialized", True)

    session_id = str(uuid.uuid4())
    state = make_initial_state(session_id)

    cl.user_session.set("state", state)
    cl.user_session.set("session_start", time.time())
    cl.user_session.set("warmup_done", False)
    cl.user_session.set("diag_q_index", 0)
    cl.user_session.set("survey_mode", False)

    mode_res = await cl.AskActionMessage(
        content=(
            "# 👋 Welcome to UnMask\n\n"
            "I'm your AI anatomy study partner for NBCOT prep.\n\n"
            "> **How it works:** I use the Socratic method — I ask questions to build real "
            "understanding, not just hand you answers. An AI supervisor routes each turn to the "
            "right specialist (diagnostic, tutor, assessment, or wrap-up).\n\n"
            "Are you here for the **pilot study** or a regular study session?"
        ),
        actions=[
            cl.Action(name="pilot",   value="pilot",   label="🔬 Pilot Study (pre/post quiz + survey)", payload={}),
            cl.Action(name="regular", value="regular", label="📚 Regular Study Session",                payload={}),
        ],
        author="UnMask",
        timeout=120,
    ).send()

    if mode_res and mode_res.get("value") == "pilot":
        cl.user_session.set("survey_mode", True)
        await run_onboarding()
        await run_pre_quiz()

    topic_res = await cl.AskActionMessage(
        content=(
            "# 📚 Let's Study\n\n"
            "**Which topic do you want to focus on today?**"
        ),
        actions=[
            cl.Action(name=key, value=f"topic:{key}", label=name, payload={"topic": key})
            for name, key, _ in _TOPIC_MENU
        ],
        author="UnMask",
        timeout=300,
    ).send()
    if topic_res:
        # value field may be None in Chainlit 2.x — name is always reliable
        val = topic_res.get("value") or topic_res.get("payload", {}).get("topic") or topic_res.get("name", "brachial_plexus")
        study_focus = val if val.startswith("topic:") else f"topic:{val}"
    else:
        study_focus = "topic:brachial_plexus"

    pref_res = await cl.AskActionMessage(
        content="Do you prefer **diagrams** or **written explanations**?",
        actions=[
            cl.Action(name="visual", value="visual", label="🖼️ Diagrams",              payload={"mode": "visual"}),
            cl.Action(name="text",   value="text",   label="📝 Written explanations",  payload={"mode": "text"}),
        ],
        author="UnMask",
        timeout=60,
    ).send()
    if pref_res:
        learning_mode = (
            pref_res.get("value") or
            pref_res.get("payload", {}).get("mode") or
            pref_res.get("name", "text")
        )
    else:
        learning_mode = "text"

    state = cl.user_session.get("state")
    state["study_focus"] = study_focus
    state["learning_mode"] = learning_mode

    order = get_diagnostic_order(study_focus, n=_DIAGNOSTIC_QUESTIONS)
    diag_total = len(order)
    cl.user_session.set("diag_order", order)
    cl.user_session.set("diag_total", diag_total)
    cl.user_session.set("warmup_done", True)
    cl.user_session.set("diag_q_index", 1)

    topic_key = study_focus.replace("topic:", "").replace("_", " ").title()
    mode_note = " I'll include diagrams as we go." if learning_mode == "visual" else ""
    q0 = generate_diagnostic_question(order[0])
    q0_block = _fmt_diag_q(0, q0, diag_total, first=True)
    state["current_diagnostic_question"] = q0
    state["current_diagnostic_answer_hint"] = get_diagnostic_answer_keywords(order[0])
    cl.user_session.set("state", state)

    await cl.Message(
        content=f"**{topic_key}** — good choice.{mode_note} Let me see what you already know.\n\n{q0_block}",
        author="UnMask",
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    if not message.content or not message.content.strip():
        await cl.Message(content="Please type your answer before submitting.", author="UnMask").send()
        return

    state = cl.user_session.get("state")
    start_time = cl.user_session.get("session_start", time.time())
    prev_phase = state.get("phase", "rapport")

    state["elapsed_seconds"] = time.time() - start_time
    state["student_message"] = message.content
    # Do NOT re-pass accumulated history — operator.add in state doubles it via checkpointer
    state["conversation_history"] = []

    warmup_already_done = cl.user_session.get("warmup_done", False)

    # VLM: student-uploaded anatomical image
    vlm_image_analyzed = False
    if message.elements and any(e.type == "image" for e in message.elements):
        for elem in message.elements:
            if elem.type == "image" and elem.path:
                try:
                    socratic_q = analyze_uploaded_image(elem.path)
                    state["student_message"] = socratic_q
                    vlm_image_analyzed = True
                    break
                except Exception:
                    import traceback; traceback.print_exc()
    state["vlm_image_analyzed"] = vlm_image_analyzed

    # ── Run the graph (supervisor + specialist pipeline) ──────────────────────
    import asyncio
    config = {"configurable": {"thread_id": state["session_id"]}}
    loop = asyncio.get_running_loop()

    thinking_msg = cl.Message(content="⏳ *Thinking...*", author="UnMask")
    await thinking_msg.send()

    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: graph.invoke(state, config=config)),
            timeout=90.0,
        )
    except asyncio.TimeoutError:
        await thinking_msg.remove()
        await cl.Message(content="The response timed out — please try again.", author="UnMask").send()
        return
    except Exception as e:
        await thinking_msg.remove()
        await cl.Message(
            content=f"I had a technical hiccup — please try again. ({type(e).__name__})",
            author="UnMask",
        ).send()
        return

    cl.user_session.set("state", result)

    phase = result.get("phase", "rapport")
    turn  = result.get("turn_count", 0)
    diagnostic_complete = result.get("diagnostic_complete", False)

    # ── Phase transition banner ────────────────────────────────────────────────
    if prev_phase != phase:
        banner = _PHASE_TRANSITION_MSGS.get((prev_phase, phase))
        if banner:
            thinking_msg.content = banner
            thinking_msg.author = "🔄 Phase Transition"
            await thinking_msg.update()
            thinking_msg = None

    # ── Build response text (inject diagnostic Q if in rapport) ───────────────
    response = result.get("generated_response", "")

    if phase == "rapport" and not diagnostic_complete:
        diag_idx = cl.user_session.get("diag_q_index", 0)
        if not warmup_already_done:
            order = get_diagnostic_order(state.get("study_focus") or "", n=_DIAGNOSTIC_QUESTIONS)
            diag_total = len(order)
            cl.user_session.set("diag_order", order)
            cl.user_session.set("diag_total", diag_total)
            cl.user_session.set("warmup_done", True)
            cl.user_session.set("diag_q_index", 1)
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

    # ── Detect explicit diagram request — suppress the graph's text response ──
    _msg_lower = (message.content or "").lower()
    _diagram_kw = ("diagram", "image", "picture", "figure", "visual", "show me", "illustrate")
    _explicit_image_req = phase == "tutoring" and any(w in _msg_lower for w in _diagram_kw)

    # ── Render main response ───────────────────────────────────────────────────
    author_map = {"wrapup": "📋 Session Report", "assessment": "🧪 Assessment", "tutoring": "📖 Tutor"}
    author = author_map.get(phase, "UnMask")

    if response and not _explicit_image_req:
        if thinking_msg is not None:
            thinking_msg.content = response
            thinking_msg.author = author
            await thinking_msg.update()
            thinking_msg = None
        else:
            await cl.Message(content=response, author=author).send()
    elif thinking_msg is not None:
        await thinking_msg.remove()

    # ── Show supervisor routing decision in a Step (after response so it renders below) ──
    agent_name = result.get("_last_agent") or "—"
    supervisor_reasoning = result.get("_supervisor_reasoning") or ""
    agent_icon = {"diagnostic": "🩺", "tutor": "📖", "assessment": "🧪", "wrapup": "📋"}.get(agent_name, "🤖")
    async with cl.Step(name="🤖 Supervisor", type="tool", show_input=False) as step:
        step.output = (
            f"**Routed to:** {agent_icon} `{agent_name}`\n\n"
            f"**Reason:** {supervisor_reasoning}\n\n"
            f"*{_phase_progress(phase)}*"
        )

    # ── Force visual hint on explicit diagram request ─────────────────────────
    if _explicit_image_req and not result.get("visual_hint"):
        topic_for_img = result.get("current_topic") or state.get("current_topic") or ""
        result["visual_hint"] = f"__concept__:{topic_for_img}\nHere is a diagram for this topic."
        result["learning_mode"] = "visual"
        state["learning_mode"] = "visual"
        cl.user_session.set("state", result)

    # ── Visual hint card ───────────────────────────────────────────────────────
    await _render_visual_hint(result, phase, suppress_text=_explicit_image_req)

    # ── Assessment feedback ───────────────────────────────────────────────────
    assessment_feedback = result.get("assessment_feedback")
    if assessment_feedback and phase == "assessment":
        await cl.Message(content=assessment_feedback, author="📝 Assessment Feedback").send()

    # ── Wrapup resources + optional survey ────────────────────────────────────
    if phase == "wrapup":
        await _send_followup_resources(result)
        if cl.user_session.get("survey_mode", False):
            duration_min = (time.time() - cl.user_session.get("session_start", time.time())) / 60
            mastery_scores = result.get("mastery_scores", {})
            topics = ", ".join(mastery_scores.keys()) if mastery_scores else "general"
            await run_post_survey(result.get("session_id", state.get("session_id", "")), duration_min, topics)



# ── Rendering helpers ──────────────────────────────────────────────────────────

async def _render_visual_hint(result: dict, phase: str, suppress_text: bool = False) -> None:
    visual_hint = result.get("visual_hint")
    if not visual_hint or phase != "tutoring":
        return

    hint_text = visual_hint
    hint_concept = result.get("current_topic") or ""
    if visual_hint.startswith("__concept__:"):
        first_newline = visual_hint.index("\n")
        hint_concept = visual_hint[len("__concept__:"):first_newline].strip()
        hint_text = visual_hint[first_newline + 1:].strip()

    img_data = get_image_for_topic(hint_concept) or get_image_for_topic(result.get("current_topic") or "")
    concept_label = hint_concept.replace("_", " ").replace(".", " › ").title()
    _sentences = re.split(r'(?<=[.!?])\s+', hint_text.strip())
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

        card_lines = [f"### 🖼️ {concept_label}", "", f"*{img_data['caption']}*", ""]
        if not has_image:
            card_lines += [f"```\n{img_data['diagram']}\n```", ""]
        if _study_notes:
            card_lines += ["**What to look for:**", f"> {_study_notes}", ""]
        card_lines += ["---", "*Study the diagram above, then try the question again.*"]
        await cl.Message(content="\n".join(card_lines), elements=elements, author="🖼️ Visual Aid").send()
    else:
        card_lines = [f"### 📖 Reference — {concept_label}", ""]
        if _study_notes:
            card_lines += ["**What to know:**", f"> {_study_notes}", ""]
        card_lines += ["---", "*Review this, then try the question again.*"]
        await cl.Message(content="\n".join(card_lines), author="🖼️ Visual Aid").send()


async def _render_debug_step(result: dict, phase: str, turn: int) -> None:
    """Show mastery scores, retrieved chunks, and session state in a cl.Step (not a blank message)."""
    mastery = result.get("mastery_scores", {})
    chunks  = result.get("retrieved_chunks", [])
    retrieval_mode = result.get("retrieval_mode", "—")

    if not chunks and not mastery:
        return

    lines = []

    if mastery:
        lines.append("**Mastery Scores**")
        for k, v in sorted(mastery.items()):
            icon = "🟢" if v >= 0.7 else "🟡" if v >= 0.4 else "🔴"
            lines.append(f"  {icon} `{k}`: {v:.2f}")
        lines.append("")

    if chunks:
        lines.append(f"**Retrieval** — PCR `{retrieval_mode}` · {len(chunks)} chunks")
        for i, c in enumerate(chunks[:5], 1):
            flag = "🔒 ANSWER" if c.get("is_answer_chunk") else f"📄 {c.get('chunk_type','ctx').upper()}"
            lines.append(f"  {i}. [{flag}] `{c.get('concept','?')}` — {c['text'][:100]}…")
        lines.append("")

    revisit_info = ""
    if result.get("revisit_scheduled"):
        rt = result.get("revisit_topic", "")
        revisit_info = f" | **Revisit:** {rt.replace('_',' ').replace('.',' › ')}"
    lines.append(
        f"**Session** — phase: `{phase}` · turn: {turn} · "
        f"elapsed: {result.get('elapsed_seconds', 0):.0f}s · "
        f"coverage: {result.get('coverage_ratio', 0):.0%} · "
        f"✓{result.get('consecutive_correct', 0)} ✗{result.get('consecutive_incorrect', 0)}"
        f"{revisit_info}"
    )

    mistake_log = result.get("mistake_log", [])
    if mistake_log:
        lines.append("")
        lines.append("**Mistakes**")
        for m in mistake_log[-5:]:
            lines.append(
                f"  Turn {m['turn']} | {m['topic'].replace('_',' ').replace('.',' › ')}: "
                f"{m.get('misconception','—') or '—'}"
            )

    async with cl.Step(name="📊 Debug Panel", type="tool", show_input=False) as step:
        step.output = "\n".join(lines)


async def _send_followup_resources(result: dict) -> None:
    """Send flashcards and diagram suggestions from SessionSummary after wrapup."""
    internal = result.get("_internal_analysis")
    if not internal:
        return

    flashcards = internal.get("flashcards", [])
    diagrams   = internal.get("diagram_suggestions", [])

    if flashcards:
        lines = ["## 🃏 Your Session Flashcards\n",
                 "*Cover the answer, read the question aloud — then reveal. Repeat daily!*\n", "---\n"]
        for i, fc in enumerate(flashcards, 1):
            if isinstance(fc, dict):
                concept = fc.get("concept", "").replace("_", " ").replace(".", " › ")
                front, back = fc.get("front", ""), fc.get("back", "")
            else:
                concept = getattr(fc, "concept", "").replace("_", " ").replace(".", " › ")
                front, back = getattr(fc, "front", ""), getattr(fc, "back", "")
            lines += [f"**Card {i}** — `{concept}`", f"**Q:** {front}", f"**A:** {back}\n"]
        await cl.Message(content="\n".join(lines), author="🃏 Flashcards").send()

    if diagrams:
        from src.anatomy_images import get_image_for_topic as _get_img
        for d in diagrams:
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
                f"### 🖼️ {d}\n\n📌 *{img['caption']}*\n\n"
                + ("" if has_image else f"```\n{img['diagram']}\n```\n\n")
                + "---\n*Tip: Cover and redraw from memory, then check.*"
            )
            await cl.Message(content=body, elements=elements, author="🖼️ Study Diagram").send()
