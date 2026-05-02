"""
Supervisor agent — LLM-based session router with rule-based fallback.

Routes each turn to one of four specialist pipelines:
  diagnostic  → rapport-phase Q&A (existing socratic_generator rapport path)
  tutor       → retrieval_planner + socratic_generator (tutoring path)
  assessment  → retrieval_planner + socratic_generator (assessment path)
  wrapup      → socratic_generator (wrapup/summary path)

The supervisor also handles the diagnostic→tutoring transition inline, eliminating
the double-invoke hack that previously lived in app.py.
"""
from __future__ import annotations

import os
import time
from typing import Literal, Optional

import yaml
from pydantic import BaseModel

from src.state import TutoringState

with open("config.yaml") as f:
    _cfg = yaml.safe_load(f)

_S = _cfg["session"]
_M = _cfg["mastery"]

AgentName = Literal["diagnostic", "tutor", "assessment", "wrapup"]

_QUIT_PHRASES = (
    "i'm done", "im done", "done for today", "i am done",
    "that's all for today", "thats all for today",
    "i want to stop", "want to stop", "end session",
    "stop for now", "i'm finished", "im finished",
    "enough for today", "i'll stop here", "ill stop here",
    "goodbye", "bye for now", "see you later",
)

_PHASE_TO_AGENT: dict[str, AgentName] = {
    "rapport":    "diagnostic",
    "tutoring":   "tutor",
    "assessment": "assessment",
    "wrapup":     "wrapup",
}


class SupervisorDecision(BaseModel):
    next_agent: AgentName
    new_phase: Literal["rapport", "tutoring", "assessment", "wrapup"]
    reasoning: str


def _rule_based_decision(state: TutoringState) -> SupervisorDecision:
    """Pure-Python rule engine — mirrors old orchestrator.py logic."""
    phase = state["phase"]
    elapsed = state.get("elapsed_seconds", 0.0)
    turn = state.get("turn_count", 0)
    diagnostic_complete = state.get("diagnostic_complete", False)
    consecutive_correct = state.get("consecutive_correct", 0)
    msg_lower = (state.get("student_message") or "").lower()

    # Quit intent
    if phase not in ("wrapup",) and any(q in msg_lower for q in _QUIT_PHRASES):
        return SupervisorDecision(
            next_agent="wrapup", new_phase="wrapup",
            reasoning="Student signalled they want to end the session.",
        )

    # Time ceiling — wrapup
    if turn >= 2 and elapsed >= _S["wrapup_cutoff_sec"] and phase != "wrapup":
        return SupervisorDecision(
            next_agent="wrapup", new_phase="wrapup",
            reasoning=f"Session time limit reached ({elapsed:.0f}s ≥ {_S['wrapup_cutoff_sec']}s). Generating summary.",
        )

    # Time ceiling — assessment
    if turn >= 2 and elapsed >= _S["assessment_cutoff_sec"] and phase not in ("assessment", "wrapup"):
        return SupervisorDecision(
            next_agent="assessment", new_phase="assessment",
            reasoning=f"Tutoring time window closed ({elapsed:.0f}s). Moving to clinical assessment.",
        )

    # Rapport → tutoring (diagnostic complete)
    if phase == "rapport" and diagnostic_complete:
        return SupervisorDecision(
            next_agent="tutor", new_phase="tutoring",
            reasoning="Diagnostic complete — mastery priors initialised. Starting Socratic tutoring.",
        )

    # Rapport stays in rapport
    if phase == "rapport":
        return SupervisorDecision(
            next_agent="diagnostic", new_phase="rapport",
            reasoning=f"Diagnostic phase in progress (turn {turn}).",
        )

    # Tutoring → assessment on mastery milestone
    if phase == "tutoring" and turn >= 3 and consecutive_correct >= max(1, _M["consecutive_correct_for_advance"]):
        return SupervisorDecision(
            next_agent="assessment", new_phase="assessment",
            reasoning=f"Student hit {consecutive_correct} consecutive correct answers. Advancing to assessment.",
        )

    # Stay in current phase
    agent = _PHASE_TO_AGENT.get(phase, "tutor")
    return SupervisorDecision(
        next_agent=agent, new_phase=phase,
        reasoning=f"Continuing {phase} phase (turn {turn}, elapsed {elapsed:.0f}s).",
    )


def _llm_decision(state: TutoringState) -> Optional[SupervisorDecision]:
    """LLM-based routing for nuanced transitions. Returns None on failure."""
    import json
    from openai import OpenAI

    phase = state["phase"]
    turn = state.get("turn_count", 0)

    # All routing decisions are handled deterministically by _rule_based_decision.
    # The LLM adds only a human-readable reasoning string — not worth 1-3s per turn.
    return None

    client = OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.getenv("OPENAI_BASE_URL"),
        timeout=15.0,
    )

    elapsed = state.get("elapsed_seconds", 0.0)
    diagnostic_complete = state.get("diagnostic_complete", False)
    mastery = state.get("mastery_scores", {})
    consecutive_correct = state.get("consecutive_correct", 0)
    consecutive_incorrect = state.get("consecutive_incorrect", 0)

    prompt = f"""\
You are a session supervisor for an OT anatomy tutoring app. Decide the next routing step.

SESSION STATE:
- phase: {phase}
- turn: {turn}
- elapsed: {elapsed:.0f}s (wrapup at {_S['wrapup_cutoff_sec']}s, assessment at {_S['assessment_cutoff_sec']}s)
- diagnostic_complete: {diagnostic_complete}
- consecutive_correct: {consecutive_correct}
- consecutive_incorrect: {consecutive_incorrect}
- mastery_scores: {json.dumps({k: round(v, 2) for k, v in mastery.items()}, indent=2) if mastery else '{}'}
- student_message: "{(state.get('student_message') or '')[:200]}"

RULES:
- Stay in diagnostic until diagnostic_complete=True
- Advance to tutoring when diagnostic_complete=True (from rapport)
- Advance to assessment when {_M['consecutive_correct_for_advance']}+ consecutive correct in tutoring
- Advance to wrapup when elapsed >= {_S['wrapup_cutoff_sec']}s OR student signals quit
- The reasoning field is shown to the student in the UI — make it a brief, human-readable sentence

Respond ONLY with a SupervisorDecision JSON object."""

    try:
        resp = client.beta.chat.completions.parse(
            model=os.getenv("UTILITY_MODEL", _cfg["llm"]["utility_model"]),
            messages=[{"role": "user", "content": prompt}],
            response_format=SupervisorDecision,
            temperature=0,
        )
        return resp.choices[0].message.parsed
    except Exception:
        return None


def _pick_start_concept(state: TutoringState) -> str:
    """Pick the weakest concept within the student's chosen topic for first tutoring Q."""
    from src.nodes.pedagogy_agent import _TOPIC_BANK_MAP, _DIAGNOSTIC_BANK  # type: ignore[attr-defined]

    sf = state.get("study_focus") or ""
    chosen_topic = sf.replace("topic:", "").strip() if sf.startswith("topic:") else ""
    mastery = state.get("mastery_scores", {})

    topic_concepts = [
        _DIAGNOSTIC_BANK[i]["concept"]
        for i in _TOPIC_BANK_MAP.get(chosen_topic, [])
    ]
    if topic_concepts:
        return min(topic_concepts, key=lambda c: mastery.get(c, 0.0))
    if mastery:
        return min(mastery, key=lambda k: mastery[k])
    return chosen_topic or "nerve_injuries.radial"


def supervisor_agent(state: TutoringState) -> dict:
    """
    LLM-based supervisor with rule-based fallback.
    Returns state updates: phase, _last_agent, _supervisor_reasoning.
    Also handles the diagnostic→tutoring transition (picks start concept, sets trigger message).
    """
    prev_phase = state["phase"]

    # Rule-based decision (always computed — used as fallback and as ground truth for time limits)
    rule = _rule_based_decision(state)

    # LLM decision (adds human-readable reasoning; validates against rule for safety)
    llm = _llm_decision(state)

    # Use LLM decision if it matches the rule's agent, else fall back to rule
    if llm is not None and llm.next_agent == rule.next_agent:
        decision = llm
    else:
        decision = rule

    result: dict = {
        "phase": decision.new_phase,
        "last_phase": prev_phase,
        "_last_agent": decision.next_agent,
        "_supervisor_reasoning": decision.reasoning,
    }

    # When transitioning rapport → tutoring (loopback after diagnostic completion),
    # inject the synthetic trigger message so socratic_generator knows what topic to open.
    if prev_phase == "rapport" and decision.new_phase == "tutoring":
        start_concept = _pick_start_concept(state)
        trigger = f"Let's work on {start_concept.replace('_', ' ').replace('.', ' ')}"
        result.update({
            "student_message": trigger,
            "current_topic": start_concept,
            "consecutive_incorrect": 0,
            "consecutive_correct": 0,
        })

    # Proactive revisit scheduling (previously in orchestrator.py)
    if decision.new_phase == "tutoring":
        revisit_after = _S.get("revisit_after_sec", 480)
        revisit_cooldown = _S.get("revisit_cooldown_sec", 180)
        last_revisit = state.get("_last_revisit_sec", 0.0)
        weak_topics = state.get("weak_topics", [])
        already_scheduled = state.get("revisit_scheduled", False)
        elapsed = state.get("elapsed_seconds", 0.0)

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
            result.update({
                "revisit_scheduled": True,
                "revisit_topic": revisit_topic,
                "current_topic": revisit_topic,
                "_last_revisit_sec": elapsed,
                "_supervisor_reasoning": (
                    f"Proactive revisit: steering back to '{revisit_topic.replace('_', ' ')}' "
                    f"(mastery {mastery_scores.get(revisit_topic, 0):.0%})."
                ),
            })

    return result
