import json
import sqlite3
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from app.core.database import SCHEMA, migrate_db
from app.services import scenic_crawler_enrichment_service as crawler


class ScenicCrawlerEnrichmentTest(unittest.TestCase):
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
            ) VALUES (
              1, 'test-mountain', '测试山景区', '浙江省', '杭州市', '西湖区',
              '4A', 4.6, '浙江省杭州市西湖区', 30.24, 120.14, '', '',
              '["山岳"]', '', '[]', '[]', '[]', '[]'
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
            with patch.object(crawler, "get_db", fake_db):
                return callback(conn)
        finally:
            conn.close()

    def test_batch_writes_profile_image_food_and_hiking_candidates(self):
        def fake_public_bundle(scenic, include_osm=True):
            return (
                [
                    {
                        "scenic_id": scenic["id"],
                        "candidate_type": "summary",
                        "title": "测试山景区介绍",
                        "content": "测试山景区是适合轻徒步和城市近郊观景的山岳型景区。",
                        "source_url": "https://zh.wikipedia.org/wiki/test",
                        "source_name": "维基百科",
                        "source_type": "wikipedia",
                        "confidence": 82,
                        "risk_level": "medium",
                    }
                ],
                [
                    {
                        "scenic_id": scenic["id"],
                        "image_url": "https://img.example.test/mountain.jpg",
                        "thumbnail_url": "https://img.example.test/mountain-thumb.jpg",
                        "source_url": "https://commons.wikimedia.org/wiki/File:test.jpg",
                        "source_name": "Wikimedia Commons",
                        "source_type": "wikimedia_commons",
                        "license": "CC BY-SA",
                        "attribution": "Tester",
                        "provider": "wikimedia_commons",
                        "risk_level": "low",
                        "confidence": 88,
                        "title": "测试山景区",
                    }
                ],
                [],
            )

        def fake_pois(scenic, include_food=True, include_hiking=True, include_paid_providers=False):
            return [
                {
                    "type": "nearby_food",
                    "name": "测试山脚面馆",
                    "address": "景区入口旁",
                    "distance_text": "约 0.8 km",
                    "source_url": "https://map.example.test/food",
                    "source_name": "高德 POI",
                    "risk_level": "low",
                    "confidence": 76,
                },
                {
                    "type": "hiking_poi",
                    "name": "测试山观景步道",
                    "address": "景区北侧",
                    "distance_text": "约 1.2 km",
                    "source_url": "https://www.openstreetmap.org/way/1",
                    "source_name": "OpenStreetMap",
                    "risk_level": "low",
                    "confidence": 81,
                },
            ]

        def assertions(conn):
            with patch.object(crawler, "public_source_bundle_detailed", fake_public_bundle), patch.object(crawler, "_collect_poi_candidates", fake_pois):
                result = crawler.run_crawler_batch(limit=1, include_pois=True)

            self.assertEqual(result["read"], 1)
            self.assertEqual(result["profileCandidates"], 3)
            self.assertEqual(result["imageCandidates"], 1)
            self.assertEqual(result["lowRiskCandidates"], 3)

            profile_types = [
                row["candidate_type"]
                for row in conn.execute("SELECT candidate_type FROM scenic_profile_candidates ORDER BY id").fetchall()
            ]
            self.assertEqual(profile_types, ["summary", "nearby_food", "hiking_poi"])

            image = conn.execute("SELECT image_url, risk_level FROM scenic_image_candidates").fetchone()
            self.assertEqual(image["image_url"], "https://img.example.test/mountain.jpg")
            self.assertEqual(image["risk_level"], "low")

        self.run_with_db(assertions)

    def test_approve_low_risk_merges_image_food_and_hiking_without_duplicates(self):
        def assertions(conn):
            conn.execute(
                """
                INSERT INTO scenic_image_candidates (
                  id, scenic_id, image_url, thumbnail_url, source_url, source_name,
                  source_type, license, attribution, provider, risk_level, status,
                  review_status, confidence
                ) VALUES (
                  10, 1, 'https://img.example.test/mountain.jpg', '', 'https://commons.test/file',
                  'Commons', 'wikimedia_commons', 'CC BY', 'Tester', 'commons',
                  'low', 'pending', 'pending', 88
                )
                """
            )
            food = [{"name": "测试山脚面馆", "address": "景区入口旁", "source": "高德 POI"}]
            hiking = [{"name": "测试山观景步道", "address": "景区北侧", "source": "OpenStreetMap"}]
            for idx, (kind, payload) in enumerate((("nearby_food", food), ("hiking_poi", hiking)), start=20):
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
                        kind,
                        json.dumps(payload, ensure_ascii=False),
                        "https://source.test",
                        "source",
                        "crawler_poi",
                        80,
                        "low",
                        "pending",
                    ),
                )

            result = crawler.approve_low_risk_candidates(limit=10)
            self.assertEqual(result["approvedImages"], 1)
            self.assertEqual(result["approvedPois"], 2)

            scenic = conn.execute("SELECT cover_image_url, nearby_food, nearby_pois, recommended_routes FROM scenic_spots WHERE id=1").fetchone()
            self.assertEqual(scenic["cover_image_url"], "https://img.example.test/mountain.jpg")
            self.assertEqual(json.loads(scenic["nearby_food"])[0]["name"], "测试山脚面馆")
            self.assertEqual(json.loads(scenic["nearby_pois"])[0]["name"], "测试山观景步道")
            self.assertIn("测试山观景步道", json.loads(scenic["recommended_routes"])[0])

            self.assertEqual(conn.execute("SELECT status FROM scenic_image_candidates WHERE id=10").fetchone()["status"], "approved")
            self.assertEqual(conn.execute("SELECT status FROM scenic_profile_candidates WHERE id=20").fetchone()["status"], "merged")

        self.run_with_db(assertions)

    def test_direct_merge_public_profile_candidates_updates_summary_and_description(self):
        def assertions(conn):
            conn.execute(
                """
                UPDATE scenic_spots
                SET summary='本地规则摘要', description='本地规则介绍', source_url='local-sql:tpt_data_jingdian:1'
                WHERE id=1
                """
            )
            conn.execute(
                """
                INSERT INTO scenic_profile_candidates (
                  id, scenic_id, candidate_type, title, content, source_url,
                  source_name, source_type, confidence, risk_level, status
                ) VALUES (
                  30, 1, 'summary', '测试山景区公开介绍',
                  '测试山景区位于浙江省杭州市，是以山岳景观、轻徒步路线和城市近郊观景体验为特色的旅游景区。',
                  'https://zh.wikipedia.org/wiki/test-mountain',
                  '维基百科', 'wikipedia', 84, 'medium', 'pending'
                )
                """
            )

            result = crawler.merge_profile_candidates_direct(limit=10)
            self.assertEqual(result["mergedProfiles"], 1)

            scenic = conn.execute("SELECT summary, description, source_url FROM scenic_spots WHERE id=1").fetchone()
            self.assertIn("测试山景区位于浙江省杭州市", scenic["summary"])
            self.assertEqual(scenic["description"], "测试山景区位于浙江省杭州市，是以山岳景观、轻徒步路线和城市近郊观景体验为特色的旅游景区。")
            self.assertEqual(scenic["source_url"], "https://zh.wikipedia.org/wiki/test-mountain")
            candidate = conn.execute("SELECT status, reviewed_by FROM scenic_profile_candidates WHERE id=30").fetchone()
            self.assertEqual(candidate["status"], "merged")
            self.assertEqual(candidate["reviewed_by"], "auto_crawler")

        self.run_with_db(assertions)

    def test_batch_can_directly_merge_public_profile_candidates(self):
        def fake_public_bundle(scenic, include_osm=True):
            return (
                [
                    {
                        "scenic_id": scenic["id"],
                        "candidate_type": "summary",
                        "title": "测试山景区公开介绍",
                        "content": "测试山景区是一个适合直接补全资料的公开来源景区介绍。",
                        "source_url": "https://zh.wikipedia.org/wiki/test-mountain",
                        "source_name": "维基百科",
                        "source_type": "wikipedia",
                        "confidence": 82,
                        "risk_level": "medium",
                    }
                ],
                [],
                [],
            )

        def assertions(conn):
            with patch.object(crawler, "public_source_bundle_detailed", fake_public_bundle):
                result = crawler.run_crawler_batch(limit=1, include_pois=False, direct_merge_profiles=True)
            self.assertEqual(result["profileCandidates"], 1)
            self.assertEqual(result["directMergedProfiles"], 1)

            scenic = conn.execute("SELECT summary, description, source_url FROM scenic_spots WHERE id=1").fetchone()
            self.assertEqual(scenic["description"], "测试山景区是一个适合直接补全资料的公开来源景区介绍。")
            self.assertEqual(scenic["source_url"], "https://zh.wikipedia.org/wiki/test-mountain")
            self.assertEqual(conn.execute("SELECT status FROM scenic_profile_candidates").fetchone()["status"], "merged")

        self.run_with_db(assertions)

    def test_backfill_public_source_links_replaces_local_sql_source(self):
        def assertions(conn):
            conn.execute("UPDATE scenic_spots SET source_url='local-sql:tpt_data_jingdian:1' WHERE id=1")

            result = crawler.backfill_public_source_links(limit=10)
            self.assertEqual(result["updated"], 1)

            scenic = conn.execute("SELECT source_url FROM scenic_spots WHERE id=1").fetchone()
            self.assertTrue(scenic["source_url"].startswith("https://uri.amap.com/marker?position=120.14,30.24"))

        self.run_with_db(assertions)

    def test_batch_includes_spots_with_cover_but_under_target_gallery(self):
        def fake_public_bundle(scenic, include_osm=True):
            return (
                [],
                [
                    {
                        "scenic_id": scenic["id"],
                        "image_url": "https://img.example.test/mountain-2.jpg",
                        "source_url": "https://commons.wikimedia.org/wiki/File:test-2.jpg",
                        "source_type": "wikimedia_commons",
                        "license": "CC BY-SA",
                        "risk_level": "low",
                        "confidence": 86,
                    }
                ],
                [],
            )

        def assertions(conn):
            conn.execute(
                """
                UPDATE scenic_spots
                SET summary='完整摘要', description='完整介绍', cover_image_url='https://img.example.test/mountain-1.jpg',
                    gallery='["https://img.example.test/mountain-1.jpg"]',
                    nearby_food='[{"name":"面馆"}]', nearby_pois='[{"name":"观景点"}]', recommended_routes='["入口 -> 观景点"]'
                WHERE id=1
                """
            )
            conn.execute(
                """
                INSERT INTO scenic_images (scenic_id,url,status,is_cover,quality_score,source)
                VALUES (1,'https://img.example.test/mountain-1.jpg','approved',1,80,'test')
                """
            )
            with patch.object(crawler, "public_source_bundle_detailed", fake_public_bundle):
                result = crawler.run_crawler_batch(limit=1, include_pois=False, target_image_count=4)
            self.assertEqual(result["read"], 1)
            self.assertEqual(result["imageCandidates"], 1)

            with patch.object(crawler, "public_source_bundle_detailed", fake_public_bundle):
                done = crawler.run_crawler_batch(limit=1, include_pois=False, target_image_count=1)
            self.assertEqual(done["read"], 0)

        self.run_with_db(assertions)

    def test_status_reports_missing_images_and_low_risk_candidates(self):
        def assertions(conn):
            conn.execute(
                "INSERT INTO scenic_image_candidates (scenic_id, image_url, risk_level, status, review_status) VALUES (1, 'https://img.test/a.jpg', 'low', 'pending', 'pending')"
            )
            conn.execute(
                """
                INSERT INTO scenic_profile_candidates (
                  scenic_id, candidate_type, title, content, source_url, source_type,
                  risk_level, status
                ) VALUES (
                  1, 'nearby_food', '[{"name":"店"}]', '[{"name":"店"}]', 'https://source.test',
                  'crawler_poi', 'low', 'pending'
                )
                """
            )

            status = crawler.crawler_status()
            self.assertEqual(status["stats"]["missingImages"], 1)
            self.assertEqual(status["stats"]["underTargetImages"], 1)
            self.assertEqual(status["stats"]["pendingProfileCandidates"], 1)
            self.assertEqual(status["stats"]["pendingImageCandidates"], 1)
            self.assertEqual(status["stats"]["lowRiskCandidates"], 2)

        self.run_with_db(assertions)


if __name__ == "__main__":
    unittest.main()
