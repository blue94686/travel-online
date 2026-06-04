import json
import sqlite3
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from app.core.database import SCHEMA, migrate_db
from app.services import admin_web_enrichment_service as web_service


class AdminWebEnrichmentServiceTest(unittest.TestCase):
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
              gallery, nearby_food, nearby_pois, recommended_routes
            ) VALUES
            (1, 'west-lake', '测试西湖', '浙江省', '杭州市', '西湖区', '5A', 4.8, '杭州',
             30.24, 120.14, '', '', '["湖泊"]', '', '[]', '[]', '[]', '[]'),
            (2, 'mountain', '测试山', '四川省', '阿坝藏族羌族自治州', '九寨沟县', '4A', 4.5, '阿坝',
             32.9, 103.9, '山岳景区', '山岳景区介绍', '["山岳"]', 'https://img.test/mountain.jpg',
             '[]', '[{"name":"山脚餐厅"}]', '[{"name":"观景步道"}]', '[]')
            """
        )
        conn.execute(
            """
            INSERT INTO scenic_image_candidates (
              id, scenic_id, image_url, thumbnail_url, source_url, source_name,
              source_type, license, attribution, provider, risk_level, status,
              review_status, title, confidence, quality_score
            ) VALUES (
              10, 1, 'https://img.test/west-lake.jpg', 'https://img.test/west-lake-thumb.jpg',
              'https://commons.test/file', 'Wikimedia Commons', 'wikimedia_commons',
              'CC BY', 'Tester', 'commons', 'low', 'pending', 'pending', '测试西湖图片', 88, 88
            )
            """
        )
        food_payload = [{"name": "湖边茶馆", "address": "景区入口", "source": "高德 POI"}]
        hiking_payload = [{"name": "环湖步道", "address": "景区内", "source": "OpenStreetMap"}]
        for idx, kind, payload, risk in (
            (20, "nearby_food", food_payload, "low"),
            (21, "hiking_poi", hiking_payload, "medium"),
            (22, "summary", "测试西湖介绍候选", "medium"),
        ):
            conn.execute(
                """
                INSERT INTO scenic_profile_candidates (
                  id, scenic_id, candidate_type, title, content, source_url,
                  source_name, source_type, confidence, risk_level, status
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    idx,
                    1,
                    kind,
                    f"{kind} 候选",
                    json.dumps(payload, ensure_ascii=False) if isinstance(payload, list) else payload,
                    "https://source.test",
                    "source",
                    "crawler_poi" if kind != "summary" else "wikipedia",
                    80,
                    risk,
                    "pending",
                ),
            )
        conn.execute(
            "INSERT INTO sync_tasks (name, source, status, message) VALUES ('scenic_crawler_enrichment', 'crawler', 'running', ?)",
            (json.dumps({"read": 2, "searched": 2, "imageCandidates": 1, "profileCandidates": 3}, ensure_ascii=False),),
        )
        conn.execute(
            "INSERT INTO sync_tasks (name, source, status, message) VALUES ('tpt_media_job', 'tpt', 'idle', '{}')"
        )
        return conn

    def run_with_db(self, callback):
        conn = self.make_db()

        @contextmanager
        def fake_db():
            yield conn
            conn.commit()

        try:
            with patch.object(web_service, "get_db", fake_db):
                return callback(conn)
        finally:
            conn.close()

    def test_overview_aggregates_missing_counts_candidates_and_jobs(self):
        def assertions(conn):
            overview = web_service.web_enrichment_overview()

            self.assertEqual(overview["totalScenic"], 2)
            self.assertEqual(overview["missingImages"], 1)
            self.assertEqual(overview["missingProfiles"], 1)
            self.assertEqual(overview["missingFood"], 1)
            self.assertEqual(overview["missingPois"], 1)
            self.assertEqual(overview["pendingImageCandidates"], 1)
            self.assertEqual(overview["pendingProfileCandidates"], 3)
            self.assertEqual(overview["pendingFoodCandidates"], 1)
            self.assertEqual(overview["pendingHikingCandidates"], 1)
            self.assertEqual(overview["lowRiskCandidates"], 2)
            self.assertEqual(overview["crawlerJob"]["status"], "running")
            self.assertEqual(len(overview["recentTasks"]), 2)

        self.run_with_db(assertions)

    def test_candidate_queue_normalizes_food_and_image_candidates(self):
        def assertions(conn):
            food = web_service.web_enrichment_candidates(candidate_type="food", limit=10)
            self.assertEqual(len(food["items"]), 1)
            self.assertEqual(food["items"][0]["candidate_kind"], "profile")
            self.assertEqual(food["items"][0]["candidate_type"], "nearby_food")
            self.assertEqual(food["items"][0]["scenic_name"], "测试西湖")
            self.assertIn("湖边茶馆", food["items"][0]["preview"])

            images = web_service.web_enrichment_candidates(candidate_type="image", risk="low", limit=10)
            self.assertEqual(len(images["items"]), 1)
            self.assertEqual(images["items"][0]["candidate_kind"], "image")
            self.assertEqual(images["items"][0]["source_name"], "Wikimedia Commons")
            self.assertEqual(images["items"][0]["risk_level"], "low")

        self.run_with_db(assertions)


if __name__ == "__main__":
    unittest.main()
