"""Where investigations are kept: the agent's memory and the list of past cases.

Both live in one git-ignored SQLite file. The agent's memory (`SqliteSaver`) keeps each case's
messages under its own thread id. The list of cases is a small table of our own in the same file,
so the screen never has to parse the memory's internal format.
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from login_investigator.generator import REPO_ROOT

MEMORY_PATH = REPO_ROOT / "memory" / "investigations.sqlite"
MAX_QUESTION_CHARS = 200  # the list shows the first question, shortened

_TABLE = """CREATE TABLE IF NOT EXISTS investigations (
    thread_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    first_question TEXT NOT NULL
)"""


@dataclass(frozen=True)
class Investigation:
    thread_id: str
    started_at: datetime  # when the analyst opened the case, on the real clock, UTC
    first_question: str


def open_memory(path: Path = MEMORY_PATH) -> SqliteSaver:
    """The agent's memory. One connection, shared safely by Streamlit's threads: SqliteSaver
    holds a lock around every use of it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    return SqliteSaver(sqlite3.connect(path, check_same_thread=False))


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute(_TABLE)
    return connection


def start(first_question: str, path: Path = MEMORY_PATH) -> Investigation:
    """Open a new case. Its thread id is random, so ids never collide or reveal anything."""
    case = Investigation(uuid.uuid4().hex, datetime.now(timezone.utc),
                         " ".join(first_question.split())[:MAX_QUESTION_CHARS])
    with _connect(path) as connection:
        connection.execute("INSERT INTO investigations VALUES (?, ?, ?)",
                           (case.thread_id, case.started_at.isoformat(), case.first_question))
    connection.close()
    return case


def list_all(path: Path = MEMORY_PATH) -> list[Investigation]:
    """Every case, newest first."""
    with _connect(path) as connection:
        rows = connection.execute(
            "SELECT thread_id, started_at, first_question FROM investigations "
            "ORDER BY started_at DESC"
        ).fetchall()
    connection.close()
    return [Investigation(thread_id, datetime.fromisoformat(started), question)
            for thread_id, started, question in rows]
