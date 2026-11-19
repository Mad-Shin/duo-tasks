# DuoTasks — Shared Couple Tasks, Groceries & Routines PWA

A full-featured, zero-App-Store shared couple web application built for **iPhone Safari + Android Chrome Home Screens** with real-time WebSocket sync, SQLite/PostgreSQL persistence, Supermarket Mode, Recurring Routines & Packs, Subtasks, and Couple Balance analytics.

## Features
- **📋 Tasks (Todoist-Style Quick-Add)**: Natural syntax (`Lait 2L demain @wife #courses !1 tous les jours`) parsed deterministically in `<0.1ms` with live preview chips, search, category/due/assignee filters, and dark mode.
- **📝 Task Detail Drawer & Subtasks**: Tap any task to edit title, notes, assignee, category, priority, due bucket, recurrence rule, quantity, supermarket aisle, and an interactive subtasks checklist.
- **🛒 Supermarket Mode (`#courses`)**: Pre-seeded 20-item 1-tap *Garde-Manger* staples grid, custom favorites, automatic aisle classification (*Fruits & Légumes*, *Frais & Laitier*, *Boulangerie*, etc.), and aisle-grouped shopping list.
- **🔁 Routines & 1-Tap Couple Packs**: Daily/weekly/monthly recurring tasks, 1-click daily routine reset, and built-in couple packs (*Courses Essentielles*, *Ménage Week-end*, *Routine Quotidienne Couple*, *Départ Week-end / Voyage*).
- **📊 Couple Balance & Activity Feed**: Active vs completed balance (`Moi` vs `Elle` vs `Ensemble`), category breakdown, and live activity feed with per-phone identity switcher.

## Repository Structure

```text
duo-tasks/
├── backend/
│   ├── app/
│   │   ├── database.py   # SQLite (local) / PostgreSQL (cloud) adapter + auto-migration + staples seed
│   │   ├── main.py       # FastAPI REST endpoints + WebSocket /ws live sync
│   │   ├── models.py     # Pydantic v2 input/output contracts
│   │   └── parser.py     # Deterministic Quick-Add, recurrence, quantity & aisle parser
│   └── tests/
│       └── test_api.py   # 15 automated parser, CRUD, subtasks, groceries, routines & PWA tests
├── frontend/             # Installable multi-view PWA (iOS Safari + Android Chrome)
│   ├── index.html
│   ├── styles.css
│   ├── app.js
│   ├── manifest.json
│   ├── sw.js
│   └── icon.svg
├── render.yaml           # Free Render + Neon Postgres cloud blueprint
└── requirements.txt
```

## Quick Start (Local PC & Home Wi-Fi)

```powershell
# 1. Start the FastAPI + PWA server
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

# 2. Open on PC
#    App: http://localhost:8000
#    Interactive API Docs: http://localhost:8000/docs
```

## Run Tests

```powershell
python -m pytest backend/tests/test_api.py -v
```
