import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from app.core.database import SCHEMA
from app.services import scenic_service
from app.services.tpt_jingdian_importer import import_tpt_jingdian_sql


SAMPLE_SQL = """SET FOREIGN_KEY_CHECKS=0;
INSERT INTO `tpt_data_jingdian` VALUES ('1', '北京动物园', '', '西直门外大街137号', '风景名胜;公园广场;动物园', '110108', 'B000A81FAR', '116.333487', '39.944157', '116.327336', '39.942834');
INSERT INTO `tpt_data_jingdian` VALUES ('2', '丽江古城', '', '丽江市古城区', '风景名胜;世界遗产;古镇古村', '530702', 'B000A00002', '100.234', '26.872', '100.229', '26.872');
INSERT INTO `tpt_data_jingdian` VALUES ('3', '玉龙雪山游客中心', '', '玉龙纳西族自治县', '风景名胜;国家级景点;山岳', '530721', 'B000A00003', '100.259', '27.104', '100.254', '27.104');
"""


class ScenicNationalSourceTest(unittest.TestCase):
    def make_db(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tpt_data_jingdian.sql"
            path.write_text(SAMPLE_SQL, encoding="utf-8")
            import_tpt_jingdian_sql(conn, path, batch_size=2)
        return conn

    def patch_db(self, conn):
        @contextmanager
        def db_context():
            yield conn

        return patch.object(scenic_service, "get_db", db_context)

    def test_list_scenic_includes_national_source_without_filter(self):
        conn = self.make_db()
        with self.patch_db(conn):
            items = scenic_service.list_scenic(limit=10)
            total = scenic_service.count_scenic()

        self.assertGreaterEqual(total, 3)
        self.assertTrue(any(item["id"] == "jingdian-2" for item in items))

    def test_list_scenic_filters_national_source_by_three_level_region(self):
        conn = self.make_db()
        with self.patch_db(conn):
            items = scenic_service.list_scenic(province="云南省", city="丽江市", district="古城区", limit=10)
            total = scenic_service.count_scenic(province="云南省", city="丽江市", district="古城区")

        self.assertEqual(total, 1)
        self.assertEqual(items[0]["name"], "丽江古城")

    def test_get_jingdian_detail_returns_normalized_source_profile(self):
        conn = self.make_db()
        with self.patch_db(conn):
            detail = scenic_service.get_scenic_source_detail("jingdian-3")

        self.assertEqual(detail["id"], "jingdian-3")
        self.assertEqual(detail["name"], "玉龙雪山游客中心")
        self.assertEqual(detail["province"], "云南省")
        self.assertEqual(detail["city"], "丽江市")
        self.assertEqual(detail["district"], "玉龙纳西族自治县")


if __name__ == "__main__":
    unittest.main()
