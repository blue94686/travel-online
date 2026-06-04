import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app.services.scenic_service as scenic_service
from app.services.tpt_jingdian_importer import import_tpt_jingdian_sql


SAMPLE_SQL = """SET FOREIGN_KEY_CHECKS=0;
INSERT INTO `tpt_data_jingdian` VALUES ('1', '礼王府', '', '西黄城根南街9号', '风景名胜;风景名胜;风景名胜', '110102', 'B000A81F8Z', '116.377178', '39.919584', '116.370948', '39.918193');
INSERT INTO `tpt_data_jingdian` VALUES ('2', '北京动物园(北2门)', '', '五塔寺路22号', '风景名胜;公园广场;动物园', '110108', 'B000A81FAR', '116.333487', '39.944157', '116.327336', '39.942834');
INSERT INTO `tpt_data_jingdian` VALUES ('3', '九寨沟瀑布群', '', '九寨沟县漳扎镇', '风景名胜;风景名胜;瀑布', '513225', 'B000JIUZHAI', '103.920', '33.260', '103.918', '33.258');
"""


class ScenicNationalSearchTest(unittest.TestCase):
    def make_db(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(
            """
            CREATE TABLE scenic_spots (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              slug TEXT UNIQUE NOT NULL,
              name TEXT NOT NULL,
              province TEXT NOT NULL,
              city TEXT NOT NULL,
              district TEXT NOT NULL,
              level TEXT,
              rating REAL,
              address TEXT,
              latitude REAL,
              longitude REAL,
              summary TEXT,
              description TEXT,
              tags TEXT,
              ticket_price TEXT,
              opening_hours TEXT,
              best_season TEXT,
              cover_image_url TEXT,
              gallery TEXT,
              weather TEXT,
              map_point TEXT,
              nearby_pois TEXT,
              recommended_routes TEXT,
              created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.execute(
            """
            INSERT INTO scenic_spots (
              slug,name,province,city,district,level,rating,address,latitude,longitude,summary,description,tags,
              ticket_price,opening_hours,best_season,cover_image_url,gallery,weather,map_point,nearby_pois,recommended_routes
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                "west-lake",
                "杭州西湖",
                "浙江省",
                "杭州市",
                "西湖区",
                "5A",
                4.9,
                "杭州市西湖区",
                30.24,
                120.14,
                "杭州代表性景区",
                "",
                '["湖泊"]',
                "免费",
                "全天",
                "四季",
                "",
                "[]",
                "{}",
                "{}",
                "[]",
                "[]",
            ),
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tpt_data_jingdian.sql"
            path.write_text(SAMPLE_SQL, encoding="utf-8")
            import_tpt_jingdian_sql(conn, path)
        return conn

    def test_list_scenic_includes_national_sql_results(self):
        conn = self.make_db()
        with patch.object(scenic_service, "get_db") as mocked_get_db:
            mocked_get_db.return_value.__enter__.return_value = conn
            mocked_get_db.return_value.__exit__.return_value = None

            rows = scenic_service.list_scenic(q="动物园")

        self.assertEqual(rows[0]["source"], "jingdian")
        self.assertEqual(rows[0]["name"], "北京动物园(北2门)")
        self.assertEqual(rows[0]["province"], "北京市")
        self.assertEqual(rows[0]["city"], "北京市")
        self.assertEqual(rows[0]["district"], "海淀区")
        self.assertEqual(rows[0]["map_url"].startswith("https://uri.amap.com/marker"), True)

    def test_list_scenic_can_append_amap_web_service_results(self):
        conn = self.make_db()
        amap_item = {
            "id": "amap-B001",
            "source": "amap",
            "name": "高德补充景点",
            "province": "北京市",
            "city": "北京市",
            "district": "东城区",
            "level": "高德POI",
            "rating": 4.5,
            "address": "东城区",
            "latitude": 39.9,
            "longitude": 116.4,
            "summary": "高德 Web 服务补充结果",
            "tags": ["风景名胜"],
            "ticket_price": "以景区公示为准",
            "opening_hours": "以景区公示为准",
            "map_url": "https://uri.amap.com/marker?position=116.4,39.9&name=高德补充景点",
        }
        with patch.object(scenic_service, "get_db") as mocked_get_db:
            mocked_get_db.return_value.__enter__.return_value = conn
            mocked_get_db.return_value.__exit__.return_value = None
            with patch.object(scenic_service, "search_amap_pois", return_value={"items": [amap_item], "status": "1"}):
                rows = scenic_service.list_scenic(q="补充", include_amap=True)

        self.assertEqual(rows[-1]["source"], "amap")
        self.assertEqual(rows[-1]["name"], "高德补充景点")

    def test_list_scenic_filters_national_results_by_region_names(self):
        conn = self.make_db()
        with patch.object(scenic_service, "get_db") as mocked_get_db:
            mocked_get_db.return_value.__enter__.return_value = conn
            mocked_get_db.return_value.__exit__.return_value = None

            rows = scenic_service.list_scenic(province="四川省", city="阿坝藏族羌族自治州", district="九寨沟县")

        self.assertEqual([row["name"] for row in rows], ["九寨沟瀑布群"])
        self.assertEqual(rows[0]["areaid"], "513225")

    def test_list_scenic_theme_uses_travel_theme_synonyms_for_national_results(self):
        conn = self.make_db()
        with patch.object(scenic_service, "get_db") as mocked_get_db:
            mocked_get_db.return_value.__enter__.return_value = conn
            mocked_get_db.return_value.__exit__.return_value = None

            rows = scenic_service.list_scenic(province="四川省", city="阿坝州", theme="自然风光")

        self.assertEqual([row["name"] for row in rows], ["九寨沟瀑布群"])

    def test_theme_summaries_count_database_results(self):
        conn = self.make_db()
        with patch.object(scenic_service, "get_db") as mocked_get_db:
            mocked_get_db.return_value.__enter__.return_value = conn
            mocked_get_db.return_value.__exit__.return_value = None

            summaries = scenic_service.list_theme_summaries()

        nature = next(item for item in summaries if item["name"] == "自然风光")
        family = next(item for item in summaries if item["name"] == "亲子乐园")
        self.assertGreaterEqual(nature["count"], 2)
        self.assertEqual(family["count"], 1)

    def test_theme_summaries_use_database_theme_catalog_metadata(self):
        conn = self.make_db()
        conn.executescript(
            """
            CREATE TABLE scenic_themes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              slug TEXT UNIQUE NOT NULL,
              name TEXT UNIQUE NOT NULL,
              description TEXT DEFAULT '',
              guide TEXT DEFAULT '',
              image_url TEXT DEFAULT '',
              icon TEXT DEFAULT '',
              keywords_json TEXT DEFAULT '[]',
              season TEXT DEFAULT '',
              audience TEXT DEFAULT '',
              route_idea TEXT DEFAULT '',
              sort_order INTEGER DEFAULT 100,
              is_active INTEGER DEFAULT 1
            );
            INSERT INTO scenic_themes (slug,name,description,guide,image_url,icon,keywords_json,season,audience,route_idea,sort_order,is_active)
            VALUES ('nature','自然风光','数据库中的自然主题描述','雨后初晴和清晨光线更适合观景。','https://example.com/nature.jpg','TreePine','["森林","峡谷"]','春秋','自然爱好者','山水观景一日线',1,1);
            """
        )
        with patch.object(scenic_service, "get_db") as mocked_get_db:
            mocked_get_db.return_value.__enter__.return_value = conn
            mocked_get_db.return_value.__exit__.return_value = None

            summaries = scenic_service.list_theme_summaries()

        nature = next(item for item in summaries if item["name"] == "自然风光")
        self.assertEqual(nature["description"], "数据库中的自然主题描述")
        self.assertEqual(nature["keywords"], ["森林", "峡谷"])
        self.assertEqual(nature["season"], "春秋")
        self.assertEqual(nature["audience"], "自然爱好者")

    def test_region_options_are_derived_from_national_areaids(self):
        conn = self.make_db()
        with patch.object(scenic_service, "get_db") as mocked_get_db:
            mocked_get_db.return_value.__enter__.return_value = conn
            mocked_get_db.return_value.__exit__.return_value = None

            provinces = scenic_service.get_scenic_region_options()
            cities = scenic_service.get_scenic_region_options(province="四川省")
            districts = scenic_service.get_scenic_region_options(province="四川省", city="阿坝州")

        self.assertIn("四川省", provinces["provinces"])
        self.assertIn("阿坝州", cities["cities"])
        self.assertIn("九寨沟县", districts["districts"])

    def test_region_options_label_direct_municipality_codes(self):
        conn = self.make_db()
        with patch.object(scenic_service, "get_db") as mocked_get_db:
            mocked_get_db.return_value.__enter__.return_value = conn
            mocked_get_db.return_value.__exit__.return_value = None

            cities = scenic_service.get_scenic_region_options(province="北京市")
            districts = scenic_service.get_scenic_region_options(province="北京市", city="北京市")

        self.assertIn("北京市", cities["cities"])
        self.assertIn("西城区", districts["districts"])
        self.assertIn("海淀区", districts["districts"])

    def test_legacy_region_label_helper_uses_shared_area_mapping(self):
        self.assertEqual(scenic_service._label_area("51", 2), "四川省")
        self.assertEqual(scenic_service._label_area("5132", 4), "阿坝州")
        self.assertEqual(scenic_service._label_area("1306", 4), "保定市")
        self.assertEqual(scenic_service._label_area("130621", 6), "满城县")


if __name__ == "__main__":
    unittest.main()
