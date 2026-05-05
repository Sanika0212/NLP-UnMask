"""LangGraph state schema for UnMask tutoring sessions."""
from typing import Literal, Optional, Annotated
from typing_extensions import TypedDict
import operator


Phase = Literal["rapport", "tutoring", "assessment", "wrapup"]
RetrievalMode = Literal["context_only", "prerequisite_first", "full_reveal"]


class TutoringState(TypedDict):
    # Identity
    session_id: str

    # Current turn
    student_message: str
    turn_count: int

    # Session phase
    phase: Phase
    elapsed_seconds: float
    diagnostic_complete: bool

    # Current topic being tutored
    current_topic: Optional[str]

    # Per-concept mastery: concept_id -> P(mastery) in [0, 1]
    mastery_scores: dict[str, float]

    # PCR retrieval mode for this turn (set by retrieval_planner)
    retrieval_mode: RetrievalMode

    # Retrieved chunks (list of dicts with text, concept, is_answer_chunk, etc.)
    retrieved_chunks: list[dict]

    # Generated response — only visible_response.socratic_question + encouragement
    generated_response: str

    # Full structured output (internal_analysis stripped before delivery)
    _internal_analysis: Optional[dict]

    # Conversation history: [{role, content}]
    # Uses operator.add so nodes can append without overwriting
    conversation_history: Annotated[list[dict], operator.add]

    # Adaptive counters
    consecutive_correct: int
    consecutive_incorrect: int
    hints_used: int

    # Coverage ratio: proportion of concept graph nodes with mastery > threshold_high
    coverage_ratio: float

    # Weak topics for proactive revisit (set by pedagogy_agent)
    weak_topics: list[str]

    # Structured mistake log — append-only record of incorrect responses
    # Each entry: {topic, misconception, turn, elapsed_sec}
    mistake_log: Annotated[list[dict], operator.add]

    # Revisit control — set by orchestrator, consumed by generator then cleared
    revisit_scheduled: bool
    revisit_topic: Optional[str]
    _last_revisit_sec: float   # elapsed_sec when last revisit was triggered

    # Phase transition tracking
    last_phase: Phase          # previous phase — used by app.py to detect transitions
    assessment_feedback: Optional[str]  # explicit feedback on student's assessment answer

    # Visual aid — shown as separate UI card when student is struggling
    visual_hint: Optional[str]

    # Onboarding preferences — captured from the first user message before diagnostics
    study_focus: Optional[str]   # "everything" | "revision" | "specific: <topic>"
    learning_mode: Optional[str] # "text" | "visual"

    # Current diagnostic question (during rapport phase) — passed to socratic_generator
    current_diagnostic_question: Optional[str]
    current_diagnostic_answer_hint: Optional[str]  # correct-answer keywords — used by rapport LLM to judge correctness

    # VLM image analysis tracking
    vlm_image_analyzed: bool  # whether a student image was analyzed this turn

    # Simulation flag — set by SimulationPanel to bypass keyword eval and force correct
    force_eval_correct: bool

    # Supervisor agent routing metadata — exposed in UI via cl.Step
    _last_agent: Optional[str]          # which specialist was invoked this turn
    _supervisor_reasoning: Optional[str]  # why the supervisor chose that agent
