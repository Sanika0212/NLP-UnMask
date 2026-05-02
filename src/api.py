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
from fastapi import FastAPI
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
from src.anatomy_images import get_image_for_topic
from src.session_manager import create_session, get_session, delete_session, save_session
from src.survey import POST_QUIZ, save_results

with open("config.yaml") as f:
    cfg = yaml.safe_load(f)

_DIAGNOSTIC_QUESTIONS = cfg["session"]["diagnostic_questions"]


async def search_anatomy_image(concept: str) -> dict:
    """Search DuckDuckGo images for an anatomy diagram, verify with vision LLM.
    Returns dict with image_url and caption, or empty dict on failure.
    """
    try:
        from duckduckgo_search import DDGS
        query = f"{concept} anatomy diagram medical illustration"
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: list(DDGS().images(query, max_results=6, safesearch="moderate"))
        )
        # Prefer Wikipedia/medical sources
        trusted = [r for r in results if any(d in r.get("url", "") for d in
                   ("wikipedia", "wikimedia", "radiopaedia", "kenhub", "teachmeanatomy"))]
        candidates = trusted[:3] or results[:3]
        if not candidates:
            return {}

        # LLM vision check via OpenRouter — ask Claude Haiku to verify image relevance
        from openai import OpenAI
        vision_client = OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
        )
        vision_model = os.getenv("VISION_MODEL", "anthropic/claude-haiku-4-5")
        for r in candidates:
            img_url = r.get("image", "")
            if not img_url:
                continue
            try:
                resp = vision_client.chat.completions.create(
                    model=vision_model,
                    max_tokens=16,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": img_url}},
                            {"type": "text", "text": f"Is this image a medical/anatomy diagram of '{concept}'? Reply YES or NO only."}
                        ]
                    }]
                )
                verdict = resp.choices[0].message.content.strip().upper()
                if verdict.startswith("YES"):
                    return {"image_url": img_url, "caption": r.get("title", concept)}
            except Exception:
                continue
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
    sess.diag_q_index = 1
    sess.warmup_done = True
    sess.study_focus = study_focus
    sess.learning_mode = body.mode

    q0 = generate_diagnostic_question(order[0])
    state["current_diagnostic_question"] = q0
    state["current_diagnostic_answer_hint"] = get_diagnostic_answer_keywords(order[0])

    topic_label = body.topic.replace("_", " ").title()
    mode_note = " I'll include diagrams as we go." if body.mode == "visual" else ""

    welcome = (
        f"Welcome! I'm UnMask — your Socratic anatomy tutor for NBCOT prep. "
        f"We'll be focusing on **{topic_label}** today.{mode_note} "
        f"I won't just hand you answers; instead I'll guide you with questions so the knowledge sticks. "
        f"Let's start with a quick diagnostic to see where you are. "
        f"Take your time — there are no penalties for thinking aloud.\n\n"
        f"**Q1 of {sess.diag_total}:** {q0}"
    )

    save_session(session_id)
    return {
        "first_question": q0,
        "welcome_message": welcome,
        "diag_total": sess.diag_total,
        "topic_label": topic_label,
        "mode_note": mode_note,
    }


async def stream_message(session_id: str, content: str):
    """Stream responses from the graph execution."""
    sess = get_session(session_id)
    if not sess:
        yield f"data: {json.dumps({'type': 'error', 'message': 'Session not found'})}\n\n"
        return

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

    try:
        result = await loop.run_in_executor(
            None, lambda: graph.invoke(state, config=config)
        )
        sess.state = result
        save_session(session_id)
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        return

    phase = result.get("phase", "rapport")
    diagnostic_complete = result.get("diagnostic_complete", False)

    yield f"data: {json.dumps({'type': 'supervisor', 'agent': result.get('_last_agent', ''), 'reasoning': result.get('_supervisor_reasoning', ''), 'phase': phase})}\n\n"

    _PHASE_TRANSITION_MSGS = {
        ("rapport", "tutoring"): "## 🎓 Diagnostic Complete — Starting Tutoring\n\nI've calibrated your starting point. We'll now use the Socratic method — I'll guide you with questions rather than answers. Let's go!",
        ("tutoring", "assessment"): "## 🧪 Tutoring Complete — Moving to Assessment\n\nStrong work! Now let's test your knowledge with a clinical scenario.",
        ("assessment", "wrapup"): "## 📋 Assessment Complete — Generating Your Report\n\nCompiling your performance report...",
        ("tutoring", "wrapup"): "## 📋 Session Time Up — Generating Your Report\n\nTime's up! Compiling your session report...",
    }

    if prev_phase != phase:
        banner = _PHASE_TRANSITION_MSGS.get((prev_phase, phase), "")
        if banner:
            yield f"data: {json.dumps({'type': 'phase_change', 'from': prev_phase, 'to': phase, 'banner': banner})}\n\n"

    response = result.get("generated_response", "")

    msg_lower = content.lower()
    diagram_kw = ("diagram", "image", "picture", "figure", "visual", "show me", "illustrate")
    explicit_image_req = phase == "tutoring" and any(w in msg_lower for w in diagram_kw)

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

    if response and not explicit_image_req:
        author_map = {
            "wrapup": "📋 Session Report",
            "assessment": "🧪 Assessment",
            "tutoring": "📖 Tutor",
        }
        author = author_map.get(phase, "UnMask")
        yield f"data: {json.dumps({'type': 'message', 'content': response, 'author': author})}\n\n"

    visual_hint = result.get("visual_hint")
    if explicit_image_req and not visual_hint:
        topic_for_img = result.get("current_topic") or state.get("current_topic") or ""
        visual_hint = f"__concept__:{topic_for_img}\nHere is a diagram for this topic."

    if visual_hint and phase == "tutoring":
        hint_text = visual_hint
        hint_concept = result.get("current_topic") or ""
        if visual_hint.startswith("__concept__:"):
            nl = visual_hint.index("\n")
            hint_concept = visual_hint[len("__concept__:") : nl].strip()
            hint_text = visual_hint[nl + 1 :].strip()

        img_data = get_image_for_topic(hint_concept) or get_image_for_topic(
            result.get("current_topic") or ""
        )
        image_url = ""
        caption = ""
        diagram_text = ""
        if img_data:
            image_file = img_data.get("image_file", "")
            if image_file:
                image_url = f"/static/anatomy/{image_file}"
            caption = img_data.get("caption", "")
            diagram_text = img_data.get("diagram", "")

        # Web search fallback: if no local file, search for an anatomical image
        if not image_url and hint_concept:
            web = await search_anatomy_image(hint_concept)
            if web:
                image_url = web.get("image_url", "")
                if not caption:
                    caption = web.get("caption", hint_concept)

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
