import json
import sqlite3
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from app.core.database import SCHEMA, migrate_db
from app.services import scenic_profile_batch_enrichment_service as batch_service


class ScenicProfileBatchEnrichmentTest(unittest.TestCase):
    def make_db(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA)
        migrate_db(conn)
        rows = [
            (
                1,
                "sql-test-park",
                "测试城市公园",
                "河北省",
                "保定市",
                "莲池区",
                "公园",
                "公园广场;公园",
                "公园广场;公园 · 来自本地 SQL 数据源",
                "测试城市公园 是本地全国旅游景点 SQL 数据源中的目的地，适合纳入景区检索、路线规划和资料补全流程。",
            ),
            (
                2,
                "sql-test-temple",
                "测试古寺",
                "浙江省",
                "杭州市",
                "西湖区",
                "寺庙道观",
                "风景名胜;寺庙道观",
                "寺庙道观 · 来自本地 SQL 数据源",
                "",
            ),
        ]
        conn.executemany(
            """
            INSERT INTO scenic_spots (
              id, slug, name, province, city, district, level, rating, address,
              latitude, longitude, summary, description, tags, ticket_price,
              opening_hours, best_season, cover_image_url, gallery
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 4.3, ?, 38.8, 115.4, ?, ?, ?, '以景区公示为准',
              '以景区公示为准', '四季皆宜', '', '[]')
            """,
            [(rid, slug, name, province, city, district, level, f"{province}{city}{district}", summary, description, json.dumps(tags.split(";"), ensure_ascii=False)) for rid, slug, name, province, city, district, level, tags, summary, description in rows],
        )
        return conn

    def test_build_profile_patch_generates_structured_fields(self):
        scenic = {
            "id": 1,
            "name": "测试古寺",
            "province": "浙江省",
            "city": "杭州市",
            "district": "西湖区",
            "level": "寺庙道观",
            "summary": "寺庙道观 · 来自本地 SQL 数据源",
            "description": "",
            "tags": '["风景名胜", "寺庙道观"]',
        }
        patch = batch_service.build_profile_patch(scenic)
        self.assertIn("summary", patch)
        self.assertIn("description", patch)
        self.assertIn("history_culture", patch)
        self.assertIn("recommended_itinerary", patch)
        self.assertIn("文化", patch["history_culture"])
        self.assertIsInstance(json.loads(patch["travel_tips"]), list)

    def test_batch_updates_generic_rows_and_reports_stats(self):
        conn = self.make_db()

        @contextmanager
        def fake_db():
            yield conn
            conn.commit()

        with patch.object(batch_service, "get_db", fake_db):
            result = batch_service.enrich_profile_batch(limit=10, offset=0)
            self.assertEqual(result["read"], 2)
            self.assertEqual(result["updated"], 2)
            self.assertIn("recommended_duration", result["fields"])

            stats = batch_service.profile_completion_stats()
            self.assertEqual(stats["missing_slogan"], 0)
            self.assertEqual(stats["missing_tips"], 0)

            row = conn.execute("SELECT summary, description, suitable_groups, completeness_score FROM scenic_spots WHERE id=1").fetchone()
            self.assertNotIn("本地 SQL 数据源", row["summary"])
            self.assertTrue(json.loads(row["suitable_groups"]))
            self.assertGreater(row["completeness_score"], 70)


if __name__ == "__main__":
    unittest.main()
