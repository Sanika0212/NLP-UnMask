"""Session store for UnMask API — persists to disk so uvicorn --reload doesn't kill sessions."""
import json
import os
import pickle
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

_sessions: dict[str, "Session"] = {}
_PERSIST_PATH = Path(__file__).parent.parent / ".session_cache.pkl"


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


def _load_from_disk() -> None:
    """Load sessions from disk on startup."""
    if _PERSIST_PATH.exists():
        try:
            with open(_PERSIST_PATH, "rb") as f:
                saved = pickle.load(f)
            # Only restore sessions created in the last 2 hours
            cutoff = time.time() - 7200
            for sid, sess in saved.items():
                if sess.session_start >= cutoff:
                    _sessions[sid] = sess
        except Exception:
            pass  # Corrupt cache — start fresh


def _save_to_disk() -> None:
    try:
        with open(_PERSIST_PATH, "wb") as f:
            pickle.dump(_sessions, f)
    except Exception:
        pass


_load_from_disk()


def create_session() -> Session:
    sess = Session(session_id=str(uuid.uuid4()))
    _sessions[sess.session_id] = sess
    _save_to_disk()
    return sess


def get_session(session_id: str) -> Optional[Session]:
    return _sessions.get(session_id)


def save_session(session_id: str) -> None:
    """Persist after state mutations."""
    if session_id in _sessions:
        _save_to_disk()


def delete_session(session_id: str) -> None:
    _sessions.pop(session_id, None)
    _save_to_disk()
