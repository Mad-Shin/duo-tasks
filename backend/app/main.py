"""
DuoTasks FastAPI Server (Lessons 3 & 4 of the Coaching Roadmap).

Combines:
1. REST API endpoints (`GET/POST/PATCH/DELETE /api/tasks`, `POST /api/parse`)
2. Live WebSocket sync (`/ws`) so checking a task on iPhone updates Android instantly
3. Static PWA hosting (`/`) so both phones install the app directly from the browser
"""

from __future__ import annotations

import mimetypes
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import get_connection, get_database_url, get_db_mode, init_db, placeholder, row_to_task_dict
from .models import ParsePreviewOut, ParsePreviewRequest, TaskCreate, TaskOut, TaskUpdate
from .parser import normalize_assignee, normalize_category, parse_quick_add

# Prevent Windows registry MIME-type quirks from breaking JS modules or Service Workers
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/manifest+json", ".webmanifest")
mimetypes.add_type("application/json", ".json")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("text/css", ".css")

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
_INITIALIZED_URLS: set[str] = set()


def ensure_db_ready() -> None:
    """Initialize schema once per configured DATABASE_URL (safe for tests & prod)."""
    url = get_database_url()
    if url not in _INITIALIZED_URLS:
        init_db()
        _INITIALIZED_URLS.add(url)


class ConnectionManager:
    """Tracks connected WebSocket clients (iPhone, Android, desktop) and broadcasts sync events."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, payload: dict[str, Any], exclude: WebSocket | None = None) -> None:
        stale: list[WebSocket] = []
        for connection in list(self.active_connections):
            if exclude is not None and connection is exclude:
                continue
            try:
                await connection.send_json(payload)
            except Exception:
                stale.append(connection)
        for conn in stale:
            self.disconnect(conn)


manager = ConnectionManager()


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_db_ready()
    yield


app = FastAPI(title="DuoTasks API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _fetch_task_by_id(conn: Any, mode: str, task_id: int) -> dict[str, Any] | None:
    ph = placeholder(mode)
    cur = conn.cursor()
    cur.execute(
        f"SELECT id, title, raw_input, assignee, category, priority, due_label, completed, recurring, created_at FROM tasks WHERE id = {ph}",
        (task_id,),
    )
    row = cur.fetchone()
    cur.close()
    return row_to_task_dict(row) if row is not None else None


@app.get("/api/health")
def health_check() -> dict[str, Any]:
    ensure_db_ready()
    return {
        "status": "ok",
        "db_mode": get_db_mode(),
        "connected_devices": len(manager.active_connections),
    }


@app.post("/api/parse", response_model=ParsePreviewOut)
def preview_parse(payload: ParsePreviewRequest) -> ParsePreviewOut:
    """Preview Todoist Quick-Add parsing without persisting anything."""
    parsed = parse_quick_add(payload.raw_input)
    return ParsePreviewOut(**parsed)


@app.get("/api/tasks", response_model=list[TaskOut])
def list_tasks(
    category: Optional[str] = Query(default=None),
    assignee: Optional[str] = Query(default=None),
    completed: Optional[bool] = Query(default=None),
) -> list[dict[str, Any]]:
    ensure_db_ready()
    with get_connection() as (conn, mode):
        ph = placeholder(mode)
        clauses: list[str] = []
        params: list[Any] = []

        if category and category.strip().lower() != "all":
            clauses.append(f"category = {ph}")
            params.append(normalize_category(category))
        if assignee and assignee.strip().lower() != "all":
            clauses.append(f"assignee = {ph}")
            params.append(normalize_assignee(assignee))
        if completed is not None:
            clauses.append(f"completed = {ph}")
            params.append(completed if mode == "postgres" else (1 if completed else 0))

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = (
            "SELECT id, title, raw_input, assignee, category, priority, due_label, completed, recurring, created_at "
            f"FROM tasks {where_sql} ORDER BY completed ASC, priority ASC, id DESC"
        )
        cur = conn.cursor()
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
        cur.close()
        return [row_to_task_dict(r) for r in rows]


@app.post("/api/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskCreate) -> dict[str, Any]:
    ensure_db_ready()
    parsed = parse_quick_add(payload.raw_input)
    title = parsed["title"]
    assignee = normalize_assignee(payload.assignee) if payload.assignee else parsed["assignee"]
    category = normalize_category(payload.category) if payload.category else parsed["category"]
    priority = payload.priority if payload.priority is not None else parsed["priority"]
    due_label = payload.due_label.strip().lower() if payload.due_label else parsed["due_label"]
    recurring_val = payload.recurring if payload.recurring is not None else bool(parsed.get("recurring", False))
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with get_connection() as (conn, mode):
        ph = placeholder(mode)
        cur = conn.cursor()
        values = (
            title,
            payload.raw_input.strip(),
            assignee,
            category,
            priority,
            due_label,
            False if mode == "postgres" else 0,
            bool(recurring_val) if mode == "postgres" else (1 if recurring_val else 0),
            created_at,
        )
        if mode == "postgres":
            cur.execute(
                f"INSERT INTO tasks (title, raw_input, assignee, category, priority, due_label, completed, recurring, created_at) "
                f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}) RETURNING id",
                values,
            )
            inserted = cur.fetchone()
            new_id = int(inserted["id"])
        else:
            cur.execute(
                f"INSERT INTO tasks (title, raw_input, assignee, category, priority, due_label, completed, recurring, created_at) "
                f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
                values,
            )
            new_id = int(cur.lastrowid)
        cur.close()
        task = _fetch_task_by_id(conn, mode, new_id)

    if task is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve created task")

    await manager.broadcast({"event": "sync", "action": "created", "task_id": new_id})
    return task


@app.post("/api/tasks/clear-completed")
async def clear_completed_tasks() -> dict[str, int]:
    ensure_db_ready()
    with get_connection() as (conn, mode):
        ph = placeholder(mode)
        comp_val = True if mode == "postgres" else 1
        cur = conn.cursor()
        cur.execute(f"DELETE FROM tasks WHERE completed = {ph}", (comp_val,))
        cleared_count = int(cur.rowcount if cur.rowcount is not None and cur.rowcount >= 0 else 0)
        cur.close()
    await manager.broadcast({"event": "sync", "action": "cleared_completed", "cleared_count": cleared_count})
    return {"cleared_count": cleared_count}


@app.patch("/api/tasks/{task_id}", response_model=TaskOut)
async def update_task(task_id: int, payload: TaskUpdate) -> dict[str, Any]:
    ensure_db_ready()
    updates = payload.model_dump(exclude_unset=True)

    with get_connection() as (conn, mode):
        existing = _fetch_task_by_id(conn, mode, task_id)
        if existing is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        if not updates:
            return existing

        ph = placeholder(mode)
        assignments: list[str] = []
        params: list[Any] = []

        if "title" in updates and updates["title"] is not None:
            assignments.append(f"title = {ph}")
            params.append(updates["title"].strip())
        if "completed" in updates and updates["completed"] is not None:
            assignments.append(f"completed = {ph}")
            params.append(bool(updates["completed"]) if mode == "postgres" else (1 if updates["completed"] else 0))
        if "assignee" in updates and updates["assignee"] is not None:
            assignments.append(f"assignee = {ph}")
            params.append(normalize_assignee(updates["assignee"]))
        if "category" in updates and updates["category"] is not None:
            assignments.append(f"category = {ph}")
            params.append(normalize_category(updates["category"]))
        if "priority" in updates and updates["priority"] is not None:
            assignments.append(f"priority = {ph}")
            params.append(int(updates["priority"]))
        if "due_label" in updates and updates["due_label"] is not None:
            assignments.append(f"due_label = {ph}")
            params.append(updates["due_label"].strip().lower())
        if "recurring" in updates and updates["recurring"] is not None:
            assignments.append(f"recurring = {ph}")
            params.append(bool(updates["recurring"]) if mode == "postgres" else (1 if updates["recurring"] else 0))

        if assignments:
            params.append(task_id)
            cur = conn.cursor()
            cur.execute(f"UPDATE tasks SET {', '.join(assignments)} WHERE id = {ph}", tuple(params))
            cur.close()

        updated = _fetch_task_by_id(conn, mode, task_id)

    if updated is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    await manager.broadcast({"event": "sync", "action": "updated", "task_id": task_id})
    return updated


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: int) -> dict[str, Any]:
    ensure_db_ready()
    with get_connection() as (conn, mode):
        existing = _fetch_task_by_id(conn, mode, task_id)
        if existing is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        ph = placeholder(mode)
        cur = conn.cursor()
        cur.execute(f"DELETE FROM tasks WHERE id = {ph}", (task_id,))
        cur.close()

    await manager.broadcast({"event": "sync", "action": "deleted", "task_id": task_id})
    return {"deleted": True, "id": task_id}


@app.websocket("/ws")
async def websocket_sync(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    await manager.broadcast(
        {"event": "devices", "connected_devices": len(manager.active_connections)},
        exclude=websocket,
    )
    try:
        while True:
            # Keep connection alive; ignore client pings or echo ack
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast({"event": "devices", "connected_devices": len(manager.active_connections)})
    except Exception:
        manager.disconnect(websocket)
        await manager.broadcast({"event": "devices", "connected_devices": len(manager.active_connections)})


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
