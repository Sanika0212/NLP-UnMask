"""In-memory session store for UnMask API."""
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

_sessions: dict[str, "Session"] = {}


@dataclass
class Session:
    session_id: str
    session_start: float = field(default_factory=time.time)
    state: dict[str, Any] = field(default_factory=dict)
    diag_order: list[str] = field(default_factory=list)
    diag_total: int = 0
    diag_q_index: int = 0
    warmup_done: bool = False
    study_focus: str = ""
    learning_mode: str = "text"


def create_session() -> Session:
    sess = Session(session_id=str(uuid.uuid4()))
    _sessions[sess.session_id] = sess
    return sess


def get_session(session_id: str) -> Optional[Session]:
    return _sessions.get(session_id)


def delete_session(session_id: str) -> None:
    _sessions.pop(session_id, None)
