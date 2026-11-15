"""
Deterministic test suite for DuoTasks (Quick-Add parser, REST CRUD, WebSocket sync, and PWA assets).
"""

from __future__ import annotations

import os
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

    def test_parse_defaults_and_english_aliases(self) -> None:
        parsed = parse_quick_add("Sortir les poubelles")
        self.assertEqual(parsed["title"], "Sortir les poubelles")
        self.assertEqual(parsed["assignee"], "both")
        self.assertEqual(parsed["category"], "inbox")
        self.assertEqual(parsed["priority"], 3)
        self.assertEqual(parsed["due_label"], "today")

        parsed_en = parse_quick_add("Pay rent @moi #home !2 weekend")
        self.assertEqual(parsed_en["title"], "Pay rent")
        self.assertEqual(parsed_en["assignee"], "me")
        self.assertEqual(parsed_en["category"], "home")
        self.assertEqual(parsed_en["priority"], 2)
        self.assertEqual(parsed_en["due_label"], "weekend")


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
        self.assertEqual(r_health.json()["status"], "ok")
        self.assertEqual(r_health.json()["db_mode"], "sqlite")

        r_parse = self.client.post("/api/parse", json={"raw_input": "Pain @me #courses !2 demain"})
        self.assertEqual(r_parse.status_code, 200)
        data = r_parse.json()
        self.assertEqual(data["title"], "Pain")
        self.assertEqual(data["assignee"], "me")
        self.assertEqual(data["category"], "courses")
        self.assertEqual(data["priority"], 2)
        self.assertEqual(data["due_label"], "tomorrow")

    def test_crud_lifecycle_and_filters(self) -> None:
        # Create
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
        self.assertFalse(created["completed"])

        # Create a second task for filter checks
        self.client.post("/api/tasks", json={"raw_input": "Vider lave-vaisselle @me #maison !3"})

        # List & filter
        r_all = self.client.get("/api/tasks")
        self.assertEqual(r_all.status_code, 200)
        self.assertEqual(len(r_all.json()), 2)

        r_wife = self.client.get("/api/tasks", params={"assignee": "wife", "category": "courses"})
        self.assertEqual(r_wife.status_code, 200)
        self.assertEqual(len(r_wife.json()), 1)
        self.assertEqual(r_wife.json()[0]["id"], task_id)

        # Update (mark completed)
        r_patch = self.client.patch(f"/api/tasks/{task_id}", json={"completed": True})
        self.assertEqual(r_patch.status_code, 200)
        self.assertTrue(r_patch.json()["completed"])

        # Delete
        r_del = self.client.delete(f"/api/tasks/{task_id}")
        self.assertEqual(r_del.status_code, 200)
        self.assertTrue(r_del.json()["deleted"])

        r_after = self.client.get("/api/tasks")
        self.assertEqual(len(r_after.json()), 1)

        # 404 on missing task
        r_missing = self.client.patch(f"/api/tasks/{task_id}", json={"completed": False})
        self.assertEqual(r_missing.status_code, 404)

    def test_websocket_receives_sync_broadcast(self) -> None:
        with self.client.websocket_connect("/ws") as ws:
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
