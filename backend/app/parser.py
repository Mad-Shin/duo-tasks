"""
Deterministic Todoist-style Quick-Add Parser (Lesson 2 of the Coaching Roadmap).

Extracts structured metadata from a single fast line of text:
- `@assignee` (`@wife`, `@elle`, `@me`, `@moi`, `@both`) -> default `"both"`
- `#category` (`#courses`, `#maison`, `#daily`, etc.)      -> default `"inbox"`
- `!priority` (`!1` urgent, `!2` high, `!3` normal)       -> default `3`
- Due keywords (`today`/`aujourd'hui`, `tomorrow`/`demain`, `weekend`/`samedi`/`dimanche`) -> default `"today"`
"""

from __future__ import annotations

import re
from typing import Any

ASSIGNEE_ALIASES: dict[str, str] = {
    "wife": "wife",
    "elle": "wife",
    "femme": "wife",
    "madame": "wife",
    "me": "me",
    "moi": "me",
    "val": "me",
    "valentin": "me",
    "both": "both",
    "nous": "both",
    "duo": "both",
}

DUE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?<!\w)(?:tomorrow|demain)(?!\w)", re.IGNORECASE), "tomorrow"),
    (re.compile(r"(?<!\w)(?:today|aujourd['’]?hui|aujourdhui|auj)(?!\w)", re.IGNORECASE), "today"),
    (re.compile(r"(?<!\w)(?:week-?end|samedi|dimanche)(?!\w)", re.IGNORECASE), "weekend"),
]

ASSIGNEE_RE = re.compile(r"(?<!\S)@([a-zA-ZÀ-ÿ0-9_-]+)")
CATEGORY_RE = re.compile(r"(?<!\S)#([a-zA-ZÀ-ÿ0-9_-]+)")
PRIORITY_RE = re.compile(r"(?<!\S)!([1-3])(?=\s|$)")


def normalize_assignee(token: str | None) -> str:
    if not token:
        return "both"
    cleaned = token.strip().lstrip("@").lower()
    return ASSIGNEE_ALIASES.get(cleaned, cleaned or "both")


def normalize_category(token: str | None) -> str:
    if not token:
        return "inbox"
    cleaned = token.strip().lstrip("#").lower()
    return cleaned or "inbox"


def parse_quick_add(raw_text: str) -> dict[str, Any]:
    """
    Parse a natural quick-add string into structured task fields without an LLM.

    Example:
        "Acheter du lait demain @wife #courses !1"
        -> {
            "title": "Acheter du lait",
            "assignee": "wife",
            "category": "courses",
            "priority": 1,
            "due_label": "tomorrow",
        }
    """
    working = (raw_text or "").strip()

    assignee = "both"
    m_assignee = ASSIGNEE_RE.search(working)
    if m_assignee:
        assignee = normalize_assignee(m_assignee.group(1))
        working = ASSIGNEE_RE.sub("", working)

    category = "inbox"
    m_category = CATEGORY_RE.search(working)
    if m_category:
        category = normalize_category(m_category.group(1))
        working = CATEGORY_RE.sub("", working)

    priority = 3
    m_priority = PRIORITY_RE.search(working)
    if m_priority:
        priority = int(m_priority.group(1))
        working = PRIORITY_RE.sub("", working)

    due_label = "today"
    for pattern, label in DUE_PATTERNS:
        if pattern.search(working):
            due_label = label
            working = pattern.sub("", working)
            break

    clean_title = re.sub(r"\s{2,}", " ", working).strip(" ,;-")
    if not clean_title:
        clean_title = (raw_text or "").strip() or "Untitled task"

    return {
        "title": clean_title,
        "assignee": assignee,
        "category": category,
        "priority": priority,
        "due_label": due_label,
    }
