"""
Pydantic API contracts for DuoTasks.

Defines the strict request/response schemas for tasks, subtasks, grocery staples,
routine packs, and couple balance analytics.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class SubtaskItem(BaseModel):
    id: int
    text: str = Field(..., min_length=1, max_length=200)
    done: bool = False


class SubtaskCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=200)


class SubtaskUpdate(BaseModel):
    text: Optional[str] = Field(default=None, min_length=1, max_length=200)
    done: Optional[bool] = None


class TaskCreate(BaseModel):
    raw_input: str = Field(..., min_length=1, max_length=280, description="Natural text like 'Lait 2L demain @wife #courses !1'")
    notes: Optional[str] = Field(default="", max_length=2000)
    assignee: Optional[str] = Field(default=None, max_length=40)
    category: Optional[str] = Field(default=None, max_length=40)
    priority: Optional[int] = Field(default=None, ge=1, le=3)
    due_label: Optional[str] = Field(default=None, max_length=40)
    due_date: Optional[str] = Field(default=None, max_length=20)
    recurring: Optional[bool] = None
    recurrence_rule: Optional[str] = Field(default=None, max_length=20)
    quantity: Optional[str] = Field(default=None, max_length=40)
    aisle: Optional[str] = Field(default=None, max_length=60)
    item_type: Optional[str] = Field(default="task", max_length=16)
    event_date: Optional[str] = Field(default=None, max_length=20)
    event_time: Optional[str] = Field(default=None, max_length=16)
    location: Optional[str] = Field(default=None, max_length=120)
    subtasks: Optional[list[SubtaskItem]] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=280)
    notes: Optional[str] = Field(default=None, max_length=2000)
    completed: Optional[bool] = None
    completed_by: Optional[str] = Field(default=None, max_length=40)
    assignee: Optional[str] = Field(default=None, max_length=40)
    category: Optional[str] = Field(default=None, max_length=40)
    priority: Optional[int] = Field(default=None, ge=1, le=3)
    due_label: Optional[str] = Field(default=None, max_length=40)
    due_date: Optional[str] = Field(default=None, max_length=20)
    recurring: Optional[bool] = None
    recurrence_rule: Optional[str] = Field(default=None, max_length=20)
    quantity: Optional[str] = Field(default=None, max_length=40)
    aisle: Optional[str] = Field(default=None, max_length=60)
    item_type: Optional[str] = Field(default=None, max_length=16)
    event_date: Optional[str] = Field(default=None, max_length=20)
    event_time: Optional[str] = Field(default=None, max_length=16)
    location: Optional[str] = Field(default=None, max_length=120)
    subtasks: Optional[list[SubtaskItem]] = None


class TaskOut(BaseModel):
    id: int
    title: str
    raw_input: str
    notes: str = ""
    assignee: str
    category: str
    priority: int
    due_label: str
    due_date: str = ""
    completed: bool
    completed_by: str = ""
    completed_at: str = ""
    recurring: bool = False
    recurrence_rule: str = "none"
    quantity: str = ""
    aisle: str = ""
    item_type: str = "task"
    event_date: str = ""
    event_time: str = ""
    location: str = ""
    subtasks: list[SubtaskItem] = Field(default_factory=list)
    created_at: str
    updated_at: str = ""


class ParsePreviewRequest(BaseModel):
    raw_input: str = Field(default="", max_length=280)


class ParsePreviewOut(BaseModel):
    title: str
    assignee: str
    category: str
    priority: int
    due_label: str
    due_date: str = ""
    recurring: bool = False
    recurrence_rule: str = "none"
    quantity: str = ""
    aisle: str = ""


class GroceryStapleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    aisle: str = Field(default="Épicerie", max_length=60)
    default_qty: str = Field(default="", max_length=40)
    emoji: str = Field(default="🛒", max_length=12)


class GroceryStapleOut(BaseModel):
    id: int
    name: str
    aisle: str
    default_qty: str
    emoji: str
    usage_count: int


class RoutinePackOut(BaseModel):
    id: str
    name: str
    description: str
    emoji: str
    tasks: list[str]


class ActivityEntryOut(BaseModel):
    id: int
    actor: str
    action: str
    task_title: str
    category: str
    created_at: str


class CoupleStatsOut(BaseModel):
    total_active: int
    total_completed: int
    overdue_or_urgent: int
    courses_active: int
    recurring_count: int
    by_assignee: dict[str, dict[str, int]]
    completed_by_actor: dict[str, int]
    by_category: dict[str, dict[str, int]]
    recent_activity: list[ActivityEntryOut]
    extra: dict[str, Any] = Field(default_factory=dict)


class CoupleProfileOut(BaseModel):
    me_name: str
    me_emoji: str
    wife_name: str
    wife_emoji: str
    love_note: str
    love_note_author: str
    kudos_count: int
    preset_tasks: list[str] = Field(
        default_factory=lambda: ["Deep clean salle de bain hebdo", "Deep clean cuisine hebdo"]
    )
    preset_courses: list[str] = Field(
        default_factory=lambda: ["Pâtes", "Riz", "Liquide vaisselle", "Linge"]
    )
    updated_at: str = ""


class CoupleProfileUpdate(BaseModel):
    me_name: Optional[str] = Field(default=None, min_length=1, max_length=32)
    me_emoji: Optional[str] = Field(default=None, min_length=1, max_length=8)
    wife_name: Optional[str] = Field(default=None, min_length=1, max_length=32)
    wife_emoji: Optional[str] = Field(default=None, min_length=1, max_length=8)
    love_note: Optional[str] = Field(default=None, max_length=200)
    love_note_author: Optional[str] = Field(default=None, max_length=20)
    preset_tasks: Optional[list[str]] = None
    preset_courses: Optional[list[str]] = None


class KudosRequest(BaseModel):
    from_partner: str = Field(default="me", max_length=20)
    message: str = Field(default="Merci mon cœur ❤️", min_length=1, max_length=160)


# --- Joint Account Budget (Revolut via MacroDroid) ---


class BudgetTransactionOut(BaseModel):
    id: int
    kind: str
    amount_cents: int
    merchant: str = ""
    note: str = ""
    source: str = "manual"
    created_at: str


class WebhookLogEntry(BaseModel):
    received_at: str
    status: str = "applied"
    reason: str = ""
    parsed_kind: str = ""
    parsed_amount_cents: int = 0
    parsed_merchant: str = ""


class BudgetOverviewOut(BaseModel):
    balance_cents: int
    currency: str = "EUR"
    joint_filter_keyword: str = ""
    webhook_configured: bool = False
    pin_required: bool = False
    updated_at: str = ""
    last_expense: Optional[BudgetTransactionOut] = None
    last_transaction: Optional[BudgetTransactionOut] = None
    transactions: list[BudgetTransactionOut] = Field(default_factory=list)
    webhook_logs: list[WebhookLogEntry] = Field(default_factory=list)


class BudgetRefillRequest(BaseModel):
    mode: str = Field(default="refill", pattern="^(refill|expense|recalibrate)$")
    amount_cents: Optional[int] = None
    amount: Optional[float] = None
    merchant: str = Field(default="", max_length=120)
    note: str = Field(default="", max_length=200)


class BudgetSettingsUpdate(BaseModel):
    joint_filter_keyword: str = Field(default="", max_length=80)


class RevolutWebhookPayload(BaseModel):
    title: str = Field(default="", max_length=300)
    text: str = Field(default="", max_length=1000)
    timestamp: Optional[str | int | float] = None
    dedupe_key: Optional[str] = Field(default=None, max_length=128)


# --- Domotique (Shelly Cloud + Local LAN Fallback) ---


class ClimateSensorOut(BaseModel):
    device_id: str
    name: str
    model: str = ""
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    battery_pct: Optional[int] = None
    online: bool = False
    updated_at: str = ""


class HeatingDeviceOut(BaseModel):
    device_id: str
    name: str
    model: str = ""
    channel: int = 0
    is_on: bool = False
    online: bool = False
    relay_temp_c: Optional[float] = None
    rssi: Optional[int] = None
    timer_remaining_sec: Optional[int] = None
    updated_at: str = ""


class LightDeviceOut(BaseModel):
    device_id: str
    name: str
    model: str = ""
    kind: str = "light"
    channel: int = 0
    is_on: bool = False
    brightness: Optional[int] = None
    online: bool = False
    updated_at: str = ""


class DomotiqueOverviewOut(BaseModel):
    configured: bool = False
    source: str = "unconfigured"
    server_uri: str = ""
    online: bool = False
    pin_required: bool = False
    fetched_at: str = ""
    error: str = ""
    heating: Optional[HeatingDeviceOut] = None
    climate: Optional[ClimateSensorOut] = None
    lights: list[LightDeviceOut] = Field(default_factory=list)


class HeatingControlRequest(BaseModel):
    on: bool
    timer_minutes: Optional[int] = Field(default=None, ge=1, le=720)


class DeviceControlRequest(BaseModel):
    on: bool
    kind: str = Field(default="light", pattern="^(light|switch)$")
    channel: int = Field(default=0, ge=0, le=3)
    brightness: Optional[int] = Field(default=None, ge=1, le=100)
    timer_minutes: Optional[int] = Field(default=None, ge=1, le=720)
