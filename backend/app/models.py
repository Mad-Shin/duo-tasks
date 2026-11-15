"""
Pydantic API contracts for DuoTasks.

These models define the exact JSON shape accepted and returned by FastAPI,
providing automatic input validation and interactive Swagger docs at `/docs`.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    raw_input: str = Field(..., min_length=1, max_length=280, description="Natural text like 'Lait demain @wife #courses !1'")
    assignee: Optional[str] = Field(default=None, max_length=40)
    category: Optional[str] = Field(default=None, max_length=40)
    priority: Optional[int] = Field(default=None, ge=1, le=3)
    due_label: Optional[str] = Field(default=None, max_length=40)


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=280)
    completed: Optional[bool] = None
    assignee: Optional[str] = Field(default=None, max_length=40)
    category: Optional[str] = Field(default=None, max_length=40)
    priority: Optional[int] = Field(default=None, ge=1, le=3)
    due_label: Optional[str] = Field(default=None, max_length=40)


class TaskOut(BaseModel):
    id: int
    title: str
    raw_input: str
    assignee: str
    category: str
    priority: int
    due_label: str
    completed: bool
    created_at: str


class ParsePreviewRequest(BaseModel):
    raw_input: str = Field(default="", max_length=280)


class ParsePreviewOut(BaseModel):
    title: str
    assignee: str
    category: str
    priority: int
    due_label: str
