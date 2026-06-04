import sqlite3
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from app.services import admin_service


class AdminDashboardTest(unittest.TestCase):
    def make_db(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(
            """
            CREATE TABLE scenic_spots (id INTEGER PRIMARY KEY, name TEXT);
            CREATE TABLE comments (id INTEGER PRIMARY KEY, scenic_id INTEGER, nickname TEXT, content TEXT, status TEXT);
            CREATE TABLE users (id INTEGER PRIMARY KEY);
            CREATE TABLE scenic_images (id INTEGER PRIMARY KEY, scenic_id INTEGER, url TEXT, status TEXT);
            CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, operator TEXT, module TEXT, action TEXT, result TEXT, created_at TEXT);
            INSERT INTO scenic_spots (id, name) VALUES (1, '杭州西湖');
            INSERT INTO users (id) VALUES (1), (2);
            INSERT INTO scenic_images (id, scenic_id, url, status) VALUES (1, 1, '/images/a.jpg', 'pending');
            INSERT INTO comments (id, scenic_id, nickname, content, status) VALUES (1, 1, '游客', '很好', 'pending');
            """
        )
        return conn

    def test_dashboard_uses_operations_kpi_without_ai_metrics(self):
        conn = self.make_db()

        @contextmanager
        def fake_db():
            yield conn

        with patch.object(admin_service, "get_db", fake_db):
            result = admin_service.dashboard()

        labels = [item["label"] for item in result["kpis"]]

        self.assertIn("待审核数", labels)
        self.assertNotIn("AI调用量", labels)
        self.assertNotIn("AI 调用量", labels)


if __name__ == "__main__":
    unittest.main()
