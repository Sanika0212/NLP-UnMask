"""
Pilot study survey — pre/post anatomy quiz + experience ratings.

Flow:
  1. Participant opts in at session start
  2. Enters their participant ID and role (OT / CS / Other)
  3. Pre-quiz: 5 MCQ anatomy questions
  4. Regular 15-min tutoring session
  5. Post-quiz: 5 MCQ anatomy questions (same concepts, rephrased)
  6. Experience survey: 5 Likert questions + open feedback
  7. Results saved to survey_results/survey_YYYYMMDD.csv

Deploy:
  Local network : chainlit run app.py --host 0.0.0.0 --port 8000
  Railway/Render: set START_COMMAND=chainlit run app.py --host 0.0.0.0 --port $PORT
"""
from __future__ import annotations

import csv
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

import chainlit as cl

_SAVE_LOCK = threading.Lock()

# ── Quiz questions ─────────────────────────────────────────────────────────────

PRE_QUIZ = [
    {
        "q": "Which nerve is primarily responsible for wrist drop?",
        "opts": ["A. Median nerve", "B. Radial nerve", "C. Ulnar nerve", "D. Axillary nerve"],
        "ans": "B",
    },
    {
        "q": "What spinal cord levels form the brachial plexus?",
        "opts": ["A. C1–C5", "B. C3–C8", "C. C5–T1", "D. C6–T2"],
        "ans": "C",
    },
    {
        "q": "A patient cannot oppose their thumb and has a flat thenar eminence — which nerve is injured?",
        "opts": ["A. Radial nerve", "B. Ulnar nerve", "C. Median nerve", "D. Musculocutaneous nerve"],
        "ans": "C",
    },
    {
        "q": "Which four muscles make up the rotator cuff?",
        "opts": [
            "A. Deltoid, Biceps, Triceps, Supraspinatus",
            "B. Supraspinatus, Infraspinatus, Teres Minor, Subscapularis",
            "C. Supraspinatus, Teres Major, Infraspinatus, Deltoid",
            "D. Biceps, Coracobrachialis, Subscapularis, Supraspinatus",
        ],
        "ans": "B",
    },
    {
        "q": "Which nerve passes through the cubital tunnel at the medial elbow?",
        "opts": ["A. Median nerve", "B. Radial nerve", "C. Musculocutaneous nerve", "D. Ulnar nerve"],
        "ans": "D",
    },
]

POST_QUIZ = [
    {
        "q": "Saturday night palsy (arm draped over a chair back during sleep) compresses which nerve?",
        "opts": ["A. Median nerve", "B. Radial nerve", "C. Ulnar nerve", "D. Axillary nerve"],
        "ans": "B",
    },
    {
        "q": "Erb's palsy (C5–C6) and Klumpke's palsy (C8–T1) are both injuries to which nerve network?",
        "opts": ["A. Lumbar plexus", "B. Cervical plexus", "C. Sacral plexus", "D. Brachial plexus"],
        "ans": "D",
    },
    {
        "q": "Carpal tunnel syndrome compresses a nerve, causing weakness in thumb opposition. Which nerve?",
        "opts": ["A. Radial nerve", "B. Ulnar nerve", "C. Median nerve", "D. Anterior interosseous nerve"],
        "ans": "C",
    },
    {
        "q": "An OT patient cannot externally rotate or abduct the shoulder after a fall. Which muscle group is most likely torn?",
        "opts": [
            "A. Long head of biceps brachii",
            "B. Rotator cuff",
            "C. Deltoid and trapezius",
            "D. Pectoralis major",
        ],
        "ans": "B",
    },
    {
        "q": "Cubitus valgus deformity stretches a nerve at the elbow, causing tingling in the ring and little fingers. Which nerve?",
        "opts": ["A. Median nerve", "B. Radial nerve", "C. Ulnar nerve", "D. Musculocutaneous nerve"],
        "ans": "C",
    },
]

EXPERIENCE_QUESTIONS = [
    "The tutor helped me understand anatomy concepts better.",
    "The Socratic questioning approach was effective for my learning.",
    "The tutor felt natural and easy to interact with (not robotic).",
    "I would use this tool to study for the NBCOT exam.",
    "I would recommend this tool to other OT or anatomy students.",
]

ROLES = ["OT Student", "CS Student", "Other"]
LIKERT_LABELS = ["1 — Strongly Disagree", "2", "3 — Neutral", "4", "5 — Strongly Agree"]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _score(answers: list[str], quiz: list[dict]) -> int:
    return sum(
        1 for a, q in zip(answers, quiz)
        if a.strip().upper().startswith(q["ans"].upper())
    )


def save_results(data: dict) -> str:
    """Append one row to today's CSV. Thread-safe."""
    Path("survey_results").mkdir(exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    filepath = f"survey_results/survey_{date_str}.csv"
    with _SAVE_LOCK:
        is_new = not os.path.exists(filepath)
        with open(filepath, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(data.keys()))
            if is_new:
                writer.writeheader()
            writer.writerow(data)
    return filepath


async def _ask_mcq(idx: int, total: int, question: dict, phase_label: str) -> str:
    """Send one MCQ and wait for the student's button click. Returns chosen option label."""
    actions = [
        cl.Action(name=f"opt_{o[0]}", value=o[0], label=o, payload={})
        for o in question["opts"]
    ]
    res = await cl.AskActionMessage(
        content=f"**{phase_label} — Q{idx}/{total}**\n\n{question['q']}",
        actions=actions,
        author="📋 Survey",
        timeout=300,
    ).send()
    return res["value"] if res else "?"


async def _ask_likert(idx: int, total: int, question: str) -> int:
    """Send one Likert question (1–5) and return the integer rating."""
    actions = [
        cl.Action(name=f"likert_{v}", value=str(v), label=label, payload={})
        for v, label in enumerate(LIKERT_LABELS, 1)
    ]
    res = await cl.AskActionMessage(
        content=f"**Experience Survey — Q{idx}/{total}**\n\n{question}",
        actions=actions,
        author="📋 Survey",
        timeout=300,
    ).send()
    try:
        return int(res["value"]) if res else 3
    except (ValueError, TypeError):
        return 3


# ── Public survey runners ──────────────────────────────────────────────────────

async def run_onboarding() -> tuple[str, str]:
    """
    Ask for participant ID and role.
    Returns (participant_id, role).
    """
    await cl.Message(
        content=(
            "## 📋 Pilot Study — Welcome\n\n"
            "You're about to take part in a short study evaluating an AI anatomy tutor.\n\n"
            "**What to expect:**\n"
            "1. 5-question pre-quiz (~2 min)\n"
            "2. 15-minute tutoring session\n"
            "3. 5-question post-quiz + brief experience survey (~3 min)\n\n"
            "Your responses are anonymous and used only for research."
        ),
        author="📋 Survey",
    ).send()

    pid_res = await cl.AskUserMessage(
        content="Please enter your **participant ID** (provided by the researcher):",
        author="📋 Survey",
        timeout=120,
    ).send()
    participant_id = (pid_res["output"] if pid_res else "unknown").strip() or "unknown"

    role_actions = [
        cl.Action(name=f"role_{r.replace(' ', '_')}", value=r, label=r, payload={})
        for r in ROLES
    ]
    role_res = await cl.AskActionMessage(
        content="What is your background?",
        actions=role_actions,
        author="📋 Survey",
        timeout=120,
    ).send()
    role = role_res["value"] if role_res else "Other"

    cl.user_session.set("survey_participant_id", participant_id)
    cl.user_session.set("survey_role", role)
    return participant_id, role


async def run_pre_quiz() -> int:
    """Run the 5-question pre-quiz. Returns score."""
    await cl.Message(
        content=(
            "## 🧠 Pre-Quiz\n\n"
            "Answer these 5 questions to establish your baseline knowledge. "
            "**Don't worry about getting them right — just do your best.**"
        ),
        author="📋 Survey",
    ).send()

    answers = []
    for i, q in enumerate(PRE_QUIZ, 1):
        ans = await _ask_mcq(i, len(PRE_QUIZ), q, "Pre-Quiz")
        answers.append(ans)
        correct = ans.strip().upper().startswith(q["ans"])
        await cl.Message(
            content="✅ Correct!" if correct else f"❌ The answer was **{q['ans']}**.",
            author="📋 Survey",
        ).send()

    score = _score(answers, PRE_QUIZ)
    cl.user_session.set("survey_pre_answers", answers)
    cl.user_session.set("survey_pre_score", score)

    await cl.Message(
        content=f"**Pre-quiz complete!** You scored {score}/{len(PRE_QUIZ)}.\n\nNow let's start the tutoring session — good luck! 🚀",
        author="📋 Survey",
    ).send()
    return score


async def run_post_survey(session_id: str, session_duration_min: float, topics_covered: str) -> None:
    """Run post-quiz + experience survey, then save all results to CSV."""
    await cl.Message(
        content=(
            "## 📋 Post-Session Survey\n\n"
            "The tutoring session is complete. Please answer these final questions — "
            "they take about 3 minutes and help us evaluate the tool."
        ),
        author="📋 Survey",
    ).send()

    # ── Post-quiz ──────────────────────────────────────────────────────────────
    await cl.Message(
        content="### 🧠 Post-Quiz\n\nSame concepts as before, different questions.",
        author="📋 Survey",
    ).send()

    post_answers = []
    for i, q in enumerate(POST_QUIZ, 1):
        ans = await _ask_mcq(i, len(POST_QUIZ), q, "Post-Quiz")
        post_answers.append(ans)

    post_score = _score(post_answers, POST_QUIZ)
    pre_score = cl.user_session.get("survey_pre_score", 0)
    pre_answers = cl.user_session.get("survey_pre_answers", [])
    gain = post_score - pre_score

    gain_msg = (
        f"📈 You improved by {gain} point{'s' if gain != 1 else ''}!" if gain > 0
        else "➡️ Same score as before — the session may have consolidated what you already knew."
        if gain == 0 else
        f"📉 Score went down by {abs(gain)} — happens sometimes under time pressure, don't worry."
    )
    await cl.Message(
        content=f"**Post-quiz complete!** You scored {post_score}/{len(POST_QUIZ)}. {gain_msg}",
        author="📋 Survey",
    ).send()

    # ── Experience survey ──────────────────────────────────────────────────────
    await cl.Message(
        content="### 💬 Experience Survey\n\nRate each statement from 1 (Strongly Disagree) to 5 (Strongly Agree).",
        author="📋 Survey",
    ).send()

    ratings = []
    for i, question in enumerate(EXPERIENCE_QUESTIONS, 1):
        r = await _ask_likert(i, len(EXPERIENCE_QUESTIONS), question)
        ratings.append(r)

    feedback_res = await cl.AskUserMessage(
        content="**Any other thoughts?** (Optional — press Enter to skip)",
        author="📋 Survey",
        timeout=120,
    ).send()
    open_feedback = (feedback_res["output"] if feedback_res else "").strip()

    # ── Save ───────────────────────────────────────────────────────────────────
    participant_id = cl.user_session.get("survey_participant_id", "unknown")
    role = cl.user_session.get("survey_role", "Other")

    data = {
        "timestamp": datetime.now().isoformat(),
        "participant_id": participant_id,
        "role": role,
        "session_id": session_id,
        "session_duration_min": round(session_duration_min, 1),
        "topics_covered": topics_covered,
        "pre_score": pre_score,
        "post_score": post_score,
        "learning_gain": gain,
        "pre_answers": ",".join(pre_answers),
        "post_answers": ",".join(post_answers),
        **{f"exp_q{i}": r for i, r in enumerate(ratings, 1)},
        "exp_mean": round(sum(ratings) / len(ratings), 2) if ratings else "",
        "open_feedback": open_feedback,
    }

    filepath = save_results(data)

    await cl.Message(
        content=(
            f"## ✅ Thank you!\n\n"
            f"Your responses have been recorded (ID: `{participant_id}`).\n\n"
            f"**Your results:**\n"
            f"- Pre-quiz: {pre_score}/5 → Post-quiz: {post_score}/5 "
            f"({'↑ +' if gain >= 0 else '↓ '}{gain} pts)\n"
            f"- Experience rating: {data['exp_mean']}/5 average\n\n"
            f"Thanks for helping us improve this tool! 🙏"
        ),
        author="📋 Survey",
    ).send()
