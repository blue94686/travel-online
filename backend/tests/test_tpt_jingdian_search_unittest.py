import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.services.tpt_jingdian_importer import import_tpt_jingdian_sql, search_tpt_jingdian


SAMPLE_SQL = """SET FOREIGN_KEY_CHECKS=0;
INSERT INTO `tpt_data_jingdian` VALUES ('1', '礼王府', '', '西黄城根南街9号', '风景名胜;风景名胜;风景名胜', '110102', 'B000A81F8Z', '116.377178', '39.919584', '116.370948', '39.918193');
INSERT INTO `tpt_data_jingdian` VALUES ('2', '北京动物园(北2门)', '', '五塔寺路22号', '风景名胜;公园广场;动物园', '110108', 'B000A81FAR', '116.333487', '39.944157', '116.327336', '39.942834');
INSERT INTO `tpt_data_jingdian` VALUES ('3', '杭州西湖', '', '西湖区龙井路1号', '风景名胜;风景名胜;湖泊', '330106', 'B000A00001', '120.148', '30.236', '120.142', '30.233');
"""


class TptJingdianSearchTest(unittest.TestCase):
    def make_db(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        return conn

    def import_sample(self, conn):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tpt_data_jingdian.sql"
            path.write_text(SAMPLE_SQL, encoding="utf-8")
            return import_tpt_jingdian_sql(conn, path, batch_size=2)

    def test_import_builds_searchable_index_and_returns_paginated_results(self):
        conn = self.make_db()
        imported = self.import_sample(conn)

        result = search_tpt_jingdian(conn, keyword="动物园", limit=10)

        self.assertEqual(imported, 3)
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["limit"], 10)
        self.assertEqual(result["offset"], 0)
        self.assertTrue(result["fts_enabled"])
        self.assertEqual(result["items"][0]["name"], "北京动物园(北2门)")

    def test_search_filters_by_areaid_and_category(self):
        conn = self.make_db()
        self.import_sample(conn)

        result = search_tpt_jingdian(conn, keyword="北京", areaid="1101", category="动物园")

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["areaid"], "110108")
        self.assertEqual(result["items"][0]["category"], "动物园")

    def test_search_prioritizes_exact_main_scenic_name_over_sub_locations(self):
        conn = self.make_db()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tpt_data_jingdian.sql"
            path.write_text(
                """SET FOREIGN_KEY_CHECKS=0;
INSERT INTO `tpt_data_jingdian` VALUES ('1', '北京动物园(东门)', '', '气象路6北京动物园', '风景名胜;公园广场;动物园', '110108', 'B000A8358T', '116.333782', '39.945029', '116.333782', '39.945029');
INSERT INTO `tpt_data_jingdian` VALUES ('2', '北京动物园', '', '西直门外大街137号', '风景名胜;公园广场;动物园', '110102', 'B000A87IUX', '116.329442', '39.939851', '116.329442', '39.939851');
INSERT INTO `tpt_data_jingdian` VALUES ('3', '北京动物园海兽馆', '', '西直门外大街137号北京动物园', '风景名胜;公园广场;动物园', '110102', 'B000A9PIEO', '116.325850', '39.939296', '116.325850', '39.939296');
""",
                encoding="utf-8",
            )
            import_tpt_jingdian_sql(conn, path, batch_size=2)

        result = search_tpt_jingdian(conn, keyword="北京动物园")

        self.assertEqual(result["items"][0]["name"], "北京动物园")


if __name__ == "__main__":
    unittest.main()
