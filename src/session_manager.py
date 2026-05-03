"""Session metadata store — SQLite so uvicorn --reload and multi-worker restarts don't kill sessions."""
import sqlite3
import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

_DB_PATH = Path("unmask_sessions.db")

# Bulk LangGraph fields are checkpointed by SqliteSaver — we only store lightweight metadata here.
_SLIM_KEYS = frozenset({
    "phase", "mastery_scores", "weak_topics", "diagnostic_complete",
    "consecutive_correct", "consecutive_incorrect", "current_topic",
    "study_focus", "learning_mode", "turn_count",
})

_SESSION_TTL_SEC = 7200  # 2 hours


@dataclass
class Session:
    session_id: str
    session_start: float = field(default_factory=time.time)
    state: dict[str, Any] = field(default_factory=dict)
    diag_order: list = field(default_factory=list)
    diag_total: int = 0
    diag_q_index: int = 0
    warmup_done: bool = False
    study_focus: str = ""
    learning_mode: str = "text"
    last_diagram_concept: Optional[str] = None


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    c.execute("""CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        session_start REAL,
        data TEXT
    )""")
    c.commit()
    return c


_db = _conn()


def _row_to_session(row) -> "Session":
    data = json.loads(row[2])
    s = Session(session_id=row[0], session_start=row[1])
    s.state         = data.get("state", {})
    s.diag_order    = data.get("diag_order", [])
    s.diag_total    = data.get("diag_total", 0)
    s.diag_q_index  = data.get("diag_q_index", 0)
    s.warmup_done   = data.get("warmup_done", False)
    s.study_focus   = data.get("study_focus", "")
    s.learning_mode = data.get("learning_mode", "text")
    s.last_diagram_concept = data.get("last_diagram_concept")
    return s


def _session_to_data(sess: "Session") -> str:
    # Only persist slim state keys — LangGraph checkpointer owns the full state
    slim_state = {k: v for k, v in (sess.state or {}).items() if k in _SLIM_KEYS}
    return json.dumps({
        "state": slim_state,
        "diag_order": sess.diag_order,
        "diag_total": sess.diag_total,
        "diag_q_index": sess.diag_q_index,
        "warmup_done": sess.warmup_done,
        "study_focus": sess.study_focus,
        "learning_mode": sess.learning_mode,
        "last_diagram_concept": sess.last_diagram_concept,
    })


def _purge_stale() -> None:
    cutoff = time.time() - _SESSION_TTL_SEC
    _db.execute("DELETE FROM sessions WHERE session_start < ?", (cutoff,))
    _db.commit()


# In-memory cache so hot path (get_session) doesn't hit SQLite on every SSE token
_cache: dict[str, "Session"] = {}


def create_session() -> "Session":
    _purge_stale()
    sess = Session(session_id=str(uuid.uuid4()))
    _cache[sess.session_id] = sess
    _db.execute(
        "INSERT INTO sessions (session_id, session_start, data) VALUES (?, ?, ?)",
        (sess.session_id, sess.session_start, _session_to_data(sess)),
    )
    _db.commit()
    return sess


def get_session(session_id: str) -> Optional["Session"]:
    if session_id in _cache:
        return _cache[session_id]
    row = _db.execute(
        "SELECT session_id, session_start, data FROM sessions WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    if not row:
        return None
    sess = _row_to_session(row)
    _cache[session_id] = sess
    return sess


def save_session(session_id: str) -> None:
    sess = _cache.get(session_id)
    if not sess:
        return
    _db.execute(
        "UPDATE sessions SET data = ? WHERE session_id = ?",
        (_session_to_data(sess), session_id),
    )
    _db.commit()


def delete_session(session_id: str) -> None:
    _cache.pop(session_id, None)
    _db.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    _db.commit()
