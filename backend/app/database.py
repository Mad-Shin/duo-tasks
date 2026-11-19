"""
Database layer for DuoTasks (Lesson 1 of the Backend Coaching Roadmap).

Design principle:
- Locally on your PC: reads/writes a zero-config SQLite file (`duo_tasks.db`).
- In the cloud (Render + Neon/Supabase): set the `DATABASE_URL` environment
  variable to a `postgresql://...` URI and the exact same API code switches
  to persistent cloud PostgreSQL without losing data on container restarts.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SQLITE_PATH = REPO_ROOT / "duo_tasks.db"


def get_database_url() -> str:
    """Return the configured database URI, defaulting to a local SQLite file."""
    return os.environ.get("DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH}").strip()


def get_db_mode() -> str:
    """Return 'postgres' when DATABASE_URL targets PostgreSQL, else 'sqlite'."""
    url = get_database_url().lower()
    if url.startswith("postgres://") or url.startswith("postgresql://"):
        return "postgres"
    return "sqlite"


def _resolve_sqlite_path(db_url: str) -> str:
    """Extract filesystem path from a sqlite:/// URI (supports :memory:)."""
    if db_url.startswith("sqlite:///"):
        raw = db_url[len("sqlite:///") :]
        if raw == ":memory:":
            return ":memory:"
        path = Path(raw)
        if not path.is_absolute():
            path = REPO_ROOT / path
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)
    return str(DEFAULT_SQLITE_PATH)


def placeholder(mode: str | None = None) -> str:
    """Return the parameter placeholder expected by the active SQL driver."""
    active_mode = mode or get_db_mode()
    return "%s" if active_mode == "postgres" else "?"


@contextmanager
def get_connection() -> Iterator[tuple[Any, str]]:
    """
    Yield `(connection, mode)` and ensure clean commit/rollback/close.

    Why a context manager?
    Every HTTP request opens a lightweight transaction, commits on success,
    rolls back on error, and always closes the connection so Windows/SQLite
    file locks never leak.
    """
    db_url = get_database_url()
    mode = get_db_mode()

    if mode == "postgres":
        try:
            import psycopg  # type: ignore
            from psycopg.rows import dict_row  # type: ignore

            conn = psycopg.connect(db_url, row_factory=dict_row)
        except ImportError:
            import psycopg2  # type: ignore
            import psycopg2.extras  # type: ignore

            conn = psycopg2.connect(db_url, cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        sqlite_path = _resolve_sqlite_path(db_url)
        conn = sqlite3.connect(sqlite_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row

    try:
        yield conn, mode
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create the `tasks` table if it does not exist yet."""
    with get_connection() as (conn, mode):
        id_col = "SERIAL PRIMARY KEY" if mode == "postgres" else "INTEGER PRIMARY KEY AUTOINCREMENT"
        completed_col = "BOOLEAN NOT NULL DEFAULT FALSE" if mode == "postgres" else "INTEGER NOT NULL DEFAULT 0"
        recurring_col = "BOOLEAN NOT NULL DEFAULT FALSE" if mode == "postgres" else "INTEGER NOT NULL DEFAULT 0"
        ddl = f"""
        CREATE TABLE IF NOT EXISTS tasks (
            id {id_col},
            title TEXT NOT NULL,
            raw_input TEXT NOT NULL,
            assignee TEXT NOT NULL DEFAULT 'both',
            category TEXT NOT NULL DEFAULT 'inbox',
            priority INTEGER NOT NULL DEFAULT 3,
            due_label TEXT NOT NULL DEFAULT 'today',
            completed {completed_col},
            recurring {recurring_col},
            created_at TEXT NOT NULL
        )
        """
        cur = conn.cursor()
        cur.execute(ddl)
        if mode == "postgres":
            cur.execute(f"ALTER TABLE tasks ADD COLUMN IF NOT EXISTS recurring {recurring_col}")
        else:
            try:
                cur.execute(f"ALTER TABLE tasks ADD COLUMN recurring {recurring_col}")
            except Exception:
                pass
        cur.close()


def row_to_task_dict(row: Any) -> dict[str, Any]:
    """Convert a SQLite Row or Postgres dict row into a normalized Task dict."""
    data = dict(row)
    data["completed"] = bool(data["completed"])
    data["recurring"] = bool(data.get("recurring", False))
    data["priority"] = int(data["priority"])
    data["id"] = int(data["id"])
    return data
