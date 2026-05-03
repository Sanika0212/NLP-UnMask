"""
LangGraph state machine for UnMask.

Graph topology:
  START
    └─► supervisor
          ├─► [diagnostic/wrapup] socratic_generator
          └─► [tutor/assessment]  retrieval_planner → socratic_generator
                                                           └─► pedagogy_agent
                                                                    ├─► supervisor  (loopback: diagnostic→tutoring)
                                                                    └─► END
"""
import uuid
from typing import Literal

from langgraph.graph import StateGraph, START, END
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

from src.state import TutoringState
from src.agents.supervisor import supervisor_agent
from src.nodes.retrieval_planner import retrieval_planner
from src.nodes.socratic_generator import socratic_generator
from src.nodes.pedagogy_agent import pedagogy_agent


def _route_by_supervisor(state: TutoringState) -> Literal["retrieval_planner", "socratic_generator"]:
    """Conditional edge: route to retrieval for tutor/assessment, direct to generator for diagnostic/wrapup."""
    agent = state.get("_last_agent", "tutor")
    if agent in ("diagnostic", "wrapup"):
        return "socratic_generator"
    return "retrieval_planner"


def _after_pedagogy(state: TutoringState) -> Literal["supervisor", "__end__"]:
    return END


def build_graph() -> StateGraph:
    builder = StateGraph(TutoringState)

    builder.add_node("supervisor",        supervisor_agent)
    builder.add_node("retrieval_planner", retrieval_planner)
    builder.add_node("socratic_generator", socratic_generator)
    builder.add_node("pedagogy_agent",    pedagogy_agent)

    builder.add_edge(START, "supervisor")

    builder.add_conditional_edges(
        "supervisor",
        _route_by_supervisor,
        {
            "retrieval_planner":  "retrieval_planner",
            "socratic_generator": "socratic_generator",
        },
    )

    builder.add_edge("retrieval_planner", "socratic_generator")
    builder.add_edge("socratic_generator", "pedagogy_agent")

    builder.add_conditional_edges(
        "pedagogy_agent",
        _after_pedagogy,
        {
            "supervisor": "supervisor",
            END: END,
        },
    )

    return builder


import os as _os
_DB_PATH = str(_os.path.join(_os.getenv("DATA_DIR", "."), "unmask_sessions.db"))
_db_conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
checkpointer = SqliteSaver(_db_conn)
graph = build_graph().compile(checkpointer=checkpointer)


def make_initial_state(session_id: str | None = None) -> TutoringState:
    """Create a fresh session state."""
    import yaml
    with open("config.yaml") as f:
        cfg = yaml.safe_load(f)

    return TutoringState(
        session_id=session_id or str(uuid.uuid4()),
        student_message="",
        turn_count=0,
        phase="rapport",
        elapsed_seconds=0.0,
        diagnostic_complete=False,
        current_topic=None,
        mastery_scores={},
        retrieval_mode="context_only",
        retrieved_chunks=[],
        generated_response="",
        _internal_analysis=None,
        conversation_history=[],
        consecutive_correct=0,
        consecutive_incorrect=0,
        hints_used=0,
        coverage_ratio=0.0,
        weak_topics=[],
        mistake_log=[],
        revisit_scheduled=False,
        revisit_topic=None,
        _last_revisit_sec=0.0,
        last_phase="rapport",
        assessment_feedback=None,
        visual_hint=None,
        study_focus=None,
        learning_mode=None,
        current_diagnostic_question=None,
        current_diagnostic_answer_hint=None,
        vlm_image_analyzed=False,
        _last_agent=None,
        _supervisor_reasoning=None,
    )
