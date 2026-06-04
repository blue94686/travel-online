import sqlite3
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from app.core.database import SCHEMA, migrate_db
from app.services import scenic_enrichment_service


class ScenicMediaPipelineTest(unittest.TestCase):
    def make_db(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA)
        migrate_db(conn)
        conn.execute(
            """
            INSERT INTO scenic_spots (
              id, slug, name, province, city, district, level, rating, address,
              latitude, longitude, summary, description, tags, cover_image_url, gallery
            ) VALUES (1, 'test-huangshan', '测试黄山', '安徽省', '黄山市', '黄山区',
              '5A', 4.9, '安徽省黄山市黄山区', 30.13, 118.17, '摘要', '介绍',
              '["自然风光"]', '', '[]')
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
            with patch.object(scenic_enrichment_service, "get_db", fake_db):
                return callback(conn)
        finally:
            conn.close()

    def test_migration_adds_lightweight_media_index_columns(self):
        conn = self.make_db()
        try:
            image_columns = {row["name"] for row in conn.execute("PRAGMA table_info(scenic_images)").fetchall()}
            candidate_columns = {row["name"] for row in conn.execute("PRAGMA table_info(scenic_image_candidates)").fetchall()}

            for column in ("thumbnail_url", "source_url", "license", "attribution", "provider", "quality_score", "last_checked_at"):
                self.assertIn(column, image_columns)
            for column in ("license", "attribution", "provider", "quality_score", "last_checked_at", "availability_status", "failure_count"):
                self.assertIn(column, candidate_columns)
        finally:
            conn.close()

    def test_public_profile_uses_only_approved_remote_images_with_metadata(self):
        def assertions(conn):
            conn.execute("UPDATE scenic_spots SET source_url='https://zh.wikipedia.org/wiki/test' WHERE id=1")
            conn.execute(
                """
                INSERT INTO scenic_images (
                  scenic_id,url,thumbnail_url,status,is_cover,source,source_url,license,attribution,provider,quality_score
                ) VALUES
                  (1,'https://cdn.example.test/approved.jpg','https://cdn.example.test/thumb.jpg','approved',1,
                   'Wikimedia Commons','https://commons.example.test/file','CC BY-SA','Author Name','wikimedia_commons',92),
                  (1,'https://cdn.example.test/pending.jpg','https://cdn.example.test/pending-thumb.jpg','pending',0,
                   'Bing Image Search','https://bing.example.test','unknown','','bing_image',55)
                """
            )

            profile = scenic_enrichment_service.public_profile(1)

            self.assertEqual(profile["cover_image_url"], "https://cdn.example.test/approved.jpg")
            self.assertEqual(profile["gallery"], ["https://cdn.example.test/approved.jpg"])
            self.assertEqual(len(profile["media_assets"]), 1)
            self.assertEqual(profile["media_assets"][0]["license"], "CC BY-SA")
            self.assertEqual(profile["media_assets"][0]["attribution"], "Author Name")
            self.assertEqual(profile["image_policy"]["storage"], "external_url_only")

        self.run_with_db(assertions)

    def test_approving_image_candidate_writes_approved_lightweight_image_record(self):
        def assertions(conn):
            conn.execute(
                """
                INSERT INTO scenic_image_candidates (
                  id,scenic_id,image_url,thumbnail_url,source_url,source_name,source_type,risk_level,
                  status,title,confidence,review_status,raw_payload_json,license,attribution,provider,quality_score
                ) VALUES (
                  8,1,'https://img.example.test/h.jpg','https://img.example.test/h-thumb.jpg',
                  'https://commons.example.test/h','Wikimedia Commons','wikimedia_commons','low',
                  'pending','测试黄山实景',0.88,'pending','{}','CC BY-SA','Author Name','wikimedia_commons',88
                )
                """
            )

            result = scenic_enrichment_service.approve_image_candidate(8)
            image = conn.execute("SELECT * FROM scenic_images WHERE scenic_id=1 AND url='https://img.example.test/h.jpg'").fetchone()
            candidate = conn.execute("SELECT status, review_status FROM scenic_image_candidates WHERE id=8").fetchone()

            self.assertEqual(result["status"], "approved")
            self.assertEqual(image["status"], "approved")
            self.assertEqual(image["thumbnail_url"], "https://img.example.test/h-thumb.jpg")
            self.assertEqual(image["source_url"], "https://commons.example.test/h")
            self.assertEqual(image["license"], "CC BY-SA")
            self.assertEqual(candidate["status"], "approved")
            self.assertEqual(candidate["review_status"], "approved")

        self.run_with_db(assertions)

    def test_profile_search_image_candidates_keep_real_source_url(self):
        def assertions(conn):
            scenic_enrichment_service._insert_image_candidate(conn, {
                "scenic_id": 1,
                "title": "测试黄山图片搜索",
                "content": "https://www.bing.com/images/search?q=test",
                "source_url": "https://www.bing.com/images/search?q=test",
                "source_name": "Bing Image Search",
                "source_type": "bing",
                "risk_level": "high",
                "confidence": 46,
                "raw_payload_json": "{}",
            })

            row = conn.execute("SELECT image_url, thumbnail_url, source_url FROM scenic_image_candidates WHERE scenic_id=1").fetchone()
            self.assertEqual(row["image_url"], "https://www.bing.com/images/search?q=test")
            self.assertEqual(row["thumbnail_url"], "https://www.bing.com/images/search?q=test")
            self.assertNotEqual(row["image_url"], "/images/hero-mountain-lake.jpg")

        self.run_with_db(assertions)

    def test_public_profile_refreshes_demo_data_from_public_sources(self):
        def assertions(conn):
            conn.execute(
                """
                UPDATE scenic_spots
                SET cover_image_url='https://images.unsplash.com/photo-demo?w=1400', source_url='', summary='演示摘要',
                    latitude=34.9, longitude=114.9
                WHERE id=1
                """
            )

            with patch.object(scenic_enrichment_service, "public_source_candidates") as public_sources:
                public_sources.return_value = (
                    {
                        "scenic_id": 1,
                        "candidate_type": "summary",
                        "title": "测试黄山公开摘要",
                        "content": "测试黄山公开摘要来自公开百科资料。",
                        "source_url": "https://zh.wikipedia.org/wiki/test-huangshan",
                        "source_name": "维基百科",
                        "source_type": "wikipedia",
                        "confidence": 62,
                        "risk_level": "medium",
                        "raw_payload_json": '{"coordinates":[{"lat":30.1329,"lon":118.1638}]}',
                    },
                    [
                        {
                            "scenic_id": 1,
                            "image_url": "https://upload.wikimedia.org/test-huangshan.jpg",
                            "thumbnail_url": "https://upload.wikimedia.org/test-huangshan-thumb.jpg",
                            "source_url": "https://commons.wikimedia.org/wiki/File:Test.jpg",
                            "source_name": "Wikimedia Commons",
                            "source_type": "wikimedia_commons",
                            "license": "CC BY-SA",
                            "attribution": "Author Name",
                            "provider": "wikimedia_commons",
                            "risk_level": "medium",
                            "status": "pending",
                            "title": "测试黄山实景",
                            "confidence": 0.7,
                            "quality_score": 70,
                            "availability_status": "unchecked",
                            "failure_count": 0,
                            "review_status": "pending",
                            "raw_payload_json": "{}",
                        }
                    ],
                )

                profile = scenic_enrichment_service.public_profile(1)

            self.assertEqual(profile["summary"], "测试黄山公开摘要来自公开百科资料。")
            self.assertEqual(profile["source_url"], "https://zh.wikipedia.org/wiki/test-huangshan")
            self.assertEqual(profile["cover_image_url"], "https://upload.wikimedia.org/test-huangshan.jpg")
            self.assertEqual(profile["media_assets"][0]["source"], "Wikimedia Commons")
            self.assertEqual(profile["media_assets"][0]["license"], "CC BY-SA")
            self.assertEqual(profile["latitude"], 30.1329)
            self.assertEqual(profile["longitude"], 118.1638)

        self.run_with_db(assertions)

    def test_public_profile_filters_demo_images_when_public_media_exists(self):
        def assertions(conn):
            conn.execute(
                """
                INSERT INTO scenic_images (
                  scenic_id,url,thumbnail_url,status,is_cover,source,source_url,provider,quality_score
                ) VALUES
                  (1,'https://images.unsplash.com/photo-demo?w=1400','https://images.unsplash.com/photo-demo?w=300','approved',0,'seed','','',0),
                  (1,'https://upload.wikimedia.org/real.jpg','https://upload.wikimedia.org/real-thumb.jpg','approved',1,
                   'Wikimedia Commons','https://commons.wikimedia.org/wiki/File:Real.jpg','wikimedia_commons',88)
                """
            )

            profile = scenic_enrichment_service.public_profile(1)

            self.assertEqual([item["url"] for item in profile["media_assets"]], ["https://upload.wikimedia.org/real.jpg"])
            self.assertEqual(profile["gallery"], ["https://upload.wikimedia.org/real.jpg"])

        self.run_with_db(assertions)


if __name__ == "__main__":
    unittest.main()
