import sqlite3
import unittest

from app.core.database import SCHEMA, migrate_db


class DatabaseMigrationTest(unittest.TestCase):
    def test_legacy_tpt_table_gets_location_columns_before_indexes(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute(
            """
            CREATE TABLE tpt_jingdian (
              source_id INTEGER PRIMARY KEY,
              name TEXT NOT NULL,
              phone TEXT DEFAULT '',
              address TEXT DEFAULT '',
              category_path TEXT DEFAULT '',
              category TEXT DEFAULT '',
              areaid TEXT DEFAULT '',
              province_code TEXT DEFAULT '',
              city_code TEXT DEFAULT '',
              district_code TEXT DEFAULT '',
              poiid TEXT DEFAULT '',
              gcj_lng REAL,
              gcj_lat REAL,
              longitude REAL,
              latitude REAL,
              search_text TEXT DEFAULT '',
              created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            INSERT INTO tpt_jingdian (
              source_id, name, address, category_path, category, areaid,
              province_code, city_code, district_code, longitude, latitude, search_text
            ) VALUES (1, '清西陵', '易县', '风景名胜;风景名胜;国家级景点', '国家级景点',
              '130633', '13', '1306', '130633', 115.36, 39.35, '清西陵 易县')
            """
        )

        conn.executescript(SCHEMA)
        conn.execute(
            """
            INSERT INTO regions (region_group, province, city, district, sort_order)
            VALUES ('华北', '河北省', '1306地区', '130633区县', 1)
            """
        )
        conn.execute(
            """
            INSERT INTO regions (region_group, province, city, district, sort_order)
            VALUES ('其他', '73省级区域', '7303地区', '730300区县', 1)
            """
        )
        migrate_db(conn)

        columns = {row["name"] for row in conn.execute("PRAGMA table_info(tpt_jingdian)").fetchall()}
        indexes = {row["name"] for row in conn.execute("PRAGMA index_list(tpt_jingdian)").fetchall()}
        jingdian = conn.execute("SELECT province, city, district FROM tpt_jingdian WHERE source_id=1").fetchone()
        good_region = conn.execute(
            "SELECT 1 FROM regions WHERE province='河北省' AND city='保定市' AND district='易县'"
        ).fetchone()
        bad_region = conn.execute(
            "SELECT 1 FROM regions WHERE province='河北省' AND city='1306地区' AND district='130633区县'"
        ).fetchone()
        bad_unknown_region = conn.execute(
            "SELECT 1 FROM regions WHERE province='73省级区域' AND city='7303地区' AND district='730300区县'"
        ).fetchone()

        self.assertIn("province", columns)
        self.assertIn("city", columns)
        self.assertIn("district", columns)
        self.assertEqual(jingdian["province"], "河北省")
        self.assertEqual(jingdian["city"], "保定市")
        self.assertEqual(jingdian["district"], "易县")
        self.assertIsNotNone(good_region)
        self.assertIsNone(bad_region)
        self.assertIsNone(bad_unknown_region)
        self.assertIn("idx_tpt_jingdian_province", indexes)
        self.assertIn("idx_tpt_jingdian_city", indexes)
        self.assertIn("idx_tpt_jingdian_district", indexes)


if __name__ == "__main__":
    unittest.main()
