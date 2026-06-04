import sqlite3
import unittest
from unittest.mock import patch

from app.routers import public_content


class DbContext:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        return False


class PublicContentTest(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """
            CREATE TABLE articles (
              id INTEGER PRIMARY KEY,
              title TEXT,
              content TEXT,
              category TEXT,
              author TEXT,
              cover_image TEXT,
              is_published INTEGER,
              created_at TEXT
            )
            """
        )
        self.conn.executemany(
            """
            INSERT INTO articles (id, title, content, category, author, cover_image, is_published, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (1, "公开指南", "正文", "攻略", "管理员", "", 1, "2026-06-01"),
                (2, "草稿指南", "草稿", "攻略", "管理员", "", 0, "2026-06-01"),
            ],
        )

    def tearDown(self):
        self.conn.close()

    def test_get_article_only_returns_published_article(self):
        with patch.object(public_content, "get_db", lambda: DbContext(self.conn)):
            published = public_content.get_article(1)
            draft = public_content.get_article(2)

        self.assertTrue(published["success"])
        self.assertEqual(published["data"]["title"], "公开指南")
        self.assertFalse(draft["success"])


if __name__ == "__main__":
    unittest.main()
