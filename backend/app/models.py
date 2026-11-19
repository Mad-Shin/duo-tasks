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
