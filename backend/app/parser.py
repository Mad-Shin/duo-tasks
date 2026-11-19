"""
Deterministic Todoist-style Quick-Add Parser for DuoTasks.

Extracts structured metadata in <0.1ms with zero LLM calls:
- `@assignee` (`@wife`, `@elle`, `@me`, `@moi`, `@both`) -> default `"both"`
- `#category` (`#courses`, `#maison`, `#daily`, etc.)      -> default `"inbox"`
- `!priority` (`!1` urgent, `!2` high, `!3` normal)       -> default `3`
- Due keywords (`today`/`aujourd'hui`, `tomorrow`/`demain`, `weekend`, `later`/`plus tard`) -> `due_label` + ISO `due_date`
- Recurrence (`every day`/`tous les jours`, `every week`/`hebdo`, `every month`/`mensuel`) -> `recurring` + `recurrence_rule`
- Explicit grocery quantities (`2L`, `500g`, `x12`, `2 bouteilles`) -> `quantity`
- Supermarket aisle classification for `#courses` items -> `aisle`
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, timedelta
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
    (re.compile(r"(?<!\w)(?:later|plus\s+tard|bient[oô]t)(?!\w)", re.IGNORECASE), "later"),
    (re.compile(r"(?<!\w)(?:lundi|monday)(?!\w)", re.IGNORECASE), "lundi"),
    (re.compile(r"(?<!\w)(?:mardi|tuesday)(?!\w)", re.IGNORECASE), "mardi"),
    (re.compile(r"(?<!\w)(?:mercredi|wednesday)(?!\w)", re.IGNORECASE), "mercredi"),
    (re.compile(r"(?<!\w)(?:jeudi|thursday)(?!\w)", re.IGNORECASE), "jeudi"),
    (re.compile(r"(?<!\w)(?:vendredi|friday)(?!\w)", re.IGNORECASE), "vendredi"),
]

WEEKDAY_INDEX: dict[str, int] = {
    "lundi": 0,
    "mardi": 1,
    "mercredi": 2,
    "jeudi": 3,
    "vendredi": 4,
}

RECURRENCE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"(?<!\w)(?:every\s+day|daily|tous\s+les\s+jours|chaque\s+jour|quotidien)(?!\w)",
            re.IGNORECASE,
        ),
        "daily",
    ),
    (
        re.compile(
            r"(?<!\w)(?:every\s+week|weekly|toutes\s+les\s+semaines|chaque\s+semaine|hebdo(?:madaire)?)(?!\w)",
            re.IGNORECASE,
        ),
        "weekly",
    ),
    (
        re.compile(
            r"(?<!\w)(?:every\s+month|monthly|tous\s+les\s+mois|chaque\s+mois|mensuel(?:le)?)(?!\w)",
            re.IGNORECASE,
        ),
        "monthly",
    ),
]

ASSIGNEE_RE = re.compile(r"(?<!\S)@([a-zA-ZÀ-ÿ0-9_-]+)")
CATEGORY_RE = re.compile(r"(?<!\S)#([a-zA-ZÀ-ÿ0-9_-]+)")
PRIORITY_RE = re.compile(r"(?<!\S)!([1-3])(?=\s|$)")
QUANTITY_RE = re.compile(
    r"(?<!\w)(?:x\s*\d+|\d+(?:[.,]\d+)?\s*(?:kg|g|mg|ml|cl|dl|l|bouteilles?|paquets?|bo[îi]tes?|tranches?|pav[ée]s?|bidons?|filets?|sachets?))(?!\w)",
    re.IGNORECASE,
)

AISLE_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    (
        "Frais & Laitier",
        ("lait", "oeuf", "beurre", "yaourt", "yogourt", "fromage", "creme", "mozzarella", "parmesan", "jambon", "lardons"),
    ),
    (
        "Boulangerie",
        ("pain", "baguette", "brioche", "croissant", "viennoiserie", "mie"),
    ),
    (
        "Fruits & Légumes",
        (
            "banane",
            "tomate",
            "pomme",
            "avocat",
            "salade",
            "legume",
            "fruit",
            "oignon",
            "ail",
            "citron",
            "carotte",
            "courgette",
            "patate",
            "pomme de terre",
            "fraise",
            "orange",
            "poire",
            "concombre",
            "poivron",
            "herbe",
            "persil",
            "basilic",
        ),
    ),
    (
        "Viande & Poisson",
        ("poulet", "viande", "boeuf", "steak", "saumon", "poisson", "thon", "crevette", "dinde", "porc", "saucisse", "cabillaud"),
    ),
    (
        "Boissons",
        ("eau", "jus", "vin", "biere", "soda", "coca", "the", "limonade", "sirop"),
    ),
    (
        "Maison & Hygiène",
        (
            "papier",
            "lessive",
            "savon",
            "eponge",
            "sac",
            "poubelle",
            "dentifrice",
            "shampoing",
            "gel douche",
            "javel",
            "sopalin",
            "essuie-tout",
            "deodorant",
            "mouchoir",
        ),
    ),
    (
        "Épicerie",
        (
            "pate",
            "riz",
            "cafe",
            "huile",
            "sucre",
            "farine",
            "sauce",
            "chocolat",
            "conserve",
            "sel",
            "poivre",
            "vinaigre",
            "lentille",
            "pois",
            "cereale",
            "confiture",
            "miel",
            "biscuit",
            "chips",
        ),
    ),
]


def _fold_ascii(text: str) -> str:
    """Lowercase and strip accents/ligatures for keyword matching."""
    replaced = text.lower().replace("œ", "oe").replace("æ", "ae")
    decomposed = unicodedata.normalize("NFKD", replaced)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


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


def compute_due_date(due_label: str, today: date | None = None) -> str:
    """Compute an ISO YYYY-MM-DD date from a due bucket label or weekday."""
    ref = today or date.today()
    label = (due_label or "today").strip().lower()
    if label == "tomorrow":
        return (ref + timedelta(days=1)).isoformat()
    if label == "weekend":
        days_until_sat = (5 - ref.weekday()) % 7
        return (ref + timedelta(days=days_until_sat)).isoformat()
    if label == "later":
        return (ref + timedelta(days=7)).isoformat()
    if label in WEEKDAY_INDEX:
        delta = (WEEKDAY_INDEX[label] - ref.weekday()) % 7
        return (ref + timedelta(days=delta)).isoformat()
    return ref.isoformat()


def infer_aisle(title_text: str, category: str) -> str:
    """Infer supermarket aisle for grocery tasks; returns '' for non-grocery tasks."""
    if category != "courses":
        return ""
    folded = _fold_ascii(title_text)
    for aisle_name, keywords in AISLE_KEYWORDS:
        for kw in keywords:
            if re.search(rf"(?<!\w){re.escape(kw)}", folded):
                return aisle_name
    return "Autre"


def parse_quick_add(raw_text: str) -> dict[str, Any]:
    """
    Parse a natural quick-add string into structured task fields without an LLM.
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

    recurring = False
    recurrence_rule = "none"
    for pattern, rule in RECURRENCE_PATTERNS:
        if pattern.search(working):
            recurring = True
            recurrence_rule = rule
            working = pattern.sub("", working)
            break

    quantity = ""
    m_qty = QUANTITY_RE.search(working)
    if m_qty:
        quantity = re.sub(r"\s+", "", m_qty.group(0)) if m_qty.group(0).lower().startswith("x") else m_qty.group(0).strip()
        working = QUANTITY_RE.sub("", working, count=1)

    clean_title = re.sub(r"\s{2,}", " ", working).strip(" ,;-")
    if not clean_title:
        clean_title = (raw_text or "").strip() or "Untitled task"

    aisle = infer_aisle(clean_title, category)
    due_date = compute_due_date(due_label)

    return {
        "title": clean_title,
        "assignee": assignee,
        "category": category,
        "priority": priority,
        "due_label": due_label,
        "due_date": due_date,
        "recurring": recurring,
        "recurrence_rule": recurrence_rule,
        "quantity": quantity,
        "aisle": aisle,
    }
