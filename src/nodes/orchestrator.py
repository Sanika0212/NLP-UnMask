"""
Orchestrator node — pure Python, zero LLM calls.

Determines phase transitions and next routing target based on session state.
Implements the state machine from the UnMask v4 spec.
"""
import time
from typing import Literal

import yaml

from src.state import TutoringState, Phase

with open("config.yaml") as f:
    _cfg = yaml.safe_load(f)

_S = _cfg["session"]
_M = _cfg["mastery"]


_QUIT_PHRASES = (
    "i'm done", "im done", "done for today", "i am done",
    "that's all for today", "thats all for today",
    "i want to stop", "want to stop", "end session",
    "stop for now", "i'm finished", "im finished",
    "enough for today", "i'll stop here", "ill stop here",
    "goodbye", "bye for now", "see you later",
)


def orchestrator(state: TutoringState) -> dict:
    """
    Route the session to the next phase.
    Returns partial state updates only (phase, next routing signal).
    """
    phase = state["phase"]
    elapsed = state["elapsed_seconds"]
    consecutive_correct = state["consecutive_correct"]
    consecutive_incorrect = state["consecutive_incorrect"]
    coverage = state["coverage_ratio"]
    diagnostic_complete = state["diagnostic_complete"]

    def _transition(new_phase: str, extra: dict | None = None) -> dict:
        """Return a phase transition dict, setting last_phase for app.py detection."""
        result = {"phase": new_phase, "last_phase": phase}
        if extra:
            result.update(extra)
        return result

    turn = state.get("turn_count", 0)

    # ── Quit intent: student wants to end the session ────────────────────────
    msg_lower = (state.get("student_message") or "").lower()
    if phase not in ("wrapup",) and any(q in msg_lower for q in _QUIT_PHRASES):
        return _transition("wrapup")

    # ── Time-based ceiling overrides (highest priority) ──────────────────────
    # Guard: never fire time transitions on the very first turns — prevents
    # stale elapsed_seconds from killing the session before it starts.
    if turn >= 2 and elapsed >= _S["wrapup_cutoff_sec"] and phase not in ("wrapup",):
        return _transition("wrapup")

    if turn >= 2 and elapsed >= _S["assessment_cutoff_sec"] and phase not in ("assessment", "wrapup"):
        return _transition("assessment")

    # ── Event-based transitions ───────────────────────────────────────────────
    if phase == "rapport":
        if diagnostic_complete:
            return _transition("tutoring")
        # Stay in rapport until diagnostic is done

    elif phase == "tutoring":
        # Advance if student has demonstrated sufficient mastery across topics
        if turn >= 3 and consecutive_correct >= max(1, _M["consecutive_correct_for_advance"]):
            return _transition("assessment", {"consecutive_correct": 0})

        # Proactive revisit: after revisit_after_sec, steer back to weakest topic
        revisit_after = _S.get("revisit_after_sec", 480)
        revisit_cooldown = _S.get("revisit_cooldown_sec", 180)
        last_revisit = state.get("_last_revisit_sec", 0.0)
        weak_topics = state.get("weak_topics", [])
        already_scheduled = state.get("revisit_scheduled", False)

        if (
            elapsed >= revisit_after
            and weak_topics
            and not already_scheduled
            and (elapsed - last_revisit) >= revisit_cooldown
        ):
            mastery_scores = state.get("mastery_scores", {})
            revisit_topic = min(
                weak_topics,
                key=lambda t: mastery_scores.get(t, _M["default_prior"])
            )
            return {
                "phase": phase,
                "revisit_scheduled": True,
                "revisit_topic": revisit_topic,
                "current_topic": revisit_topic,
                "_last_revisit_sec": elapsed,
            }

    elif phase == "assessment":
        # Assessment always runs to completion (wrapup triggered by time ceiling)
        pass

    # No phase change — return current phase unchanged
    return {"phase": phase, "last_phase": phase}


def should_retrieve(state: TutoringState) -> Literal["retrieval_planner", "socratic_generator"]:
    """Conditional edge: skip retrieval for rapport/wrapup phases."""
    if state["phase"] in ("rapport", "wrapup"):
        return "socratic_generator"
    return "retrieval_planner"
