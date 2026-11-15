# DuoTasks — Backend Coaching Roadmap (5 Hands-On Lessons)

This repository is intentionally compact (~350 lines of backend Python) so you can read, break, test, and extend every layer of a real modern web service.

---

## Lesson 1: SQL, Connections & Cloud Portability (`backend/app/database.py`)
**Concepts learned**: SQLite vs PostgreSQL, connection lifecycles, SQL DDL (`CREATE TABLE IF NOT EXISTS`), and environment variables (`DATABASE_URL`).

- **Read**: Open [`backend/app/database.py`](backend/app/database.py) and trace `get_connection()` and `init_db()`. Notice why every request commits and closes its connection in a `try/finally` block, and why `DATABASE_URL` switches cleanly between your local PC (`duo_tasks.db`) and Neon PostgreSQL in the cloud.
- **Hands-on Challenge #1**: Add a `recurring` boolean column (`INTEGER NOT NULL DEFAULT 0` in SQLite / `BOOLEAN NOT NULL DEFAULT FALSE` in Postgres) to the `tasks` table and expose it in [`backend/app/models.py`](backend/app/models.py).

---

## Lesson 2: Deterministic Parsing Before LLMs (`backend/app/parser.py`)
**Concepts learned**: Regular expressions (`re`), word boundaries, normalization dictionaries, and zero-latency input parsing.

- **Read**: Open [`backend/app/parser.py`](backend/app/parser.py) and read `parse_quick_add()`. See how `"Acheter du lait demain @wife #courses !1"` becomes clean structured JSON in `< 0.1ms` with zero API cost.
- **Hands-on Challenge #2**: Add support for a recurrence token (e.g., `"every day"` / `"tous les jours"`) that returns `"recurring": True` and strips the phrase cleanly from `title`.

---

## Lesson 3: REST API Design & Validation (`backend/app/main.py` & `models.py`)
**Concepts learned**: HTTP verbs (`GET`, `POST`, `PATCH`, `DELETE`), status codes (`201 Created`, `404 Not Found`), Pydantic validation, and parameterized SQL queries (`?` / `%s` to block SQL injection).

- **Read**: Open [`backend/app/main.py`](backend/app/main.py) and start the server (`uvicorn backend.app.main:app --reload`), then open `http://localhost:8000/docs` to test every route visually with Swagger UI.
- **Hands-on Challenge #3**: Add a `POST /api/tasks/clear-completed` endpoint that deletes all tasks where `completed = True`, broadcasts a WebSocket sync event, and returns `{"cleared_count": N}`. Write a unit test for it in [`backend/tests/test_api.py`](backend/tests/test_api.py).

---

## Lesson 4: Real-Time Multi-Phone Sync via WebSockets (`/ws`)
**Concepts learned**: Push vs Polling, stateful `ConnectionManager`, and why `PATCH` triggers `manager.broadcast(...)` so your iPhone and your wife's Android update live without refreshing.

- **Read**: Open two browser windows side-by-side at `http://localhost:8000`, add a task in window 1, and watch window 2 update immediately.
- **Hands-on Challenge #4**: Display a subtle toast or counter showing how many devices are currently connected in `/api/health` (`len(manager.active_connections)`).

---

## Lesson 5: Free $0 Cloud Deployment (GitHub + Neon + Render)
**Concepts learned**: Twelve-Factor App config (`$PORT`, `DATABASE_URL`), ephemeral container disks vs managed PostgreSQL, and HTTPS PWA installation on iOS & Android.

1. Push `duo-tasks/` to a private GitHub repo.
2. Create a free PostgreSQL database on **Neon.tech** and copy its `postgresql://...` connection string.
3. Create a free Web Service on **Render** pointing to your repo (it reads [`render.yaml`](render.yaml) automatically) and paste `DATABASE_URL` in Environment Variables.
4. Open your Render `https://...onrender.com` URL on Safari (iPhone) and Chrome (Android) and tap **Add to Home Screen** (`+ Icône` in the top bar).
