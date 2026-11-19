"""
DuoTasks FastAPI Server — Full Couple Productivity, Supermarket & Routines Backend.
"""

from __future__ import annotations

import hmac
import json
import mimetypes
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from .database import get_connection, get_database_url, get_db_mode, init_db, placeholder, row_to_task_dict
from .models import (
    BudgetOverviewOut,
    BudgetRefillRequest,
    BudgetSettingsUpdate,
    BudgetTransactionOut,
    CoupleProfileOut,
    CoupleProfileUpdate,
    CoupleStatsOut,
    GroceryStapleCreate,
    GroceryStapleOut,
    KudosRequest,
    ParsePreviewOut,
    ParsePreviewRequest,
    RevolutWebhookPayload,
    RoutinePackOut,
    SubtaskCreate,
    SubtaskUpdate,
    TaskCreate,
    TaskOut,
    TaskUpdate,
)
from .parser import compute_due_date, infer_aisle, normalize_assignee, normalize_category, parse_quick_add
from .revolut_parser import compute_dedupe_key, parse_revolut_notification

# Prevent Windows registry MIME-type quirks from breaking JS modules or Service Workers
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/manifest+json", ".webmanifest")
mimetypes.add_type("application/json", ".json")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("text/css", ".css")

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
_INITIALIZED_URLS: set[str] = set()

TASK_COLUMNS = (
    "id, title, raw_input, notes, assignee, category, priority, due_label, due_date, "
    "completed, completed_by, completed_at, recurring, recurrence_rule, quantity, aisle, "
    "subtasks_json, item_type, event_date, event_time, location, created_at, updated_at"
)

ROUTINE_PACKS: list[dict[str, Any]] = [
    {
        "id": "courses-essentielles",
        "name": "Courses Essentielles",
        "description": "Le fond de frigo et petit-déjeuner pour la semaine.",
        "emoji": "🛒",
        "tasks": [
            "Lait demi-écrémé 2L @both #courses !2",
            "Œufs bio x12 @both #courses !2",
            "Pain frais x2 @both #courses !2",
            "Bananes x6 @both #courses !3",
            "Yaourts nature x8 @both #courses !3",
            "Café en grains 250g @both #courses !2",
        ],
    },
    {
        "id": "menage-weekend",
        "name": "Ménage Week-end",
        "description": "Répartition claire pour boucler l'appart en 1h.",
        "emoji": "🧹",
        "tasks": [
            "Passer l'aspirateur et la serpillière @me #maison weekend !2",
            "Nettoyer salle de bain et miroirs @wife #maison weekend !2",
            "Changer les draps & lancer lessive @both #maison weekend !2",
            "Trier les poubelles et verre @me #maison weekend !3",
        ],
    },
    {
        "id": "routine-quotidienne",
        "name": "Routine Quotidienne Couple",
        "description": "Petits réflexes de fin de journée pour rester sereins.",
        "emoji": "☀️",
        "tasks": [
            "Vider le lave-vaisselle tous les jours @both #daily !3",
            "Ranger plan de travail cuisine tous les jours @both #daily !3",
            "Vérifier agenda du lendemain tous les jours @both #daily !3",
        ],
    },
    {
        "id": "preparatifs-voyage",
        "name": "Départ Week-end / Voyage",
        "description": "Checklist express avant de fermer la porte.",
        "emoji": "🧳",
        "tasks": [
            "Vérifier billets, cartes d'identité et chargeurs @both #weekend !1",
            "Arroser les plantes avant le départ @wife #maison !2",
            "Vider frigo périssable et poubelles @me #maison !2",
            "Fermer volets et couper eau / gaz @both #maison !1",
        ],
    },
    {
        "id": "date-night-apero",
        "name": "Soirée Date Night & Apéro",
        "description": "Le kit couple pour déconnecter à deux après la semaine.",
        "emoji": "🥂",
        "tasks": [
            "Prendre une bonne bouteille de vin et burrata @me #courses !2",
            "Choisir le film ou réserver le petit resto @wife #date !2",
            "Mettre la playlist & allumer les bougies @both #date !3",
            "Zéro écran pro après 20h @both #date !1",
        ],
    },
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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


app = FastAPI(title="DuoTasks API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _bool_param(val: bool, mode: str) -> Any:
    return bool(val) if mode == "postgres" else (1 if val else 0)


def _fetch_task_by_id(conn: Any, mode: str, task_id: int) -> dict[str, Any] | None:
    ph = placeholder(mode)
    cur = conn.cursor()
    cur.execute(f"SELECT {TASK_COLUMNS} FROM tasks WHERE id = {ph}", (task_id,))
    row = cur.fetchone()
    cur.close()
    return row_to_task_dict(row) if row is not None else None


def _log_activity(conn: Any, mode: str, actor: str, action: str, task_title: str, category: str) -> None:
    ph = placeholder(mode)
    cur = conn.cursor()
    cur.execute(
        f"INSERT INTO activity_log (actor, action, task_title, category, created_at) VALUES ({ph}, {ph}, {ph}, {ph}, {ph})",
        (actor or "both", action, task_title[:120], category or "inbox", _utc_now()),
    )
    cur.close()


def _insert_task_row(
    conn: Any,
    mode: str,
    *,
    title: str,
    raw_input: str,
    notes: str,
    assignee: str,
    category: str,
    priority: int,
    due_label: str,
    due_date: str,
    recurring: bool,
    recurrence_rule: str,
    quantity: str,
    aisle: str,
    subtasks: list[dict[str, Any]],
    item_type: str = "task",
    event_date: str = "",
    event_time: str = "",
    location: str = "",
) -> int:
    ph = placeholder(mode)
    now = _utc_now()
    subtasks_json = json.dumps(subtasks, ensure_ascii=False)
    values = (
        title,
        raw_input,
        notes,
        assignee,
        category,
        priority,
        due_label,
        due_date,
        _bool_param(False, mode),
        "",
        "",
        _bool_param(recurring, mode),
        recurrence_rule,
        quantity,
        aisle,
        subtasks_json,
        item_type,
        event_date,
        event_time,
        location,
        now,
        now,
    )
    cur = conn.cursor()
    cols = (
        "title, raw_input, notes, assignee, category, priority, due_label, due_date, "
        "completed, completed_by, completed_at, recurring, recurrence_rule, quantity, aisle, "
        "subtasks_json, item_type, event_date, event_time, location, created_at, updated_at"
    )
    placeholders = ", ".join([ph] * 22)
    if mode == "postgres":
        cur.execute(f"INSERT INTO tasks ({cols}) VALUES ({placeholders}) RETURNING id", values)
        inserted = cur.fetchone()
        new_id = int(inserted["id"])
    else:
        cur.execute(f"INSERT INTO tasks ({cols}) VALUES ({placeholders})", values)
        new_id = int(cur.lastrowid)
    cur.close()
    return new_id


@app.get("/api/health")
def health_check() -> dict[str, Any]:
    ensure_db_ready()
    return {
        "status": "ok",
        "version": "2.0.0",
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
    due_label: Optional[str] = Query(default=None),
    recurring: Optional[bool] = Query(default=None),
    item_type: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
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
            params.append(_bool_param(completed, mode))
        if due_label and due_label.strip().lower() != "all":
            clauses.append(f"due_label = {ph}")
            params.append(due_label.strip().lower())
        if recurring is not None:
            clauses.append(f"recurring = {ph}")
            params.append(_bool_param(recurring, mode))
        if item_type and item_type.strip().lower() != "all":
            clauses.append(f"item_type = {ph}")
            params.append(item_type.strip().lower())
        if search and search.strip():
            like_pattern = f"%{search.strip().lower()}%"
            clauses.append(f"(LOWER(title) LIKE {ph} OR LOWER(notes) LIKE {ph} OR LOWER(category) LIKE {ph} OR LOWER(location) LIKE {ph})")
            params.extend([like_pattern, like_pattern, like_pattern, like_pattern])

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT {TASK_COLUMNS} FROM tasks {where_sql} ORDER BY completed ASC, priority ASC, id DESC"
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
    due_date = payload.due_date.strip() if payload.due_date else compute_due_date(due_label)

    if payload.recurrence_rule is not None:
        recurrence_rule = payload.recurrence_rule.strip().lower() or "none"
        recurring_val = payload.recurring if payload.recurring is not None else (recurrence_rule != "none")
    elif payload.recurring is not None:
        recurring_val = bool(payload.recurring)
        recurrence_rule = parsed["recurrence_rule"] if parsed["recurrence_rule"] != "none" else ("daily" if recurring_val else "none")
    else:
        recurring_val = bool(parsed["recurring"])
        recurrence_rule = parsed["recurrence_rule"]

    quantity = payload.quantity.strip() if payload.quantity is not None else parsed["quantity"]
    aisle = payload.aisle.strip() if payload.aisle is not None else (parsed["aisle"] or infer_aisle(title, category))
    item_type = (payload.item_type or "task").strip().lower()
    if item_type not in ("task", "event"):
        item_type = "task"
    event_date = (payload.event_date or "").strip()
    if item_type == "event" and not event_date:
        event_date = due_date
    event_time = (payload.event_time or "").strip()
    location = (payload.location or "").strip()
    subtasks = [s.model_dump() for s in payload.subtasks] if payload.subtasks else []
    notes = (payload.notes or "").strip()

    with get_connection() as (conn, mode):
        new_id = _insert_task_row(
            conn,
            mode,
            title=title,
            raw_input=payload.raw_input.strip(),
            notes=notes,
            assignee=assignee,
            category=category,
            priority=priority,
            due_label=due_label,
            due_date=due_date,
            recurring=recurring_val,
            recurrence_rule=recurrence_rule,
            quantity=quantity,
            aisle=aisle,
            subtasks=subtasks,
            item_type=item_type,
            event_date=event_date,
            event_time=event_time,
            location=location,
        )
        _log_activity(conn, mode, assignee, "created", title, category)
        task = _fetch_task_by_id(conn, mode, new_id)

    if task is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve created task")

    await manager.broadcast({"event": "sync", "action": "created", "task_id": new_id})
    return task


@app.post("/api/tasks/clear-completed")
async def clear_completed_tasks(category: Optional[str] = Query(default=None)) -> dict[str, int]:
    ensure_db_ready()
    with get_connection() as (conn, mode):
        ph = placeholder(mode)
        comp_val = _bool_param(True, mode)
        cur = conn.cursor()
        if category and category.strip().lower() != "all":
            norm_cat = normalize_category(category)
            cur.execute(f"DELETE FROM tasks WHERE completed = {ph} AND category = {ph}", (comp_val, norm_cat))
        else:
            cur.execute(f"DELETE FROM tasks WHERE completed = {ph}", (comp_val,))
        cleared_count = int(cur.rowcount if cur.rowcount is not None and cur.rowcount >= 0 else 0)
        if cleared_count > 0:
            _log_activity(conn, mode, "both", "cleared_completed", f"{cleared_count} tâche(s)", category or "all")
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
        now = _utc_now()

        if "title" in updates and updates["title"] is not None:
            assignments.append(f"title = {ph}")
            params.append(updates["title"].strip())
        if "notes" in updates and updates["notes"] is not None:
            assignments.append(f"notes = {ph}")
            params.append(updates["notes"].strip())
        if "assignee" in updates and updates["assignee"] is not None:
            assignments.append(f"assignee = {ph}")
            params.append(normalize_assignee(updates["assignee"]))
        if "category" in updates and updates["category"] is not None:
            new_cat = normalize_category(updates["category"])
            assignments.append(f"category = {ph}")
            params.append(new_cat)
            if new_cat == "courses" and "aisle" not in updates and not existing["aisle"]:
                title_for_aisle = updates.get("title") or existing["title"]
                assignments.append(f"aisle = {ph}")
                params.append(infer_aisle(title_for_aisle, "courses"))
        if "priority" in updates and updates["priority"] is not None:
            assignments.append(f"priority = {ph}")
            params.append(int(updates["priority"]))
        if "due_label" in updates and updates["due_label"] is not None:
            lbl = updates["due_label"].strip().lower()
            assignments.append(f"due_label = {ph}")
            params.append(lbl)
            if "due_date" not in updates:
                assignments.append(f"due_date = {ph}")
                params.append(compute_due_date(lbl))
        if "due_date" in updates and updates["due_date"] is not None:
            assignments.append(f"due_date = {ph}")
            params.append(updates["due_date"].strip())
        if "quantity" in updates and updates["quantity"] is not None:
            assignments.append(f"quantity = {ph}")
            params.append(updates["quantity"].strip())
        if "aisle" in updates and updates["aisle"] is not None:
            assignments.append(f"aisle = {ph}")
            params.append(updates["aisle"].strip())
        if "item_type" in updates and updates["item_type"] is not None:
            assignments.append(f"item_type = {ph}")
            params.append(updates["item_type"].strip().lower())
        if "event_date" in updates and updates["event_date"] is not None:
            assignments.append(f"event_date = {ph}")
            params.append(updates["event_date"].strip())
        if "event_time" in updates and updates["event_time"] is not None:
            assignments.append(f"event_time = {ph}")
            params.append(updates["event_time"].strip())
        if "location" in updates and updates["location"] is not None:
            assignments.append(f"location = {ph}")
            params.append(updates["location"].strip())
        if "subtasks" in updates and updates["subtasks"] is not None:
            assignments.append(f"subtasks_json = {ph}")
            params.append(json.dumps(updates["subtasks"], ensure_ascii=False))

        # Keep recurring boolean & recurrence_rule synchronized
        if "recurrence_rule" in updates and updates["recurrence_rule"] is not None:
            rule = updates["recurrence_rule"].strip().lower() or "none"
            rec_bool = updates["recurring"] if ("recurring" in updates and updates["recurring"] is not None) else (rule != "none")
            assignments.append(f"recurrence_rule = {ph}")
            params.append(rule)
            assignments.append(f"recurring = {ph}")
            params.append(_bool_param(bool(rec_bool), mode))
        elif "recurring" in updates and updates["recurring"] is not None:
            rec_bool = bool(updates["recurring"])
            assignments.append(f"recurring = {ph}")
            params.append(_bool_param(rec_bool, mode))
            if not rec_bool:
                assignments.append(f"recurrence_rule = {ph}")
                params.append("none")
            elif existing["recurrence_rule"] == "none":
                assignments.append(f"recurrence_rule = {ph}")
                params.append("daily")

        # Handle completion state + completed_by / completed_at + activity log
        if "completed" in updates and updates["completed"] is not None:
            done_bool = bool(updates["completed"])
            assignments.append(f"completed = {ph}")
            params.append(_bool_param(done_bool, mode))
            if done_bool:
                actor = normalize_assignee(updates.get("completed_by")) if updates.get("completed_by") else existing["assignee"]
                assignments.append(f"completed_by = {ph}")
                params.append(actor)
                assignments.append(f"completed_at = {ph}")
                params.append(now)
                if not existing["completed"]:
                    _log_activity(conn, mode, actor, "completed", existing["title"], existing["category"])
            else:
                assignments.append(f"completed_by = {ph}")
                params.append("")
                assignments.append(f"completed_at = {ph}")
                params.append("")
                if existing["completed"]:
                    _log_activity(conn, mode, existing["assignee"], "reopened", existing["title"], existing["category"])

        if assignments:
            assignments.append(f"updated_at = {ph}")
            params.append(now)
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
        _log_activity(conn, mode, existing["assignee"], "deleted", existing["title"], existing["category"])

    await manager.broadcast({"event": "sync", "action": "deleted", "task_id": task_id})
    return {"deleted": True, "id": task_id}


def _ics_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


@app.get("/api/tasks/{task_id}/ics")
def download_task_ics(task_id: int) -> Response:
    """Export an event/task as RFC 5545 .ics for 1-tap Apple Calendar / Google import."""
    ensure_db_ready()
    with get_connection() as (conn, mode):
        task = _fetch_task_by_id(conn, mode, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    raw_date = (task.get("event_date") or task.get("due_date") or datetime.now(timezone.utc).date().isoformat()).strip()
    raw_time = (task.get("event_time") or "").strip()
    compact_date = raw_date.replace("-", "")

    if raw_time and ":" in raw_time:
        hh, mm = raw_time.split(":", 1)
        start_dt = datetime.strptime(f"{raw_date} {hh.zfill(2)}:{mm[:2].zfill(2)}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + timedelta(hours=2)
        dtstart_line = f"DTSTART:{start_dt.strftime('%Y%m%dT%H%M00')}"
        dtend_line = f"DTEND:{end_dt.strftime('%Y%m%dT%H%M00')}"
    else:
        dtstart_line = f"DTSTART;VALUE=DATE:{compact_date}"
        next_day = (datetime.strptime(raw_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y%m%d")
        dtend_line = f"DTEND;VALUE=DATE:{next_day}"

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//DuoTasks//Valentin & Lisa//FR",
        "CALSCALE:GREGORIAN",
        "BEGIN:VEVENT",
        f"UID:duotasks-{task_id}@duotasks.local",
        f"DTSTAMP:{stamp}",
        dtstart_line,
        dtend_line,
        f"SUMMARY:{_ics_escape(task['title'])}",
    ]
    if task.get("location"):
        lines.append(f"LOCATION:{_ics_escape(task['location'])}")
    if task.get("notes"):
        lines.append(f"DESCRIPTION:{_ics_escape(task['notes'])}")
    lines.extend(["END:VEVENT", "END:VCALENDAR", ""])

    ics_body = "\r\n".join(lines)
    return Response(
        content=ics_body,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="duotasks-event-{task_id}.ics"'},
    )


# --- Subtasks Checklist Endpoints ---


@app.post("/api/tasks/{task_id}/subtasks", response_model=TaskOut)
async def add_subtask(task_id: int, payload: SubtaskCreate) -> dict[str, Any]:
    ensure_db_ready()
    with get_connection() as (conn, mode):
        existing = _fetch_task_by_id(conn, mode, task_id)
        if existing is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        subtasks = list(existing["subtasks"])
        next_id = max((int(s["id"]) for s in subtasks), default=0) + 1
        subtasks.append({"id": next_id, "text": payload.text.strip(), "done": False})
        ph = placeholder(mode)
        cur = conn.cursor()
        cur.execute(
            f"UPDATE tasks SET subtasks_json = {ph}, updated_at = {ph} WHERE id = {ph}",
            (json.dumps(subtasks, ensure_ascii=False), _utc_now(), task_id),
        )
        cur.close()
        updated = _fetch_task_by_id(conn, mode, task_id)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    await manager.broadcast({"event": "sync", "action": "subtask_added", "task_id": task_id})
    return updated


@app.patch("/api/tasks/{task_id}/subtasks/{subtask_id}", response_model=TaskOut)
async def update_subtask(task_id: int, subtask_id: int, payload: SubtaskUpdate) -> dict[str, Any]:
    ensure_db_ready()
    with get_connection() as (conn, mode):
        existing = _fetch_task_by_id(conn, mode, task_id)
        if existing is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        subtasks = list(existing["subtasks"])
        found = False
        for item in subtasks:
            if int(item["id"]) == subtask_id:
                if payload.text is not None:
                    item["text"] = payload.text.strip()
                if payload.done is not None:
                    item["done"] = bool(payload.done)
                found = True
                break
        if not found:
            raise HTTPException(status_code=404, detail=f"Subtask {subtask_id} not found")
        ph = placeholder(mode)
        cur = conn.cursor()
        cur.execute(
            f"UPDATE tasks SET subtasks_json = {ph}, updated_at = {ph} WHERE id = {ph}",
            (json.dumps(subtasks, ensure_ascii=False), _utc_now(), task_id),
        )
        cur.close()
        updated = _fetch_task_by_id(conn, mode, task_id)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    await manager.broadcast({"event": "sync", "action": "subtask_updated", "task_id": task_id})
    return updated


@app.delete("/api/tasks/{task_id}/subtasks/{subtask_id}", response_model=TaskOut)
async def delete_subtask(task_id: int, subtask_id: int) -> dict[str, Any]:
    ensure_db_ready()
    with get_connection() as (conn, mode):
        existing = _fetch_task_by_id(conn, mode, task_id)
        if existing is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        subtasks = [item for item in existing["subtasks"] if int(item["id"]) != subtask_id]
        if len(subtasks) == len(existing["subtasks"]):
            raise HTTPException(status_code=404, detail=f"Subtask {subtask_id} not found")
        ph = placeholder(mode)
        cur = conn.cursor()
        cur.execute(
            f"UPDATE tasks SET subtasks_json = {ph}, updated_at = {ph} WHERE id = {ph}",
            (json.dumps(subtasks, ensure_ascii=False), _utc_now(), task_id),
        )
        cur.close()
        updated = _fetch_task_by_id(conn, mode, task_id)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    await manager.broadcast({"event": "sync", "action": "subtask_deleted", "task_id": task_id})
    return updated


# --- Routines & Template Packs Endpoints ---


@app.post("/api/routines/reset-daily")
async def reset_daily_routines() -> dict[str, int]:
    ensure_db_ready()
    with get_connection() as (conn, mode):
        ph = placeholder(mode)
        true_val = _bool_param(True, mode)
        false_val = _bool_param(False, mode)
        cur = conn.cursor()
        cur.execute(
            f"UPDATE tasks SET completed = {ph}, completed_by = {ph}, completed_at = {ph}, updated_at = {ph} "
            f"WHERE recurring = {ph} AND completed = {ph}",
            (false_val, "", "", _utc_now(), true_val, true_val),
        )
        reset_count = int(cur.rowcount if cur.rowcount is not None and cur.rowcount >= 0 else 0)
        if reset_count > 0:
            _log_activity(conn, mode, "both", "reset_routines", f"{reset_count} routine(s)", "daily")
        cur.close()
    await manager.broadcast({"event": "sync", "action": "routines_reset", "reset_count": reset_count})
    return {"reset_count": reset_count}


@app.get("/api/routines/packs", response_model=list[RoutinePackOut])
def list_routine_packs() -> list[dict[str, Any]]:
    return ROUTINE_PACKS


@app.post("/api/routines/packs/{pack_id}/apply")
async def apply_routine_pack(pack_id: str) -> dict[str, Any]:
    ensure_db_ready()
    pack = next((p for p in ROUTINE_PACKS if p["id"] == pack_id), None)
    if pack is None:
        raise HTTPException(status_code=404, detail=f"Pack '{pack_id}' not found")

    added_count = 0
    with get_connection() as (conn, mode):
        ph = placeholder(mode)
        false_val = _bool_param(False, mode)
        cur = conn.cursor()
        cur.execute(f"SELECT LOWER(title) AS t FROM tasks WHERE completed = {ph}", (false_val,))
        active_titles = {str(r["t"]) for r in cur.fetchall()}
        cur.close()

        for raw_line in pack["tasks"]:
            parsed = parse_quick_add(raw_line)
            if parsed["title"].lower() in active_titles:
                continue
            _insert_task_row(
                conn,
                mode,
                title=parsed["title"],
                raw_input=raw_line,
                notes="",
                assignee=parsed["assignee"],
                category=parsed["category"],
                priority=parsed["priority"],
                due_label=parsed["due_label"],
                due_date=parsed["due_date"],
                recurring=bool(parsed["recurring"]),
                recurrence_rule=parsed["recurrence_rule"],
                quantity=parsed["quantity"],
                aisle=parsed["aisle"],
                subtasks=[],
            )
            active_titles.add(parsed["title"].lower())
            added_count += 1

        if added_count > 0:
            _log_activity(conn, mode, "both", "applied_pack", f"{pack['name']} (+{added_count})", "pack")

    await manager.broadcast({"event": "sync", "action": "pack_applied", "pack_id": pack_id, "added_count": added_count})
    return {"pack_id": pack_id, "added_count": added_count}


# --- Groceries Staples Endpoints ---


@app.get("/api/groceries/staples", response_model=list[GroceryStapleOut])
def list_grocery_staples() -> list[dict[str, Any]]:
    ensure_db_ready()
    with get_connection() as (conn, _):
        cur = conn.cursor()
        cur.execute("SELECT id, name, aisle, default_qty, emoji, usage_count FROM grocery_staples ORDER BY usage_count DESC, aisle ASC, name ASC")
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        return rows


@app.post("/api/groceries/staples", response_model=GroceryStapleOut, status_code=status.HTTP_201_CREATED)
def create_grocery_staple(payload: GroceryStapleCreate) -> dict[str, Any]:
    ensure_db_ready()
    name = payload.name.strip()
    aisle = payload.aisle.strip() or infer_aisle(name, "courses") or "Épicerie"
    default_qty = payload.default_qty.strip()
    emoji = payload.emoji.strip() or "🛒"

    with get_connection() as (conn, mode):
        ph = placeholder(mode)
        cur = conn.cursor()
        cur.execute(f"SELECT id, name, aisle, default_qty, emoji, usage_count FROM grocery_staples WHERE LOWER(name) = {ph}", (name.lower(),))
        existing = cur.fetchone()
        if existing is not None:
            existing_id = int(existing["id"])
            cur.execute(
                f"UPDATE grocery_staples SET aisle = {ph}, default_qty = {ph}, emoji = {ph} WHERE id = {ph}",
                (aisle, default_qty, emoji, existing_id),
            )
            cur.execute(f"SELECT id, name, aisle, default_qty, emoji, usage_count FROM grocery_staples WHERE id = {ph}", (existing_id,))
            row = dict(cur.fetchone())
            cur.close()
            return row

        if mode == "postgres":
            cur.execute(
                f"INSERT INTO grocery_staples (name, aisle, default_qty, emoji, usage_count) VALUES ({ph}, {ph}, {ph}, {ph}, 0) RETURNING id",
                (name, aisle, default_qty, emoji),
            )
            new_id = int(cur.fetchone()["id"])
        else:
            cur.execute(
                f"INSERT INTO grocery_staples (name, aisle, default_qty, emoji, usage_count) VALUES ({ph}, {ph}, {ph}, {ph}, 0)",
                (name, aisle, default_qty, emoji),
            )
            new_id = int(cur.lastrowid)
        cur.execute(f"SELECT id, name, aisle, default_qty, emoji, usage_count FROM grocery_staples WHERE id = {ph}", (new_id,))
        row = dict(cur.fetchone())
        cur.close()
        return row


@app.post("/api/groceries/staples/{staple_id}/quick-add", response_model=TaskOut)
async def quick_add_grocery_staple(staple_id: int) -> dict[str, Any]:
    ensure_db_ready()
    with get_connection() as (conn, mode):
        ph = placeholder(mode)
        cur = conn.cursor()
        cur.execute(f"SELECT id, name, aisle, default_qty, emoji, usage_count FROM grocery_staples WHERE id = {ph}", (staple_id,))
        staple_row = cur.fetchone()
        if staple_row is None:
            cur.close()
            raise HTTPException(status_code=404, detail=f"Staple {staple_id} not found")
        staple = dict(staple_row)

        cur.execute(f"UPDATE grocery_staples SET usage_count = usage_count + 1 WHERE id = {ph}", (staple_id,))

        false_val = _bool_param(False, mode)
        cur.execute(
            f"SELECT id FROM tasks WHERE completed = {ph} AND category = {ph} AND LOWER(title) = {ph} LIMIT 1",
            (false_val, "courses", staple["name"].lower()),
        )
        existing_task = cur.fetchone()
        cur.close()

        if existing_task is not None:
            task_id = int(existing_task["id"])
            task = _fetch_task_by_id(conn, mode, task_id)
        else:
            raw = f"{staple['name']} {staple['default_qty']} #courses @both".strip()
            task_id = _insert_task_row(
                conn,
                mode,
                title=staple["name"],
                raw_input=raw,
                notes="",
                assignee="both",
                category="courses",
                priority=2,
                due_label="today",
                due_date=compute_due_date("today"),
                recurring=False,
                recurrence_rule="none",
                quantity=staple["default_qty"],
                aisle=staple["aisle"] or "Épicerie",
                subtasks=[],
            )
            _log_activity(conn, mode, "both", "quick_added", staple["name"], "courses")
            task = _fetch_task_by_id(conn, mode, task_id)

    if task is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve added grocery task")

    await manager.broadcast({"event": "sync", "action": "staple_added", "task_id": task["id"]})
    return task


# --- Couple Profile, Love Note & Kudos ---

DEFAULT_PRESET_TASKS = ["Deep clean salle de bain hebdo", "Deep clean cuisine hebdo"]


def _row_to_profile_dict(row: Any) -> dict[str, Any]:
    data = dict(row)
    raw_presets = data.pop("preset_tasks_json", None)
    presets: list[str] = list(DEFAULT_PRESET_TASKS)
    if isinstance(raw_presets, str) and raw_presets.strip():
        try:
            loaded = json.loads(raw_presets)
            if isinstance(loaded, list):
                presets = [str(item).strip() for item in loaded if str(item).strip()]
        except Exception:
            pass
    data["preset_tasks"] = presets
    return data


@app.get("/api/couple/profile", response_model=CoupleProfileOut)
def get_couple_profile() -> dict[str, Any]:
    ensure_db_ready()
    with get_connection() as (conn, _):
        cur = conn.cursor()
        cur.execute(
            "SELECT me_name, me_emoji, wife_name, wife_emoji, love_note, love_note_author, kudos_count, preset_tasks_json, updated_at "
            "FROM couple_profile WHERE id = 1"
        )
        row = cur.fetchone()
        cur.close()
    if row is None:
        return {
            "me_name": "Valentin",
            "me_emoji": "🦊",
            "wife_name": "Lisa",
            "wife_emoji": "🌸",
            "love_note": "On fait quoi de beau ce soir ? ✨",
            "love_note_author": "both",
            "kudos_count": 0,
            "preset_tasks": list(DEFAULT_PRESET_TASKS),
            "updated_at": "",
        }
    return _row_to_profile_dict(row)


@app.patch("/api/couple/profile", response_model=CoupleProfileOut)
async def update_couple_profile(payload: CoupleProfileUpdate) -> dict[str, Any]:
    ensure_db_ready()
    updates = payload.model_dump(exclude_unset=True)
    with get_connection() as (conn, mode):
        ph = placeholder(mode)
        assignments: list[str] = []
        params: list[Any] = []
        now = _utc_now()

        for field in ("me_name", "me_emoji", "wife_name", "wife_emoji", "love_note", "love_note_author"):
            if field in updates and updates[field] is not None:
                val = updates[field].strip()
                if field == "love_note_author":
                    val = normalize_assignee(val)
                assignments.append(f"{field} = {ph}")
                params.append(val)

        if "preset_tasks" in updates and updates["preset_tasks"] is not None:
            cleaned_presets = [str(p).strip() for p in updates["preset_tasks"] if str(p).strip()]
            assignments.append(f"preset_tasks_json = {ph}")
            params.append(json.dumps(cleaned_presets, ensure_ascii=False))

        if assignments:
            assignments.append(f"updated_at = {ph}")
            params.append(now)
            cur = conn.cursor()
            cur.execute(f"UPDATE couple_profile SET {', '.join(assignments)} WHERE id = 1", tuple(params))
            if "love_note" in updates and updates["love_note"] is not None:
                author = normalize_assignee(updates.get("love_note_author")) if updates.get("love_note_author") else "both"
                _log_activity(conn, mode, author, "love_note", updates["love_note"].strip() or "Mot doux mis à jour", "couple")
            cur.close()

        cur = conn.cursor()
        cur.execute(
            "SELECT me_name, me_emoji, wife_name, wife_emoji, love_note, love_note_author, kudos_count, preset_tasks_json, updated_at "
            "FROM couple_profile WHERE id = 1"
        )
        profile = _row_to_profile_dict(cur.fetchone())
        cur.close()

    await manager.broadcast({"event": "sync", "action": "profile_updated"})
    return profile


@app.post("/api/couple/kudos")
async def send_couple_kudos(payload: KudosRequest) -> dict[str, Any]:
    ensure_db_ready()
    actor = normalize_assignee(payload.from_partner)
    msg = payload.message.strip() or "Merci mon cœur ❤️"
    now = _utc_now()

    with get_connection() as (conn, mode):
        ph = placeholder(mode)
        cur = conn.cursor()
        cur.execute(f"UPDATE couple_profile SET kudos_count = kudos_count + 1, updated_at = {ph} WHERE id = 1", (now,))
        cur.execute("SELECT kudos_count FROM couple_profile WHERE id = 1")
        row = cur.fetchone()
        new_count = int(row["kudos_count"]) if row else 1
        cur.close()
        _log_activity(conn, mode, actor, "kudos", msg, "couple")

    await manager.broadcast({"event": "kudos", "from": actor, "message": msg, "kudos_count": new_count})
    return {"kudos_count": new_count, "message": msg, "from": actor}


# --- Couple Balance & Activity Analytics ---


@app.get("/api/stats", response_model=CoupleStatsOut)
def get_couple_stats() -> dict[str, Any]:
    ensure_db_ready()
    with get_connection() as (conn, _):
        cur = conn.cursor()
        cur.execute(f"SELECT {TASK_COLUMNS} FROM tasks")
        tasks = [row_to_task_dict(r) for r in cur.fetchall()]

        cur.execute("SELECT id, actor, action, task_title, category, created_at FROM activity_log ORDER BY id DESC LIMIT 15")
        recent_activity = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT kudos_count FROM couple_profile WHERE id = 1")
        prof_row = cur.fetchone()
        kudos_count = int(prof_row["kudos_count"]) if prof_row else 0
        cur.close()

    by_assignee: dict[str, dict[str, int]] = {
        "me": {"active": 0, "completed": 0},
        "wife": {"active": 0, "completed": 0},
        "both": {"active": 0, "completed": 0},
    }
    completed_by_actor: dict[str, int] = {"me": 0, "wife": 0, "both": 0}
    by_category: dict[str, dict[str, int]] = {}

    total_active = 0
    total_completed = 0
    overdue_or_urgent = 0
    courses_active = 0
    recurring_count = 0

    for t in tasks:
        who = t["assignee"] if t["assignee"] in by_assignee else "both"
        cat = t["category"] or "inbox"
        if cat not in by_category:
            by_category[cat] = {"active": 0, "completed": 0}

        if t["recurring"]:
            recurring_count += 1

        if t["completed"]:
            total_completed += 1
            by_assignee[who]["completed"] += 1
            by_category[cat]["completed"] += 1
            actor = t["completed_by"] if t["completed_by"] in completed_by_actor else who
            completed_by_actor[actor] += 1
        else:
            total_active += 1
            by_assignee[who]["active"] += 1
            by_category[cat]["active"] += 1
            if t["priority"] == 1:
                overdue_or_urgent += 1
            if cat == "courses":
                courses_active += 1

    couple_score = total_completed * 10 + kudos_count * 15
    return {
        "total_active": total_active,
        "total_completed": total_completed,
        "overdue_or_urgent": overdue_or_urgent,
        "courses_active": courses_active,
        "recurring_count": recurring_count,
        "by_assignee": by_assignee,
        "completed_by_actor": completed_by_actor,
        "by_category": by_category,
        "recent_activity": recent_activity,
        "extra": {
            "connected_devices": len(manager.active_connections),
            "kudos_count": kudos_count,
            "couple_score": couple_score,
        },
    }


# --- Joint Account Budget (Revolut via MacroDroid Android) ---


def _verify_duo_pin(x_duo_pin: str | None) -> None:
    expected = os.environ.get("DUO_PIN", "").strip()
    if not expected:
        return
    provided = (x_duo_pin or "").strip()
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="PIN Duo requis ou invalide",
        )


def _verify_revolut_webhook_secret(x_webhook_secret: str | None) -> None:
    expected = os.environ.get("REVOLUT_WEBHOOK_SECRET", "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="REVOLUT_WEBHOOK_SECRET non configuré sur le serveur",
        )
    provided = (x_webhook_secret or "").strip()
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Header X-Webhook-Secret invalide",
        )


def _decode_webhook_logs(raw_json: Any) -> list[dict[str, Any]]:
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

    out: list[dict[str, Any]] = []
    for item in items[:5]:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "received_at": str(item.get("received_at") or ""),
                "title": str(item.get("title") or "")[:160],
                "text": str(item.get("text") or "")[:240],
                "status": str(item.get("status") or "ignored"),
                "reason": str(item.get("reason") or ""),
                "parsed_kind": str(item.get("parsed_kind") or ""),
                "parsed_amount_cents": int(item.get("parsed_amount_cents") or 0),
                "parsed_merchant": str(item.get("parsed_merchant") or ""),
            }
        )
    return out


def _append_webhook_log(
    conn: Any,
    mode: str,
    existing_logs_json: Any,
    entry: dict[str, Any],
) -> None:
    logs = _decode_webhook_logs(existing_logs_json)
    logs.insert(0, entry)
    trimmed = logs[:5]
    ph = placeholder(mode)
    cur = conn.cursor()
    cur.execute(
        f"UPDATE budget_account SET webhook_logs_json = {ph} WHERE id = 1",
        (json.dumps(trimmed, ensure_ascii=False),),
    )
    cur.close()


def _row_to_budget_tx(row: Any) -> dict[str, Any]:
    data = dict(row)
    return {
        "id": int(data["id"]),
        "kind": str(data.get("kind") or "expense"),
        "amount_cents": int(data.get("amount_cents") or 0),
        "merchant": str(data.get("merchant") or ""),
        "note": str(data.get("note") or ""),
        "source": str(data.get("source") or "manual"),
        "raw_text": str(data.get("raw_text") or ""),
        "created_at": str(data.get("created_at") or ""),
    }


def _insert_budget_tx(
    conn: Any,
    mode: str,
    *,
    kind: str,
    amount_cents: int,
    merchant: str,
    note: str,
    source: str,
    raw_text: str,
    dedupe_key: str | None,
    created_at: str,
) -> int:
    ph = placeholder(mode)
    cur = conn.cursor()
    cols = "kind, amount_cents, merchant, note, source, raw_text, dedupe_key, created_at"
    vals = (kind, amount_cents, merchant[:120], note[:200], source, raw_text[:320], dedupe_key, created_at)
    phs = ", ".join([ph] * 8)
    if mode == "postgres":
        cur.execute(f"INSERT INTO budget_transactions ({cols}) VALUES ({phs}) RETURNING id", vals)
        inserted = cur.fetchone()
        new_id = int(inserted["id"])
    else:
        cur.execute(f"INSERT INTO budget_transactions ({cols}) VALUES ({phs})", vals)
        new_id = int(cur.lastrowid)
    cur.close()
    return new_id


def _build_budget_overview(conn: Any) -> dict[str, Any]:
    cur = conn.cursor()
    cur.execute(
        "SELECT balance_cents, currency, joint_filter_keyword, webhook_logs_json, updated_at "
        "FROM budget_account WHERE id = 1"
    )
    acc = cur.fetchone()
    if acc is None:
        acc_dict = {
            "balance_cents": 0,
            "currency": "EUR",
            "joint_filter_keyword": "",
            "webhook_logs_json": "[]",
            "updated_at": "",
        }
    else:
        acc_dict = dict(acc)

    cur.execute(
        "SELECT id, kind, amount_cents, merchant, note, source, raw_text, created_at "
        "FROM budget_transactions ORDER BY id DESC LIMIT 15"
    )
    tx_rows = [_row_to_budget_tx(r) for r in cur.fetchall()]

    cur.execute(
        "SELECT id, kind, amount_cents, merchant, note, source, raw_text, created_at "
        "FROM budget_transactions WHERE kind = 'expense' ORDER BY id DESC LIMIT 1"
    )
    last_exp_row = cur.fetchone()
    cur.close()

    return {
        "balance_cents": int(acc_dict.get("balance_cents") or 0),
        "currency": str(acc_dict.get("currency") or "EUR"),
        "joint_filter_keyword": str(acc_dict.get("joint_filter_keyword") or ""),
        "webhook_configured": bool(os.environ.get("REVOLUT_WEBHOOK_SECRET", "").strip()),
        "pin_required": bool(os.environ.get("DUO_PIN", "").strip()),
        "updated_at": str(acc_dict.get("updated_at") or ""),
        "last_expense": _row_to_budget_tx(last_exp_row) if last_exp_row else None,
        "last_transaction": tx_rows[0] if tx_rows else None,
        "transactions": tx_rows,
        "webhook_logs": _decode_webhook_logs(acc_dict.get("webhook_logs_json")),
    }


def _resolve_cents_from_payload(payload: BudgetRefillRequest) -> int:
    if payload.amount_cents is not None:
        return int(payload.amount_cents)
    if payload.amount is not None:
        try:
            dec = Decimal(str(payload.amount))
            return int((dec * Decimal(100)).quantize(Decimal("1")))
        except (InvalidOperation, ValueError):
            raise HTTPException(status_code=422, detail="Montant invalide")
    raise HTTPException(status_code=422, detail="amount_cents ou amount requis")


@app.get("/api/budget", response_model=BudgetOverviewOut)
def get_budget_overview(x_duo_pin: Optional[str] = Header(default=None, alias="X-Duo-Pin")) -> dict[str, Any]:
    ensure_db_ready()
    _verify_duo_pin(x_duo_pin)
    with get_connection() as (conn, _):
        return _build_budget_overview(conn)


@app.post("/api/budget/refill", response_model=BudgetOverviewOut)
async def budget_refill_or_adjust(
    payload: BudgetRefillRequest,
    x_duo_pin: Optional[str] = Header(default=None, alias="X-Duo-Pin"),
) -> dict[str, Any]:
    ensure_db_ready()
    _verify_duo_pin(x_duo_pin)

    cents = _resolve_cents_from_payload(payload)
    mode_op = payload.mode
    if mode_op in ("refill", "expense") and cents <= 0:
        raise HTTPException(status_code=422, detail="Le montant doit être strictement positif")

    now = _utc_now()
    note = payload.note.strip()
    merchant = payload.merchant.strip()

    with get_connection() as (conn, mode):
        ph = placeholder(mode)
        cur = conn.cursor()
        cur.execute("SELECT balance_cents FROM budget_account WHERE id = 1")
        row = cur.fetchone()
        current_balance = int(row["balance_cents"]) if row else 0
        cur.close()

        if mode_op == "refill":
            new_balance = current_balance + cents
            tx_amount = cents
            tx_merchant = merchant or "Refill compte joint"
        elif mode_op == "expense":
            new_balance = current_balance - cents
            tx_amount = cents
            tx_merchant = merchant or "Dépense manuelle"
        else:
            # recalibrate: cents represents the exact true Revolut balance
            new_balance = cents
            tx_amount = new_balance - current_balance
            tx_merchant = merchant or "Recalage solde"
            if not note:
                euros = f"{new_balance / 100:.2f}".replace(".", ",")
                note = f"Solde réel {euros} €"

        _insert_budget_tx(
            conn,
            mode,
            kind=mode_op,
            amount_cents=tx_amount,
            merchant=tx_merchant,
            note=note,
            source="manual",
            raw_text="",
            dedupe_key=None,
            created_at=now,
        )

        cur = conn.cursor()
        cur.execute(
            f"UPDATE budget_account SET balance_cents = {ph}, updated_at = {ph} WHERE id = 1",
            (new_balance, now),
        )
        cur.close()
        overview = _build_budget_overview(conn)

    await manager.broadcast({"event": "sync", "action": f"budget_{mode_op}"})
    return overview


@app.delete("/api/budget/transactions/{tx_id}", response_model=BudgetOverviewOut)
async def delete_budget_transaction(
    tx_id: int,
    x_duo_pin: Optional[str] = Header(default=None, alias="X-Duo-Pin"),
) -> dict[str, Any]:
    ensure_db_ready()
    _verify_duo_pin(x_duo_pin)
    now = _utc_now()

    with get_connection() as (conn, mode):
        ph = placeholder(mode)
        cur = conn.cursor()
        cur.execute(
            f"SELECT id, kind, amount_cents FROM budget_transactions WHERE id = {ph}",
            (tx_id,),
        )
        tx = cur.fetchone()
        if tx is None:
            cur.close()
            raise HTTPException(status_code=404, detail="Transaction introuvable")

        kind = str(tx["kind"])
        amt = int(tx["amount_cents"])

        cur.execute("SELECT balance_cents FROM budget_account WHERE id = 1")
        acc = cur.fetchone()
        current_balance = int(acc["balance_cents"]) if acc else 0

        if kind == "expense":
            new_balance = current_balance + amt
        elif kind == "refill":
            new_balance = current_balance - amt
        else:
            new_balance = current_balance

        cur.execute(f"DELETE FROM budget_transactions WHERE id = {ph}", (tx_id,))
        cur.execute(
            f"UPDATE budget_account SET balance_cents = {ph}, updated_at = {ph} WHERE id = 1",
            (new_balance, now),
        )
        cur.close()
        overview = _build_budget_overview(conn)

    await manager.broadcast({"event": "sync", "action": "budget_tx_deleted", "tx_id": tx_id})
    return overview


@app.patch("/api/budget/settings", response_model=BudgetOverviewOut)
async def update_budget_settings(
    payload: BudgetSettingsUpdate,
    x_duo_pin: Optional[str] = Header(default=None, alias="X-Duo-Pin"),
) -> dict[str, Any]:
    ensure_db_ready()
    _verify_duo_pin(x_duo_pin)
    now = _utc_now()
    kw = payload.joint_filter_keyword.strip()

    with get_connection() as (conn, mode):
        ph = placeholder(mode)
        cur = conn.cursor()
        cur.execute(
            f"UPDATE budget_account SET joint_filter_keyword = {ph}, updated_at = {ph} WHERE id = 1",
            (kw, now),
        )
        cur.close()
        overview = _build_budget_overview(conn)

    await manager.broadcast({"event": "sync", "action": "budget_settings_updated"})
    return overview


@app.post("/api/budget/webhook/revolut")
async def revolut_macrodroid_webhook(
    payload: RevolutWebhookPayload,
    x_webhook_secret: Optional[str] = Header(default=None, alias="X-Webhook-Secret"),
) -> dict[str, Any]:
    ensure_db_ready()
    _verify_revolut_webhook_secret(x_webhook_secret)

    now = _utc_now()
    dedupe_key = compute_dedupe_key(
        payload.title,
        payload.text,
        timestamp=payload.timestamp,
        explicit_key=payload.dedupe_key,
    )

    with get_connection() as (conn, mode):
        ph = placeholder(mode)
        cur = conn.cursor()
        cur.execute(
            "SELECT balance_cents, joint_filter_keyword, webhook_logs_json FROM budget_account WHERE id = 1"
        )
        acc = cur.fetchone()
        current_balance = int(acc["balance_cents"]) if acc else 0
        keyword = str(acc["joint_filter_keyword"] or "") if acc else ""
        logs_json = acc["webhook_logs_json"] if acc else "[]"

        # Check idempotence first (protects against MacroDroid cold-start retries)
        cur.execute(
            f"SELECT id FROM budget_transactions WHERE dedupe_key = {ph}",
            (dedupe_key,),
        )
        existing = cur.fetchone()
        cur.close()

        if existing is not None:
            return {
                "status": "duplicate",
                "dedupe_key": dedupe_key,
                "transaction_id": int(existing["id"]),
                "balance_cents": current_balance,
            }

        parsed = parse_revolut_notification(payload.title, payload.text, joint_filter_keyword=keyword)
        if parsed.get("ignored"):
            reason = str(parsed.get("reason") or "ignored")
            _append_webhook_log(
                conn,
                mode,
                logs_json,
                {
                    "received_at": now,
                    "title": payload.title.strip()[:160],
                    "text": payload.text.strip()[:240],
                    "status": "ignored",
                    "reason": reason,
                    "parsed_kind": "",
                    "parsed_amount_cents": 0,
                    "parsed_merchant": "",
                },
            )
            broadcast_action = "budget_webhook_ignored"
            result: dict[str, Any] = {"status": "ignored", "reason": reason, "balance_cents": current_balance}
        else:
            kind = str(parsed["kind"])
            amount_cents = int(parsed["amount_cents"])
            merchant = str(parsed["merchant"])
            raw_text = str(parsed["raw_text"])
            new_balance = current_balance - amount_cents if kind == "expense" else current_balance + amount_cents

            try:
                tx_id = _insert_budget_tx(
                    conn,
                    mode,
                    kind=kind,
                    amount_cents=amount_cents,
                    merchant=merchant,
                    note="",
                    source="macrodroid",
                    raw_text=raw_text,
                    dedupe_key=dedupe_key,
                    created_at=now,
                )
            except Exception as exc:
                # Race-condition duplicate on UNIQUE(dedupe_key)
                if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
                    conn.rollback()
                    return {"status": "duplicate", "dedupe_key": dedupe_key, "balance_cents": current_balance}
                raise

            cur = conn.cursor()
            cur.execute(
                f"UPDATE budget_account SET balance_cents = {ph}, updated_at = {ph} WHERE id = 1",
                (new_balance, now),
            )
            cur.close()

            _append_webhook_log(
                conn,
                mode,
                logs_json,
                {
                    "received_at": now,
                    "title": payload.title.strip()[:160],
                    "text": payload.text.strip()[:240],
                    "status": "applied",
                    "reason": "",
                    "parsed_kind": kind,
                    "parsed_amount_cents": amount_cents,
                    "parsed_merchant": merchant,
                },
            )
            broadcast_action = "budget_webhook_applied"
            result = {
                "status": "ok",
                "kind": kind,
                "amount_cents": amount_cents,
                "merchant": merchant,
                "balance_cents": new_balance,
                "transaction_id": tx_id,
                "dedupe_key": dedupe_key,
            }

    await manager.broadcast({"event": "sync", "action": broadcast_action})
    return result


@app.websocket("/ws")
async def websocket_sync(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    await manager.broadcast(
        {"event": "devices", "connected_devices": len(manager.active_connections)},
        exclude=websocket,
    )
    try:
        while True:
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast({"event": "devices", "connected_devices": len(manager.active_connections)})
    except Exception:
        manager.disconnect(websocket)
        await manager.broadcast({"event": "devices", "connected_devices": len(manager.active_connections)})


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
