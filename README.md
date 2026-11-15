# DuoTasks — Shared Couple Todoist PWA

A clean, zero-App-Store shared daily task and grocery web app built for **iPhone + Android Home Screens** and designed as a hands-on **Python FastAPI Backend Training** project.

## Repository Structure

```text
duo-tasks/
├── backend/
│   ├── app/
│   │   ├── database.py   # SQLite (local) / PostgreSQL (cloud) dual adapter
│   │   ├── main.py       # FastAPI REST endpoints + WebSocket /ws live sync
│   │   ├── models.py     # Pydantic v2 input/output contracts
│   │   └── parser.py     # Deterministic Todoist Quick-Add parser
│   └── tests/
│       └── test_api.py   # Automated parser, CRUD & PWA test suite
├── frontend/             # Zero-build installable PWA (iOS Safari + Android Chrome)
│   ├── index.html
│   ├── styles.css
│   ├── app.js
│   ├── manifest.json
│   ├── sw.js
│   └── icon.svg
├── COACHING_ROADMAP.md   # 5-lesson guided backend training challenges
├── render.yaml           # Free Render + Neon Postgres cloud blueprint
└── requirements.txt
```

## Quick Start (Local PC & Home Wi-Fi)

```powershell
# 1. Start the FastAPI + PWA server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# 2. Open on PC
#    App: http://localhost:8000
#    Interactive API Docs: http://localhost:8000/docs

# 3. Open on iPhone / Android (same Wi-Fi)
#    http://<YOUR-PC-LOCAL-IP>:8000
```

## Run Tests

```powershell
python -m pytest backend/tests/test_api.py
```

## Quick-Add Syntax

- `@wife` / `@elle` / `@me` / `@moi` / `@both` — Assign owner
- `#courses` / `#maison` / `#daily` — Tag category
- `!1` (urgent), `!2` (high), `!3` (normal) — Set priority
- `demain` / `tomorrow` / `weekend` — Set due bucket
