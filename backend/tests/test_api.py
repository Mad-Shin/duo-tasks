"""
Comprehensive deterministic test suite for DuoTasks v2.0:
- Quick-Add parser (assignees, categories, priorities, due dates, recurrence, quantities, aisles)
- REST CRUD, filtering, search, notes & task drawer updates
- Subtasks checklist lifecycle
- Supermarket staples seeding, creation & 1-tap quick-add
- Routine packs (list, apply, deduplicate) & daily routine reset
- Couple balance analytics & activity log
- WebSocket live sync & PWA static assets
"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.main import _INITIALIZED_URLS, app  # noqa: E402
from backend.app.parser import parse_quick_add  # noqa: E402


class TestQuickAddParser(unittest.TestCase):
    def test_parse_full_french_todoist_syntax(self) -> None:
        parsed = parse_quick_add("Acheter du lait demain @wife #courses !1")
        self.assertEqual(parsed["title"], "Acheter du lait")
        self.assertEqual(parsed["assignee"], "wife")
        self.assertEqual(parsed["category"], "courses")
        self.assertEqual(parsed["priority"], 1)
        self.assertEqual(parsed["due_label"], "tomorrow")
        self.assertEqual(parsed["aisle"], "Frais & Laitier")

    def test_parse_defaults_and_english_aliases(self) -> None:
        parsed = parse_quick_add("Sortir les poubelles")
        self.assertEqual(parsed["title"], "Sortir les poubelles")
        self.assertEqual(parsed["assignee"], "both")
        self.assertEqual(parsed["category"], "inbox")
        self.assertEqual(parsed["priority"], 3)
        self.assertEqual(parsed["due_label"], "today")
        self.assertFalse(parsed["recurring"])
        self.assertEqual(parsed["recurrence_rule"], "none")
        self.assertEqual(parsed["aisle"], "")

        parsed_en = parse_quick_add("Pay rent @moi #home !2 weekend")
        self.assertEqual(parsed_en["title"], "Pay rent")
        self.assertEqual(parsed_en["assignee"], "me")
        self.assertEqual(parsed_en["category"], "home")
        self.assertEqual(parsed_en["priority"], 2)
        self.assertEqual(parsed_en["due_label"], "weekend")
        self.assertFalse(parsed_en["recurring"])

    def test_parse_recurring_rules(self) -> None:
        parsed_fr = parse_quick_add("Sortir le chien tous les jours @me #daily")
        self.assertEqual(parsed_fr["title"], "Sortir le chien")
        self.assertTrue(parsed_fr["recurring"])
        self.assertEqual(parsed_fr["recurrence_rule"], "daily")

        parsed_en = parse_quick_add("Take vitamins every day @both")
        self.assertEqual(parsed_en["title"], "Take vitamins")
        self.assertTrue(parsed_en["recurring"])
        self.assertEqual(parsed_en["recurrence_rule"], "daily")

        parsed_wk = parse_quick_add("Nettoyer frigo hebdo @wife #maison")
        self.assertEqual(parsed_wk["title"], "Nettoyer frigo")
        self.assertTrue(parsed_wk["recurring"])
        self.assertEqual(parsed_wk["recurrence_rule"], "weekly")

        parsed_mo = parse_quick_add("Payer loyer mensuel @me #admin")
        self.assertEqual(parsed_mo["title"], "Payer loyer")
        self.assertTrue(parsed_mo["recurring"])
        self.assertEqual(parsed_mo["recurrence_rule"], "monthly")

    def test_parse_grocery_quantity_and_aisle(self) -> None:
        p1 = parse_quick_add("Lait demi-écrémé 2L @both #courses !2")
        self.assertEqual(p1["title"], "Lait demi-écrémé")
        self.assertEqual(p1["quantity"], "2L")
        self.assertEqual(p1["aisle"], "Frais & Laitier")

        p2 = parse_quick_add("Gâteau au chocolat #courses")
        self.assertEqual(p2["aisle"], "Épicerie")

        p3 = parse_quick_add("Baguette x2 #courses")
        self.assertEqual(p3["title"], "Baguette")
        self.assertEqual(p3["quantity"], "x2")
        self.assertEqual(p3["aisle"], "Boulangerie")

    def test_parse_weekdays_french_and_english(self) -> None:
        p_fr = parse_quick_add("Resto italien 20h vendredi @both #date !2")
        self.assertEqual(p_fr["title"], "Resto italien 20h")
        self.assertEqual(p_fr["due_label"], "vendredi")
        self.assertEqual(p_fr["category"], "date")
        self.assertRegex(p_fr["due_date"], r"^\d{4}-\d{2}-\d{2}$")

        p_en = parse_quick_add("Sport monday @me #daily")
        self.assertEqual(p_en["title"], "Sport")
        self.assertEqual(p_en["due_label"], "lundi")

        p_lisa = parse_quick_add("Appeler fleuriste @lisa #date")
        self.assertEqual(p_lisa["assignee"], "wife")
        self.assertEqual(p_lisa["title"], "Appeler fleuriste")


class TestTasksAPIAndPWA(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._prev_db_url = os.environ.get("DATABASE_URL")
        db_file = Path(self._tmp.name) / "test_duo_tasks.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
        _INITIALIZED_URLS.clear()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        if self._prev_db_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self._prev_db_url
        self._tmp.cleanup()

    def test_health_and_parse_preview(self) -> None:
        r_health = self.client.get("/api/health")
        self.assertEqual(r_health.status_code, 200)
        health = r_health.json()
        self.assertEqual(health["status"], "ok")
        self.assertEqual(health["db_mode"], "sqlite")
        self.assertIsInstance(health["connected_devices"], int)

        r_parse = self.client.post("/api/parse", json={"raw_input": "Pain x2 @me #courses !2 demain tous les jours"})
        self.assertEqual(r_parse.status_code, 200)
        data = r_parse.json()
        self.assertEqual(data["title"], "Pain")
        self.assertEqual(data["assignee"], "me")
        self.assertEqual(data["category"], "courses")
        self.assertEqual(data["priority"], 2)
        self.assertEqual(data["due_label"], "tomorrow")
        self.assertEqual(data["quantity"], "x2")
        self.assertEqual(data["aisle"], "Boulangerie")
        self.assertTrue(data["recurring"])

    def test_crud_lifecycle_and_filters(self) -> None:
        r_create = self.client.post(
            "/api/tasks",
            json={"raw_input": "Acheter du lait demain @wife #courses !1"},
        )
        self.assertEqual(r_create.status_code, 201)
        created = r_create.json()
        task_id = created["id"]
        self.assertEqual(created["title"], "Acheter du lait")
        self.assertEqual(created["assignee"], "wife")
        self.assertEqual(created["category"], "courses")
        self.assertEqual(created["priority"], 1)
        self.assertEqual(created["aisle"], "Frais & Laitier")
        self.assertFalse(created["completed"])

        self.client.post("/api/tasks", json={"raw_input": "Vider lave-vaisselle @me #maison !3"})

        r_all = self.client.get("/api/tasks")
        self.assertEqual(r_all.status_code, 200)
        self.assertEqual(len(r_all.json()), 2)

        r_wife = self.client.get("/api/tasks", params={"assignee": "wife", "category": "courses"})
        self.assertEqual(r_wife.status_code, 200)
        self.assertEqual(len(r_wife.json()), 1)
        self.assertEqual(r_wife.json()[0]["id"], task_id)

        r_patch = self.client.patch(f"/api/tasks/{task_id}", json={"completed": True, "completed_by": "wife"})
        self.assertEqual(r_patch.status_code, 200)
        self.assertTrue(r_patch.json()["completed"])
        self.assertEqual(r_patch.json()["completed_by"], "wife")

        r_del = self.client.delete(f"/api/tasks/{task_id}")
        self.assertEqual(r_del.status_code, 200)
        self.assertTrue(r_del.json()["deleted"])

        r_missing = self.client.patch(f"/api/tasks/{task_id}", json={"completed": False})
        self.assertEqual(r_missing.status_code, 404)

    def test_search_and_task_drawer_updates(self) -> None:
        r1 = self.client.post(
            "/api/tasks",
            json={"raw_input": "Prendre café @both #courses", "notes": "Grain torréfaction moyenne"},
        )
        tid = r1.json()["id"]
        self.client.post("/api/tasks", json={"raw_input": "Appeler syndic @me #admin"})

        r_search = self.client.get("/api/tasks", params={"search": "torréfaction"})
        self.assertEqual(r_search.status_code, 200)
        self.assertEqual(len(r_search.json()), 1)
        self.assertEqual(r_search.json()[0]["id"], tid)

        r_upd = self.client.patch(
            f"/api/tasks/{tid}",
            json={"notes": "Arabica bio", "quantity": "500g", "recurrence_rule": "weekly"},
        )
        self.assertEqual(r_upd.status_code, 200)
        body = r_upd.json()
        self.assertEqual(body["notes"], "Arabica bio")
        self.assertEqual(body["quantity"], "500g")
        self.assertTrue(body["recurring"])
        self.assertEqual(body["recurrence_rule"], "weekly")

    def test_subtasks_checklist_lifecycle(self) -> None:
        r_task = self.client.post("/api/tasks", json={"raw_input": "Préparer valises @both #weekend"})
        tid = r_task.json()["id"]

        r_add1 = self.client.post(f"/api/tasks/{tid}/subtasks", json={"text": "Chargeurs USB-C"})
        self.assertEqual(r_add1.status_code, 200)
        self.assertEqual(len(r_add1.json()["subtasks"]), 1)
        sub_id = r_add1.json()["subtasks"][0]["id"]

        r_add2 = self.client.post(f"/api/tasks/{tid}/subtasks", json={"text": "Passeports"})
        self.assertEqual(len(r_add2.json()["subtasks"]), 2)

        r_toggle = self.client.patch(f"/api/tasks/{tid}/subtasks/{sub_id}", json={"done": True})
        self.assertEqual(r_toggle.status_code, 200)
        self.assertTrue(r_toggle.json()["subtasks"][0]["done"])

        r_del_sub = self.client.delete(f"/api/tasks/{tid}/subtasks/{sub_id}")
        self.assertEqual(r_del_sub.status_code, 200)
        self.assertEqual(len(r_del_sub.json()["subtasks"]), 1)

    def test_recurring_persistence_and_scoped_clear_completed(self) -> None:
        r_rec = self.client.post("/api/tasks", json={"raw_input": "Arroser plantes tous les jours @both #maison"})
        rec_id = r_rec.json()["id"]
        self.assertTrue(r_rec.json()["recurring"])

        r_course = self.client.post("/api/tasks", json={"raw_input": "Tomates @both #courses"})
        c_id = r_course.json()["id"]
        self.client.patch(f"/api/tasks/{c_id}", json={"completed": True})
        self.client.patch(f"/api/tasks/{rec_id}", json={"completed": True})

        # Scoped clear for courses only
        r_clear_courses = self.client.post("/api/tasks/clear-completed", params={"category": "courses"})
        self.assertEqual(r_clear_courses.status_code, 200)
        self.assertEqual(r_clear_courses.json(), {"cleared_count": 1})

        # Maison completed task still remains until global clear
        self.assertEqual(len(self.client.get("/api/tasks").json()), 1)
        r_clear_all = self.client.post("/api/tasks/clear-completed")
        self.assertEqual(r_clear_all.json(), {"cleared_count": 1})
        self.assertEqual(len(self.client.get("/api/tasks").json()), 0)

    def test_grocery_staples_seeded_create_and_quick_add(self) -> None:
        r_staples = self.client.get("/api/groceries/staples")
        self.assertEqual(r_staples.status_code, 200)
        staples = r_staples.json()
        self.assertGreaterEqual(len(staples), 24)

        r_new = self.client.post(
            "/api/groceries/staples",
            json={"name": "Mozzarella di bufala", "aisle": "Frais & Laitier", "default_qty": "x2", "emoji": "🧀"},
        )
        self.assertEqual(r_new.status_code, 201)
        sid = r_new.json()["id"]

        r_qa = self.client.post(f"/api/groceries/staples/{sid}/quick-add")
        self.assertEqual(r_qa.status_code, 200)
        added_task = r_qa.json()
        self.assertEqual(added_task["title"], "Mozzarella di bufala")
        self.assertEqual(added_task["category"], "courses")
        self.assertEqual(added_task["quantity"], "x2")

        # Calling quick-add again while still active should not duplicate
        r_qa2 = self.client.post(f"/api/groceries/staples/{sid}/quick-add")
        self.assertEqual(r_qa2.json()["id"], added_task["id"])

    def test_routine_packs_and_daily_reset(self) -> None:
        r_packs = self.client.get("/api/routines/packs")
        self.assertEqual(r_packs.status_code, 200)
        packs = r_packs.json()
        self.assertGreaterEqual(len(packs), 5)

        r_date_pack = self.client.post("/api/routines/packs/date-night-apero/apply")
        self.assertEqual(r_date_pack.status_code, 200)
        self.assertEqual(r_date_pack.json()["added_count"], 4)

        r_apply = self.client.post("/api/routines/packs/routine-quotidienne/apply")
        self.assertEqual(r_apply.status_code, 200)
        self.assertEqual(r_apply.json()["added_count"], 3)

        # Applying again while active adds 0 duplicates
        r_apply2 = self.client.post("/api/routines/packs/routine-quotidienne/apply")
        self.assertEqual(r_apply2.json()["added_count"], 0)

        # Complete all 3 daily routines, then reset
        tasks = [t for t in self.client.get("/api/tasks").json() if t["recurring"]]
        for t in tasks:
            self.client.patch(f"/api/tasks/{t['id']}", json={"completed": True, "completed_by": "me"})

        r_reset = self.client.post("/api/routines/reset-daily")
        self.assertEqual(r_reset.status_code, 200)
        self.assertEqual(r_reset.json()["reset_count"], 3)

        after = [t for t in self.client.get("/api/tasks").json() if t["recurring"]]
        self.assertTrue(all(not t["completed"] for t in after))

    def test_couple_profile_love_note_and_kudos(self) -> None:
        r_prof = self.client.get("/api/couple/profile")
        self.assertEqual(r_prof.status_code, 200)
        self.assertEqual(r_prof.json()["me_name"], "Valentin")
        self.assertEqual(r_prof.json()["kudos_count"], 0)
        self.assertIsInstance(r_prof.json()["preset_tasks"], list)
        self.assertGreaterEqual(len(r_prof.json()["preset_tasks"]), 2)

        r_upd = self.client.patch(
            "/api/couple/profile",
            json={
                "wife_name": "Emma",
                "wife_emoji": "🌻",
                "love_note": "Apéro à 19h30 ?",
                "love_note_author": "me",
                "preset_tasks": ["Deep clean frigo", "Laver les vitres"],
            },
        )
        self.assertEqual(r_upd.status_code, 200)
        self.assertEqual(r_upd.json()["wife_name"], "Emma")
        self.assertEqual(r_upd.json()["wife_emoji"], "🌻")
        self.assertEqual(r_upd.json()["love_note"], "Apéro à 19h30 ?")
        self.assertEqual(r_upd.json()["preset_tasks"], ["Deep clean frigo", "Laver les vitres"])

        r_prof2 = self.client.get("/api/couple/profile")
        self.assertEqual(r_prof2.status_code, 200)
        self.assertEqual(r_prof2.json()["preset_tasks"], ["Deep clean frigo", "Laver les vitres"])

        r_kudos = self.client.post(
            "/api/couple/kudos",
            json={"from_partner": "wife", "message": "Trop hâte ❤️"},
        )
        self.assertEqual(r_kudos.status_code, 200)
        self.assertEqual(r_kudos.json()["kudos_count"], 1)

        r_stats = self.client.get("/api/stats")
        self.assertEqual(r_stats.status_code, 200)
        self.assertEqual(r_stats.json()["extra"]["kudos_count"], 1)
        self.assertGreaterEqual(r_stats.json()["extra"]["couple_score"], 15)

    def test_event_creation_filtering_and_ics_export(self) -> None:
        r_ev = self.client.post(
            "/api/tasks",
            json={
                "raw_input": "Mariage Paul & Marie",
                "item_type": "event",
                "event_date": "2026-12-05",
                "event_time": "15:00",
                "location": "Château de Vincennes",
                "category": "date",
            },
        )
        self.assertEqual(r_ev.status_code, 201)
        ev = r_ev.json()
        self.assertEqual(ev["item_type"], "event")
        self.assertEqual(ev["event_date"], "2026-12-05")
        self.assertEqual(ev["event_time"], "15:00")
        self.assertEqual(ev["location"], "Château de Vincennes")

        # Filter by item_type=event
        self.client.post("/api/tasks", json={"raw_input": "Sortir poubelles @me"})
        r_filtered = self.client.get("/api/tasks", params={"item_type": "event"})
        self.assertEqual(r_filtered.status_code, 200)
        self.assertEqual(len(r_filtered.json()), 1)
        self.assertEqual(r_filtered.json()[0]["id"], ev["id"])

        # Download .ics for Apple Calendar
        r_ics = self.client.get(f"/api/tasks/{ev['id']}/ics")
        self.assertEqual(r_ics.status_code, 200)
        self.assertIn("text/calendar", r_ics.headers["content-type"])
        self.assertIn("BEGIN:VCALENDAR", r_ics.text)
        self.assertIn("SUMMARY:Mariage Paul & Marie", r_ics.text)
        self.assertIn("LOCATION:Château de Vincennes", r_ics.text)
        self.assertIn("DTSTART:20261205T150000", r_ics.text)

    def test_couple_stats_and_activity_log(self) -> None:
        t1 = self.client.post("/api/tasks", json={"raw_input": "Courses @both #courses !1"}).json()
        self.client.post("/api/tasks", json={"raw_input": "Facture @me #admin !2"})
        self.client.patch(f"/api/tasks/{t1['id']}", json={"completed": True, "completed_by": "wife"})

        r_stats = self.client.get("/api/stats")
        self.assertEqual(r_stats.status_code, 200)
        stats = r_stats.json()
        self.assertEqual(stats["total_active"], 1)
        self.assertEqual(stats["total_completed"], 1)
        self.assertEqual(stats["completed_by_actor"]["wife"], 1)
        self.assertGreaterEqual(len(stats["recent_activity"]), 3)

    def test_websocket_receives_sync_broadcast(self) -> None:
        with self.client.websocket_connect("/ws") as ws:
            health_live = self.client.get("/api/health").json()
            self.assertEqual(health_live["connected_devices"], 1)

            r_post = self.client.post("/api/tasks", json={"raw_input": "Test sync @both #daily"})
            self.assertEqual(r_post.status_code, 201)
            msg = ws.receive_json()
            self.assertEqual(msg["event"], "sync")
            self.assertEqual(msg["action"], "created")
            self.assertEqual(msg["task_id"], r_post.json()["id"])

    def test_pwa_static_assets_served(self) -> None:
        r_root = self.client.get("/")
        self.assertEqual(r_root.status_code, 200)
        self.assertIn("DuoTasks", r_root.text)
        self.assertIn('rel="manifest"', r_root.text)
        self.assertIn("apple-mobile-web-app-capable", r_root.text)

        r_manifest = self.client.get("/manifest.json")
        self.assertEqual(r_manifest.status_code, 200)
        manifest = r_manifest.json()
        self.assertEqual(manifest["short_name"], "DuoTasks")
        self.assertEqual(manifest["display"], "standalone")

    def test_legacy_schema_auto_migration(self) -> None:
        with tempfile.TemporaryDirectory() as legacy_dir:
            legacy_db = Path(legacy_dir) / "legacy.db"
            conn = sqlite3.connect(str(legacy_db))
            conn.execute(
                """
                CREATE TABLE tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    raw_input TEXT NOT NULL,
                    assignee TEXT NOT NULL DEFAULT 'both',
                    category TEXT NOT NULL DEFAULT 'inbox',
                    priority INTEGER NOT NULL DEFAULT 3,
                    due_label TEXT NOT NULL DEFAULT 'today',
                    completed INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "INSERT INTO tasks (title, raw_input, created_at) VALUES (?, ?, ?)",
                ("Legacy task", "Legacy task", "2026-11-15T10:00:00+00:00"),
            )
            conn.commit()
            conn.close()

            prev_url = os.environ.get("DATABASE_URL")
            try:
                os.environ["DATABASE_URL"] = f"sqlite:///{legacy_db}"
                _INITIALIZED_URLS.clear()
                with TestClient(app) as legacy_client:
                    r = legacy_client.get("/api/tasks")
                    self.assertEqual(r.status_code, 200)
                    tasks = r.json()
                    self.assertEqual(len(tasks), 1)
                    self.assertEqual(tasks[0]["title"], "Legacy task")
                    self.assertEqual(tasks[0]["subtasks"], [])
                    self.assertEqual(tasks[0]["recurrence_rule"], "none")
            finally:
                if prev_url is None:
                    os.environ.pop("DATABASE_URL", None)
                else:
                    os.environ["DATABASE_URL"] = prev_url
                _INITIALIZED_URLS.clear()


if __name__ == "__main__":
    unittest.main(verbosity=2)
