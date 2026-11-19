"""
Database layer for DuoTasks (Dual SQLite local / PostgreSQL cloud adapter).

Design principle:
- Locally on PC: reads/writes a zero-config SQLite file (`duo_tasks.db`).
- In the cloud (Render + Neon/Supabase): set `DATABASE_URL` to a `postgresql://...`
  URI and the exact same API code switches to persistent cloud PostgreSQL.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SQLITE_PATH = REPO_ROOT / "duo_tasks.db"

DEFAULT_GROCERY_STAPLES: list[tuple[str, str, str, str]] = [
    ("Lait demi-écrémé", "Frais & Laitier", "2L", "🥛"),
    ("Œufs bio", "Frais & Laitier", "x12", "🥚"),
    ("Beurre doux", "Frais & Laitier", "250g", "🧈"),
    ("Yaourts nature", "Frais & Laitier", "x8", "🥣"),
    ("Fromage râpé", "Frais & Laitier", "200g", "🧀"),
    ("Pain / Baguette", "Boulangerie", "x2", "🥖"),
    ("Bananes", "Fruits & Légumes", "x6", "🍌"),
    ("Tomates", "Fruits & Légumes", "500g", "🍅"),
    ("Avocats", "Fruits & Légumes", "x2", "🥑"),
    ("Pommes", "Fruits & Légumes", "1kg", "🍎"),
    ("Oignons & Ail", "Fruits & Légumes", "1 filet", "🧅"),
    ("Blancs de poulet", "Viande & Poisson", "500g", "🍗"),
    ("Saumon frais", "Viande & Poisson", "2 pavés", "🐟"),
    ("Pâtes", "Épicerie", "500g", "🍝"),
    ("Riz basmati", "Épicerie", "1kg", "🍚"),
    ("Café en grains / moulu", "Épicerie", "250g", "☕"),
    ("Huile d'olive", "Épicerie", "1L", "🫒"),
    ("Eau / Pack", "Boissons", "x6", "💧"),
    ("Vin blanc / Apéro", "Boissons", "1 bout.", "🥂"),
    ("Bières artisanales", "Boissons", "x4", "🍺"),
    ("Burrata / Comté", "Frais & Laitier", "x1", "🧀"),
    ("Chocolat noir 70%", "Épicerie", "1 tab.", "🍫"),
    ("Papier toilette", "Maison & Hygiène", "x12", "🧻"),
    ("Lessive liquide", "Maison & Hygiène", "1 bidon", "🧺"),
]


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


def _safe_add_column(cur: Any, mode: str, table: str, column_name: str, column_def: str) -> None:
    """Add a column idempotently for both PostgreSQL and SQLite."""
    if mode == "postgres":
        cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column_name} {column_def}")
    else:
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_def}")
        except Exception:
            pass


def init_db() -> None:
    """Create tables if missing, migrate columns idempotently, and seed staples."""
    with get_connection() as (conn, mode):
        id_col = "SERIAL PRIMARY KEY" if mode == "postgres" else "INTEGER PRIMARY KEY AUTOINCREMENT"
        bool_false = "BOOLEAN NOT NULL DEFAULT FALSE" if mode == "postgres" else "INTEGER NOT NULL DEFAULT 0"

        tasks_ddl = f"""
        CREATE TABLE IF NOT EXISTS tasks (
            id {id_col},
            title TEXT NOT NULL,
            raw_input TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            assignee TEXT NOT NULL DEFAULT 'both',
            category TEXT NOT NULL DEFAULT 'inbox',
            priority INTEGER NOT NULL DEFAULT 3,
            due_label TEXT NOT NULL DEFAULT 'today',
            due_date TEXT NOT NULL DEFAULT '',
            completed {bool_false},
            completed_by TEXT NOT NULL DEFAULT '',
            completed_at TEXT NOT NULL DEFAULT '',
            recurring {bool_false},
            recurrence_rule TEXT NOT NULL DEFAULT 'none',
            quantity TEXT NOT NULL DEFAULT '',
            aisle TEXT NOT NULL DEFAULT '',
            subtasks_json TEXT NOT NULL DEFAULT '[]',
            item_type TEXT NOT NULL DEFAULT 'task',
            event_date TEXT NOT NULL DEFAULT '',
            event_time TEXT NOT NULL DEFAULT '',
            location TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT ''
        )
        """

        staples_ddl = f"""
        CREATE TABLE IF NOT EXISTS grocery_staples (
            id {id_col},
            name TEXT NOT NULL UNIQUE,
            aisle TEXT NOT NULL DEFAULT 'Épicerie',
            default_qty TEXT NOT NULL DEFAULT '',
            emoji TEXT NOT NULL DEFAULT '🛒',
            usage_count INTEGER NOT NULL DEFAULT 0
        )
        """

        activity_ddl = f"""
        CREATE TABLE IF NOT EXISTS activity_log (
            id {id_col},
            actor TEXT NOT NULL DEFAULT 'both',
            action TEXT NOT NULL,
            task_title TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'inbox',
            created_at TEXT NOT NULL
        )
        """

        profile_ddl = """
        CREATE TABLE IF NOT EXISTS couple_profile (
            id INTEGER PRIMARY KEY,
            me_name TEXT NOT NULL DEFAULT 'Valentin',
            me_emoji TEXT NOT NULL DEFAULT '🦊',
            wife_name TEXT NOT NULL DEFAULT 'Lisa',
            wife_emoji TEXT NOT NULL DEFAULT '🌸',
            love_note TEXT NOT NULL DEFAULT 'On fait quoi de beau ce soir ? ✨',
            love_note_author TEXT NOT NULL DEFAULT 'both',
            kudos_count INTEGER NOT NULL DEFAULT 0,
            preset_tasks_json TEXT NOT NULL DEFAULT '["Deep clean salle de bain hebdo", "Deep clean cuisine hebdo"]',
            updated_at TEXT NOT NULL DEFAULT ''
        )
        """

        cur = conn.cursor()
        cur.execute(tasks_ddl)
        cur.execute(staples_ddl)
        cur.execute(activity_ddl)
        cur.execute(profile_ddl)

        # Idempotent migrations for pre-existing databases
        migrations: list[tuple[str, str]] = [
            ("notes", "TEXT NOT NULL DEFAULT ''"),
            ("due_date", "TEXT NOT NULL DEFAULT ''"),
            ("completed_by", "TEXT NOT NULL DEFAULT ''"),
            ("completed_at", "TEXT NOT NULL DEFAULT ''"),
            ("recurring", bool_false),
            ("recurrence_rule", "TEXT NOT NULL DEFAULT 'none'"),
            ("quantity", "TEXT NOT NULL DEFAULT ''"),
            ("aisle", "TEXT NOT NULL DEFAULT ''"),
            ("subtasks_json", "TEXT NOT NULL DEFAULT '[]'"),
            ("item_type", "TEXT NOT NULL DEFAULT 'task'"),
            ("event_date", "TEXT NOT NULL DEFAULT ''"),
            ("event_time", "TEXT NOT NULL DEFAULT ''"),
            ("location", "TEXT NOT NULL DEFAULT ''"),
            ("updated_at", "TEXT NOT NULL DEFAULT ''"),
        ]
        for col_name, col_def in migrations:
            _safe_add_column(cur, mode, "tasks", col_name, col_def)

        _safe_add_column(
            cur,
            mode,
            "couple_profile",
            "preset_tasks_json",
            "TEXT NOT NULL DEFAULT '[\"Deep clean salle de bain hebdo\", \"Deep clean cuisine hebdo\"]'",
        )

        # Seed default grocery staples idempotently
        cur.execute("SELECT name FROM grocery_staples")
        existing_names = {
            str(r["name"] if isinstance(r, dict) or hasattr(r, "keys") else r[0]).lower()
            for r in cur.fetchall()
        }
        ph = placeholder(mode)
        for name, aisle, qty, emoji in DEFAULT_GROCERY_STAPLES:
            if name.lower() not in existing_names:
                cur.execute(
                    f"INSERT INTO grocery_staples (name, aisle, default_qty, emoji, usage_count) "
                    f"VALUES ({ph}, {ph}, {ph}, {ph}, 0)",
                    (name, aisle, qty, emoji),
                )

        # Seed couple_profile row id=1 if missing
        cur.execute("SELECT COUNT(*) AS cnt FROM couple_profile")
        prof_row = cur.fetchone()
        prof_cnt = int(prof_row["cnt"] if isinstance(prof_row, dict) or hasattr(prof_row, "keys") else prof_row[0])
        if prof_cnt == 0:
            cur.execute(
                f"INSERT INTO couple_profile (id, me_name, me_emoji, wife_name, wife_emoji, love_note, love_note_author, kudos_count, updated_at) "
                f"VALUES (1, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, 0, {ph})",
                ("Valentin", "🦊", "Lisa", "🌸", "On fait quoi de beau ce soir ? ✨", "both", ""),
            )
        else:
            cur.execute(
                f"UPDATE couple_profile SET wife_name = {ph} WHERE id = 1 AND wife_name = {ph}",
                ("Lisa", "Chérie"),
            )

        cur.close()


def _parse_subtasks(raw_json: Any) -> list[dict[str, Any]]:
    """Decode subtasks JSON safely into a list of normalized dicts."""
    if isinstance(raw_json, list):
        items = raw_json
    elif isinstance(raw_json, str) and raw_json.strip():
        try:
            loaded = json.loads(raw_json)
            items = loaded if isinstance(loaded, list) else []
        except Exception:
            items = []
    else:
        items = []

    normalized: list[dict[str, Any]] = []
    for idx, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        normalized.append(
            {
                "id": int(item.get("id", idx)),
                "text": text,
                "done": bool(item.get("done", False)),
            }
        )
    return normalized


def row_to_task_dict(row: Any) -> dict[str, Any]:
    """Convert a SQLite Row or Postgres dict row into a normalized Task dict."""
    data = dict(row)
    raw_subtasks = data.pop("subtasks_json", "[]")
    data["id"] = int(data["id"])
    data["priority"] = int(data.get("priority", 3))
    data["completed"] = bool(data.get("completed", False))
    data["recurring"] = bool(data.get("recurring", False))
    data["notes"] = str(data.get("notes") or "")
    data["due_date"] = str(data.get("due_date") or "")
    data["completed_by"] = str(data.get("completed_by") or "")
    data["completed_at"] = str(data.get("completed_at") or "")
    data["recurrence_rule"] = str(data.get("recurrence_rule") or ("daily" if data["recurring"] else "none"))
    data["quantity"] = str(data.get("quantity") or "")
    data["aisle"] = str(data.get("aisle") or "")
    data["item_type"] = str(data.get("item_type") or "task")
    data["event_date"] = str(data.get("event_date") or "")
    data["event_time"] = str(data.get("event_time") or "")
    data["location"] = str(data.get("location") or "")
    data["updated_at"] = str(data.get("updated_at") or "")
    data["subtasks"] = _parse_subtasks(raw_subtasks)
    return data
