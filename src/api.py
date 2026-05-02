"""FastAPI backend for UnMask anatomy tutor.

Run: uvicorn src.api:app --reload --port 8000
"""
import asyncio
import json
import os
import time
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

import httpx
import yaml
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.graph import graph, make_initial_state
from src.nodes.pedagogy_agent import (
    generate_diagnostic_question,
    get_diagnostic_order,
    get_diagnostic_answer_keywords,
)
from src.agents.supervisor import _pick_start_concept
from src.anatomy_images import get_image_for_topic
from src.nodes.socratic_generator import register_token_queue, unregister_token_queue
from src.session_manager import create_session, get_session, delete_session, save_session
from src.survey import POST_QUIZ, save_results

with open("config.yaml") as f:
    cfg = yaml.safe_load(f)

_DIAGNOSTIC_QUESTIONS = cfg["session"]["diagnostic_questions"]


async def search_anatomy_image(concept: str) -> dict:
    """Search Wikimedia Commons for an anatomy diagram.
    Returns dict with image_url and caption, or empty dict on failure.
    """
    import urllib.request, urllib.parse, json as _json
    try:
        query = f"{concept.replace('_', ' ')} anatomy"
        params = urllib.parse.urlencode({
            "action": "query",
            "list": "search",
            "srnamespace": "6",  # File namespace
            "srsearch": f"{query} filetype:jpg|png",
            "srlimit": "8",
            "format": "json",
        })
        url = f"https://commons.wikimedia.org/w/api.php?{params}"
        loop = asyncio.get_event_loop()

        def _fetch():
            req = urllib.request.Request(url, headers={"User-Agent": "UnMaskTutor/1.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                return _json.loads(r.read())

        data = await loop.run_in_executor(None, _fetch)
        hits = data.get("query", {}).get("search", [])
        if not hits:
            return {}

        # Get image URL for first hit
        title = hits[0]["title"]
        params2 = urllib.parse.urlencode({
            "action": "query",
            "titles": title,
            "prop": "imageinfo",
            "iiprop": "url|mime",
            "format": "json",
        })
        url2 = f"https://commons.wikimedia.org/w/api.php?{params2}"

        def _fetch2():
            req = urllib.request.Request(url2, headers={"User-Agent": "UnMaskTutor/1.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                return _json.loads(r.read())

        data2 = await loop.run_in_executor(None, _fetch2)
        pages = data2.get("query", {}).get("pages", {})
        for page in pages.values():
            info = (page.get("imageinfo") or [{}])[0]
            img_url = info.get("url", "")
            mime = info.get("mime", "")
            if img_url and mime.startswith("image/"):
                # Quick Gemini vision check — verify image is actually relevant anatomy
                try:
                    from openai import OpenAI as _OAI
                    vc = _OAI(
                        api_key=os.environ["OPENAI_API_KEY"],
                        base_url=os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
                    )
                    vresp = vc.chat.completions.create(
                        model=os.getenv("VISION_MODEL", _cfg["llm"].get("vision_model", "google/gemini-2.0-flash-lite")),
                        max_tokens=4,
                        messages=[{"role": "user", "content": [
                            {"type": "image_url", "image_url": {"url": img_url}},
                            {"type": "text", "text": f"Medical anatomy diagram of '{concept}'? YES or NO."},
                        ]}],
                    )
                    verdict = vresp.choices[0].message.content.strip().upper()
                    if verdict.startswith("NO"):
                        continue  # explicitly rejected — try next result
                    # YES or any other response = trust it
                except Exception:
                    pass  # on error, trust Wikimedia result
                caption = title.replace("File:", "").rsplit(".", 1)[0]
                return {"image_url": img_url, "caption": caption}
    except Exception:
        pass
    return {}


app = FastAPI(title="UnMask API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static/anatomy", StaticFiles(directory="public/anatomy"), name="anatomy")


class SetupBody(BaseModel):
    topic: str          # bare key e.g. "dermatomes"
    mode: str = "text"  # "visual" | "text"


class MessageBody(BaseModel):
    content: str


class SurveyBody(BaseModel):
    participant_id: str
    role: str  # "OT Student" | "CS Student" | "Other"
    pre_score: int
    pre_answers: list[str]   # e.g. ["A","C","B","B","D"]
    post_answers: list[str]
    exp_ratings: list[int]   # 5 Likert scores 1-5
    open_feedback: str = ""
    topics_covered: str = ""
    session_duration_min: float = 0.0


@app.post("/api/sessions")
def create_new_session():
    """Create a new session."""
    sess = create_session()
    sess.state = make_initial_state(sess.session_id)
    return {"session_id": sess.session_id}


@app.post("/api/sessions/{session_id}/setup")
def setup_session(session_id: str, body: SetupBody):
    """Initialize session with study focus and learning mode."""
    sess = get_session(session_id)
    if not sess:
        return {"error": "Session not found"}, 404

    study_focus = f"topic:{body.topic}"
    state = sess.state
    state["study_focus"] = study_focus
    state["learning_mode"] = body.mode

    order = get_diagnostic_order(study_focus, n=_DIAGNOSTIC_QUESTIONS)
    sess.diag_order = order
    sess.diag_total = len(order)
    sess.diag_q_index = 0  # Q1 not sent yet — waits for user to click Start
    sess.warmup_done = True
    sess.study_focus = study_focus
    sess.learning_mode = body.mode

    topic_label = body.topic.replace("_", " ").title()
    mode_note = " I'll include diagrams as we go." if body.mode == "visual" else ""

    welcome = (
        f"Welcome! I'm UnMask — your Socratic anatomy tutor for NBCOT prep. "
        f"We'll be focusing on **{topic_label}** today.{mode_note} "
        f"I won't just hand you answers; I'll guide you with questions so the knowledge actually sticks. "
        f"We'll start with a quick {sess.diag_total}-question diagnostic to calibrate where you are — "
        f"no penalties for thinking aloud, no wrong answers."
    )

    save_session(session_id)
    return {
        "welcome_message": welcome,
        "diag_total": sess.diag_total,
        "topic_label": topic_label,
    }


async def stream_message(session_id: str, content: str):
    """Stream responses from the graph execution."""
    sess = get_session(session_id)
    if not sess:
        yield f"data: {json.dumps({'type': 'error', 'message': 'Session not found'})}\n\n"
        return

    # ── "Ready" trigger: user clicked Start — send Q1 with no LLM call ────────
    _READY_TRIGGERS = {"let's start!", "let's start", "ready", "start", "begin", "go", "i'm ready", "im ready"}
    if content.strip().lower().rstrip("→ ").strip() in _READY_TRIGGERS and sess.diag_q_index == 0:
        order = sess.diag_order
        q0 = generate_diagnostic_question(order[0])
        sess.state["current_diagnostic_question"] = q0
        sess.state["current_diagnostic_answer_hint"] = get_diagnostic_answer_keywords(order[0])
        sess.diag_q_index = 1
        save_session(session_id)
        msg = f"Great — let's dive in.\n\n**Q1 of {sess.diag_total}:** {q0}"
        yield f"data: {json.dumps({'type': 'message', 'content': msg, 'author': 'UnMask'})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        return

    # ── "idk" shortcut during diagnostic — skip LLM, use template ─────────────
    _IDK_PHRASES = {"idk", "i don't know", "i dont know", "no idea", "not sure", "don't know", "dont know", "no clue", "pass", "skip"}
    if (sess.state.get("phase", "rapport") == "rapport"
            and content.strip().lower() in _IDK_PHRASES
            and not sess.state.get("diagnostic_complete", False)):
        order = sess.diag_order
        diag_idx = sess.diag_q_index
        _IDK_RESPONSES = [
            "That one's tricky — we'll build it up.",
            "No worries — we'll come back to it.",
            "Fair enough — we'll cover this as we go.",
            "Got it — we'll work through it together.",
        ]
        ack = _IDK_RESPONSES[(diag_idx - 1) % len(_IDK_RESPONSES)]
        if diag_idx < len(order):
            next_q = generate_diagnostic_question(order[diag_idx])
            sess.state["current_diagnostic_question"] = next_q
            sess.state["current_diagnostic_answer_hint"] = get_diagnostic_answer_keywords(order[diag_idx])
            sess.diag_q_index = diag_idx + 1
            # Update mastery scores (no LLM — just keep default prior)
            sess.state["turn_count"] = sess.state.get("turn_count", 0) + 1
            save_session(session_id)
            msg = f"{ack}\n\n**Q{diag_idx + 1} of {sess.diag_total}:** {next_q}"
            yield f"data: {json.dumps({'type': 'message', 'content': msg, 'author': 'UnMask'})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return
        else:
            # Last question answered with idk — complete diagnostic
            sess.state["turn_count"] = sess.state.get("turn_count", 0) + 1
            sess.state["diagnostic_complete"] = True
            save_session(session_id)
            # Fall through to the normal flow which handles the tutoring transition

    state = sess.state
    state["elapsed_seconds"] = time.time() - sess.session_start
    state["student_message"] = content
    # Preserve history — only inject new user turn; graph nodes append assistant reply
    history = state.get("conversation_history", [])
    state["conversation_history"] = history
    prev_phase = state.get("phase", "rapport")

    yield f"data: {json.dumps({'type': 'thinking'})}\n\n"

    config = {"configurable": {"thread_id": sess.session_id}}
    loop = asyncio.get_event_loop()

    # Register streaming queue so socratic_generator can push tokens while running
    token_q = register_token_queue(session_id)

    try:
        # Run graph in background thread while draining the token stream
        invoke_future = loop.run_in_executor(
            None, lambda: graph.invoke(state, config=config)
        )

        # Drain token queue — yield SSE token events as they arrive
        streaming_started = False
        while True:
            try:
                token = token_q.get(timeout=0.05)
                if token is None:
                    break  # end sentinel
                if not streaming_started:
                    streaming_started = True
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
            except Exception:
                # No token yet — check if invoke finished (shouldn't happen before sentinel)
                if invoke_future.done():
                    break
                await asyncio.sleep(0)  # yield control back to event loop

        result = await invoke_future
        sess.state = result
        save_session(session_id)
    except Exception as e:
        unregister_token_queue(session_id)
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        return
    finally:
        unregister_token_queue(session_id)

    phase = result.get("phase", "rapport")
    diagnostic_complete = result.get("diagnostic_complete", False)
    print(f"[DEBUG] invoke1 done: phase={phase} diag_complete={diagnostic_complete} turn={result.get('turn_count')} prev_phase={prev_phase}", flush=True)

    yield f"data: {json.dumps({'type': 'supervisor', 'agent': result.get('_last_agent', ''), 'reasoning': result.get('_supervisor_reasoning', ''), 'phase': phase})}\n\n"

    _PHASE_TRANSITION_MSGS = {
        ("rapport", "tutoring"): "## 🎓 Diagnostic Complete — Starting Tutoring\n\nI've calibrated your starting point. We'll now use the Socratic method — I'll guide you with questions rather than answers. Let's go!",
        ("tutoring", "assessment"): "## 🧪 Tutoring Complete — Moving to Assessment\n\nStrong work! Now let's test your knowledge with a clinical scenario.",
        ("assessment", "wrapup"): "## 📋 Assessment Complete — Generating Your Report\n\nCompiling your performance report...",
        ("tutoring", "wrapup"): "## 📋 Session Time Up — Generating Your Report\n\nTime's up! Compiling your session report...",
    }

    response = result.get("generated_response", "")

    msg_lower = content.lower()
    diagram_kw = ("diagram", "image", "picture", "figure", "visual", "show me", "illustrate")
    explicit_image_req = phase in ("tutoring", "assessment") and any(w in msg_lower for w in diagram_kw)

    if phase == "rapport" and not diagnostic_complete:
        diag_idx = sess.diag_q_index
        order = sess.diag_order
        if diag_idx < len(order):
            next_q = generate_diagnostic_question(order[diag_idx])
            q_block = f"\n\n**Q{diag_idx + 1} of {sess.diag_total}:** {next_q}"
            response = (response + q_block) if response else q_block.strip()
            result["current_diagnostic_question"] = next_q
            result["current_diagnostic_answer_hint"] = get_diagnostic_answer_keywords(
                order[diag_idx]
            )
            sess.diag_q_index = diag_idx + 1
            yield f"data: {json.dumps({'type': 'diagnostic_question', 'question': next_q, 'index': diag_idx, 'total': sess.diag_total})}\n\n"

    author_map = {
        "wrapup": "📋 Session Report",
        "assessment": "🧪 Assessment",
        "tutoring": "📖 Tutor",
    }
    author = author_map.get(phase, "UnMask")
    # In tutoring, a diagram request suppresses the text — but still resolve the streaming placeholder
    if response:
        if explicit_image_req and phase == "tutoring":
            yield f"data: {json.dumps({'type': 'message', 'content': '', 'author': author})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'message', 'content': response, 'author': author})}\n\n"

    # ── Diagnostic → Tutoring transition ─────────────────────────────────────
    # The graph no longer loops back after diagnostic completes (to avoid stacking 4 LLM calls
    # in one invoke). Instead, we detect the transition here and fire a second invoke to generate
    # the first tutoring question, streaming it as a separate message.
    if diagnostic_complete and phase == "rapport":
        start_concept = _pick_start_concept(result)
        trigger = f"Let's work on {start_concept.replace('_', ' ').replace('.', ' ')}"
        print(f"[DEBUG] transitioning to tutoring, concept={start_concept}", flush=True)
        tutoring_state = {
            "phase": "tutoring",
            "last_phase": "rapport",
            "student_message": trigger,
            "current_topic": start_concept,
            "consecutive_incorrect": 0,
            "consecutive_correct": 0,
            "diagnostic_complete": True,
            "elapsed_seconds": result.get("elapsed_seconds", 0.0),
            "mastery_scores": result.get("mastery_scores", {}),
        }
        banner = _PHASE_TRANSITION_MSGS[("rapport", "tutoring")]
        yield f"data: {json.dumps({'type': 'phase_change', 'from': 'rapport', 'to': 'tutoring', 'banner': banner})}\n\n"
        yield f"data: {json.dumps({'type': 'thinking'})}\n\n"
        token_q2 = register_token_queue(session_id)
        try:
            print(f"[DEBUG] firing second invoke for tutoring start", flush=True)
            invoke2_future = loop.run_in_executor(None, lambda: graph.invoke(tutoring_state, config=config))
            while True:
                try:
                    token = token_q2.get(timeout=0.05)
                    if token is None:
                        break
                    yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
                except Exception:
                    if invoke2_future.done():
                        break
                    await asyncio.sleep(0)
            result2 = await invoke2_future
            print(f"[DEBUG] invoke2 done: phase={result2.get('phase')} response={str(result2.get('generated_response',''))[:60]}", flush=True)
            sess.state = result2
            save_session(session_id)
            tut_response = result2.get("generated_response", "")
            if tut_response:
                yield f"data: {json.dumps({'type': 'message', 'content': tut_response, 'author': '📖 Tutor'})}\n\n"
            yield f"data: {json.dumps({'type': 'state_update', 'phase': 'tutoring', 'mastery': result2.get('mastery_scores', {}), 'consecutive_incorrect': 0, 'consecutive_correct': 0, 'diagnostic_complete': True, 'weak_topics': result2.get('weak_topics', []), 'mistake_log': result2.get('mistake_log', []), 'turn_count': result2.get('turn_count', 0)})}\n\n"
        except Exception as e:
            print(f"[DEBUG] invoke2 EXCEPTION: {e}", flush=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            unregister_token_queue(session_id)
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        return

    if prev_phase != phase:
        banner = _PHASE_TRANSITION_MSGS.get((prev_phase, phase), "")
        if banner:
            yield f"data: {json.dumps({'type': 'phase_change', 'from': prev_phase, 'to': phase, 'banner': banner})}\n\n"

    visual_hint = result.get("visual_hint")
    if explicit_image_req and not visual_hint:
        # Use textbook section from internal analysis if available (most specific)
        internal = result.get("_internal_analysis") or {}
        section = internal.get("relevant_textbook_section", "")
        current = result.get("current_topic") or state.get("current_topic") or ""
        sf = (sess.study_focus or "").replace("topic:", "")
        # Pick most specific concept that has a diagram, falling back to study_focus
        from src.anatomy_images import get_image_for_topic as _gif
        topic_for_img = next(
            (t for t in [section, current, sf] if t and _gif(t)),
            sf or current
        )
        visual_hint = f"__concept__:{topic_for_img}\nHere is a diagram for this topic."

    # Clear visual_hint from state after showing so it doesn't repeat on next turn
    if visual_hint:
        sess.state["visual_hint"] = None

    if visual_hint and phase in ("tutoring", "assessment"):
        hint_text = visual_hint
        hint_concept = result.get("current_topic") or ""
        if visual_hint.startswith("__concept__:"):
            nl = visual_hint.index("\n")
            hint_concept = visual_hint[len("__concept__:") : nl].strip()
            hint_text = visual_hint[nl + 1 :].strip()

        # If student explicitly asked for a different diagram, skip local cache for this concept
        _new_kw = ("new", "other", "another", "different", "else", "more")
        want_new = explicit_image_req and any(w in content.lower() for w in _new_kw)
        last_shown = getattr(sess, "last_diagram_concept", None)
        skip_local = want_new and last_shown == hint_concept

        img_data = None
        if not skip_local:
            img_data = get_image_for_topic(hint_concept) or get_image_for_topic(
                result.get("current_topic") or ""
            )
        image_url = ""
        caption = ""
        diagram_text = ""
        if img_data:
            image_file = img_data.get("image_file", "")
            if image_file:
                # Prefer .html version if .png was stored but .html exists
                if image_file.endswith(".png"):
                    html_equiv = image_file.replace(".png", ".html")
                    html_path = f"public/anatomy/{html_equiv}"
                    if os.path.exists(html_path):
                        image_file = html_equiv
                image_url = f"/static/anatomy/{image_file}"
            caption = img_data.get("caption", "")
            diagram_text = img_data.get("diagram", "")

        # Web search: always try when student asks for "new diagram", or when no local file
        if (not image_url or skip_local) and hint_concept:
            web = await search_anatomy_image(hint_concept)
            if web:
                image_url = web.get("image_url", "")
                if not caption:
                    caption = web.get("caption", hint_concept)

        sess.last_diagram_concept = hint_concept

        yield f"data: {json.dumps({'type': 'visual_hint', 'concept': hint_concept, 'image_url': image_url, 'caption': caption, 'diagram_text': diagram_text, 'study_notes': hint_text[:300]})}\n\n"

    yield f"data: {json.dumps({'type': 'state_update', 'phase': phase, 'mastery': result.get('mastery_scores', {}), 'consecutive_incorrect': result.get('consecutive_incorrect', 0), 'consecutive_correct': result.get('consecutive_correct', 0), 'diagnostic_complete': diagnostic_complete, 'weak_topics': result.get('weak_topics', []), 'mistake_log': result.get('mistake_log', []), 'turn_count': result.get('turn_count', 0)})}\n\n"

    # YouTube Resources in wrapup phase
    if phase == "wrapup":
        internal_analysis = result.get("_internal_analysis", {})
        youtube_resources = internal_analysis.get("youtube_resources", [])
        if youtube_resources:
            resources_data = []
            for yt in youtube_resources:
                if isinstance(yt, dict):
                    resources_data.append({
                        "concept": yt.get("concept", ""),
                        "title": yt.get("title", ""),
                        "creator": yt.get("creator", ""),
                        "search_query": yt.get("search_query", ""),
                        "description": yt.get("description", ""),
                    })
                else:
                    resources_data.append({
                        "concept": getattr(yt, "concept", ""),
                        "title": getattr(yt, "title", ""),
                        "creator": getattr(yt, "creator", ""),
                        "search_query": getattr(yt, "search_query", ""),
                        "description": getattr(yt, "description", ""),
                    })
            yield f"data: {json.dumps({'type': 'youtube_resources', 'resources': resources_data})}\n\n"

    yield f"data: {json.dumps({'type': 'done'})}\n\n"


@app.post("/api/sessions/{session_id}/messages")
async def send_message(session_id: str, body: MessageBody):
    """Stream messages from graph execution."""
    return StreamingResponse(
        stream_message(session_id, body.content),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/sessions/{session_id}/state")
def get_session_state(session_id: str):
    """Retrieve full session state."""
    sess = get_session(session_id)
    if not sess:
        return {"error": "Session not found"}, 404
    return sess.state


@app.delete("/api/sessions/{session_id}")
def delete_session_endpoint(session_id: str):
    """Delete a session."""
    delete_session(session_id)
    return {"ok": True}


@app.post("/api/sessions/{session_id}/survey")
def submit_survey(session_id: str, body: SurveyBody):
    """Submit survey responses and save results."""
    # Compute post_score by checking post_answers against POST_QUIZ correct answers
    post_score = sum(
        1 for ans, q in zip(body.post_answers, POST_QUIZ)
        if ans.strip().upper().startswith(q["ans"].upper())
    )

    # Compute learning_gain
    learning_gain = post_score - body.pre_score

    # Build data dict with all fields
    data = {
        "timestamp": datetime.now().isoformat(),
        "participant_id": body.participant_id,
        "role": body.role,
        "session_id": session_id,
        "session_duration_min": round(body.session_duration_min, 1),
        "topics_covered": body.topics_covered,
        "pre_score": body.pre_score,
        "post_score": post_score,
        "learning_gain": learning_gain,
        "pre_answers": ",".join(body.pre_answers),
        "post_answers": ",".join(body.post_answers),
        **{f"exp_q{i}": r for i, r in enumerate(body.exp_ratings, 1)},
        "exp_mean": round(sum(body.exp_ratings) / len(body.exp_ratings), 2) if body.exp_ratings else "",
        "open_feedback": body.open_feedback,
    }

    # Save results
    save_results(data)

    return {
        "ok": True,
        "post_score": post_score,
        "learning_gain": learning_gain,
    }


@app.post("/api/sessions/{session_id}/image")
async def upload_image(session_id: str, file: UploadFile = File(...)):
    """Upload an anatomy image for VLM identification."""
    sess = get_session(session_id)
    if not sess:
        return {"error": "Session not found"}, 404

    try:
        # Read the file and convert to base64
        file_content = await file.read()
        import base64
        image_base64 = base64.b64encode(file_content).decode("utf-8")

        # Determine media type from file extension
        file_ext = file.filename.lower().split(".")[-1] if file.filename else "jpeg"
        media_type_map = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}
        media_type = media_type_map.get(file_ext, "image/jpeg")

        # Call vision model via OpenRouter to identify the structure
        from openai import OpenAI
        vision_client = OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
        )
        vision_model = os.getenv("VISION_MODEL", _cfg["llm"].get("vision_model", "google/gemini-2.0-flash-lite"))

        identification_resp = vision_client.chat.completions.create(
            model=vision_model,
            max_tokens=50,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image_base64}"}},
                    {"type": "text", "text": "A student in an OT anatomy class uploaded this image. Identify the anatomical structure shown (be specific: e.g. 'brachial plexus', 'median nerve', 'rotator cuff'). Reply with ONLY the anatomical name, nothing else."}
                ]
            }]
        )

        identified_structure = identification_resp.choices[0].message.content.strip()

        # Generate a Socratic question
        openai_client = OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
        )
        openai_model = os.getenv("OPENAI_MODEL", "anthropic/claude-opus-4")

        socratic_resp = openai_client.chat.completions.create(
            model=openai_model,
            max_tokens=100,
            messages=[
                {"role": "system", "content": f"You are a Socratic anatomy tutor. The student uploaded an image of {identified_structure}. Ask ONE Socratic question that makes them think about its function or clinical relevance. Do NOT name the structure in your question. End with '?'"},
                {"role": "user", "content": "Ask your Socratic question."},
            ]
        )

        socratic_question = socratic_resp.choices[0].message.content.strip()

        # Look up local anatomy image if it exists
        img_data = get_image_for_topic(identified_structure)
        image_url = ""
        if img_data and img_data.get("image_file"):
            image_url = f"/static/anatomy/{img_data['image_file']}"

        return {
            "concept": identified_structure,
            "socratic_question": socratic_question,
            "image_url": image_url,
        }
    except Exception as e:
        return {"error": str(e)}, 500


@app.get("/api/tts")
async def text_to_speech(text: str, voice: str = "nova"):
    """Neural TTS via OpenAI. Requires OPENAI_TTS_KEY env var (direct OpenAI key, not OpenRouter)."""
    tts_key = os.getenv("OPENAI_TTS_KEY")
    if not tts_key:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "TTS not configured"}, status_code=501)

    from openai import OpenAI
    tts_client = OpenAI(api_key=tts_key)  # always api.openai.com

    # Sanitise text: strip markdown
    import re
    clean = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    clean = re.sub(r'\*(.+?)\*', r'\1', clean)
    clean = re.sub(r'[#_`>~]', '', clean)
    clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', clean)
    clean = clean.strip()[:4096]

    allowed = {"alloy", "echo", "fable", "nova", "onyx", "shimmer"}
    voice = voice if voice in allowed else "nova"

    response = tts_client.audio.speech.create(
        model="tts-1-hd",
        voice=voice,  # type: ignore
        input=clean,
        response_format="mp3",
    )

    return StreamingResponse(
        response.iter_bytes(chunk_size=4096),
        media_type="audio/mpeg",
        headers={"Cache-Control": "no-store"},
    )
