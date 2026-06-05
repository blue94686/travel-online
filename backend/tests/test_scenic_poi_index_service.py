import json
import sqlite3
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from app.core.database import SCHEMA, migrate_db
from app.services import scenic_poi_index_service as poi_index


class ScenicPoiIndexServiceTest(unittest.TestCase):
    def make_db(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA)
        migrate_db(conn)
        conn.execute(
            """
            INSERT INTO scenic_spots (
              id, slug, name, province, city, district, level, rating, address,
              latitude, longitude, summary, description, tags, cover_image_url,
              gallery, nearby_food, nearby_pois, nearby_hotels, recommended_routes, travel_tips
            ) VALUES (
              1, 'test-mountain', '测试山景区', '浙江省', '杭州市', '西湖区',
              '4A', 4.6, '浙江省杭州市西湖区', 30.24, 120.14,
              '山岳徒步景区', '适合徒步、观景和亲子休闲。', '["徒步","山岳","公园"]',
              '', '[]', '[]', '[]', '[]', '[]', '[]'
            )
            """
        )
        return conn

    def run_with_db(self, callback):
        conn = self.make_db()

        @contextmanager
        def fake_db():
            yield conn
            conn.commit()

        try:
            with patch.object(poi_index, "get_db", fake_db):
                return callback(conn)
        finally:
            conn.close()

    def test_backfill_theme_poi_index_adds_all_requested_categories(self):
        def assertions(conn):
            result = poi_index.backfill_theme_poi_index(limit=1)
            self.assertEqual(result["updated"], 1)
            self.assertEqual(result["poiItems"], 18)

            scenic = conn.execute("SELECT nearby_pois, nearby_food, nearby_hotels, recommended_routes, travel_tips FROM scenic_spots WHERE id=1").fetchone()
            nearby_pois = json.loads(scenic["nearby_pois"])
            nearby_food = json.loads(scenic["nearby_food"])
            nearby_hotels = json.loads(scenic["nearby_hotels"])
            categories = {item["category"] for item in [*nearby_pois, *nearby_food, *nearby_hotels]}

            self.assertTrue({
                "bus_station", "subway_station", "parking", "restaurant", "cafe", "snack_street",
                "hotel", "homestay", "campground", "mall", "supermarket", "specialty_store",
                "nearby_scenic", "viewpoint", "park", "trailhead", "supply_point", "trail_camp",
            }.issubset(categories))
            self.assertTrue(all(item["source_url"].startswith("https://uri.amap.com/search?keyword=") for item in nearby_pois[:5]))
            self.assertGreaterEqual(len(json.loads(scenic["recommended_routes"])), 3)
            self.assertGreaterEqual(len(json.loads(scenic["travel_tips"])), 3)

        self.run_with_db(assertions)


if __name__ == "__main__":
    unittest.main()
