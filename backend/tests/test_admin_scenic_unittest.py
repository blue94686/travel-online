import sqlite3
import unittest
from unittest.mock import patch

from app.routers import admin_scenic


class DbContext:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        return False


class AdminScenicListTest(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """
            CREATE TABLE scenic_spots (
              id INTEGER PRIMARY KEY,
              name TEXT,
              province TEXT,
              city TEXT,
              district TEXT,
              level TEXT
            )
            """
        )
        self.conn.executemany(
            "INSERT INTO scenic_spots (id, name, province, city, district, level) VALUES (?, ?, ?, ?, ?, ?)",
            [
                (1, "白石山", "河北省", "保定市", "涞源县", "5A"),
                (2, "清西陵", "河北省", "保定市", "易县", "4A"),
                (3, "西湖", "浙江省", "杭州市", "西湖区", "5A"),
            ],
        )

    def tearDown(self):
        self.conn.close()

    def test_admin_scenic_list_uses_keyword_alias_and_returns_list_payload(self):
        with patch.object(admin_scenic, "get_db", lambda: DbContext(self.conn)):
            response = admin_scenic.admin_scenic_list(keyword="保定", limit=1)

        data = response["data"]
        self.assertTrue(response["success"])
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["limit"], 1)
        self.assertEqual(len(data["list"]), 1)
        self.assertEqual(data["list"][0]["city"], "保定市")


if __name__ == "__main__":
    unittest.main()
