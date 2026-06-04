import sqlite3
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from app.core.database import SCHEMA, migrate_db
from app.services import scenic_external_enrichment_service as external_service


class ScenicExternalEnrichmentTest(unittest.TestCase):
    def make_db(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA)
        migrate_db(conn)
        conn.execute(
            """
            INSERT INTO scenic_spots (
              id, slug, name, province, city, district, level, rating, address,
              latitude, longitude, summary, description, tags, ticket_price,
              opening_hours, best_season, cover_image_url, gallery
            ) VALUES (1, 'test-west-lake', '测试西湖', '浙江省', '杭州市', '西湖区',
              '5A', 4.8, '浙江省杭州市西湖区', 30.24, 120.14, '', '', '["湖泊"]',
              '', '', '', '', '[]')
            """
        )
        conn.execute(
            """
            INSERT INTO api_configs (provider, label, enabled, api_key_secret)
            VALUES ('bing_search', 'Bing Search API', 1, 'web-key'),
                   ('bing_image', 'Bing Image Search API', 1, 'image-key'),
                   ('amap_web_service', '高德 Web 服务', 1, 'amap-key')
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
            with patch.object(external_service, "get_db", fake_db):
                return callback(conn)
        finally:
            conn.close()

    def test_external_batch_inserts_web_and_image_candidates_from_search_results(self):
        def fake_get_json(url, headers=None, timeout=8):
            if "/images/search" in url:
                return {
                    "value": [
                        {
                            "name": "测试西湖 全景",
                            "contentUrl": "https://example-cdn.test/westlake.jpg",
                            "thumbnailUrl": "https://example-cdn.test/westlake-thumb.jpg",
                            "hostPageUrl": "https://www.example-tourism.gov.cn/westlake",
                            "encodingFormat": "jpeg",
                        }
                    ]
                }
            return {
                "webPages": {
                    "value": [
                        {
                            "name": "测试西湖景区官方网站",
                            "url": "https://www.example-tourism.gov.cn/westlake",
                            "snippet": "测试西湖是杭州代表性湖泊景区，拥有湖光山色、历史遗迹和环湖步道。",
                        },
                        {
                            "name": "测试西湖开放时间",
                            "url": "https://www.example-tourism.gov.cn/westlake/time",
                            "snippet": "开放时间为每日 08:00-17:30，节假日以景区公告为准。",
                        },
                    ]
                }
            }

        def assertions(conn):
            with patch.object(external_service, "_http_get_json", fake_get_json):
                result = external_service.external_enrich_profile_batch(limit=1, offset=0, include_public_sources=False)

            self.assertEqual(result["requested"], 1)
            self.assertEqual(result["searched"], 1)
            self.assertGreaterEqual(result["profile_candidates"], 2)
            self.assertEqual(result["image_candidates"], 1)

            profile_rows = conn.execute(
                "SELECT candidate_type, source_url, source_type FROM scenic_profile_candidates WHERE scenic_id=1"
            ).fetchall()
            self.assertTrue(any(row["candidate_type"] == "official_site" for row in profile_rows))
            self.assertTrue(any(row["candidate_type"] == "summary" for row in profile_rows))
            self.assertTrue(all(row["source_type"] == "bing_web" for row in profile_rows))

            image_row = conn.execute("SELECT image_url, source_url, source_type FROM scenic_image_candidates WHERE scenic_id=1").fetchone()
            self.assertEqual(image_row["image_url"], "https://example-cdn.test/westlake.jpg")
            self.assertEqual(image_row["source_type"], "bing_image")

        self.run_with_db(assertions)

    def test_external_batch_skips_network_when_search_providers_are_not_configured(self):
        def assertions(conn):
            conn.execute("UPDATE api_configs SET enabled=0, api_key_secret='' WHERE provider IN ('bing_search','bing_image')")

            with patch.object(external_service, "_http_get_json") as get_json:
                result = external_service.external_enrich_profile_batch(limit=1, offset=0, include_public_sources=False)

            self.assertEqual(result["requested"], 1)
            self.assertEqual(result["searched"], 0)
            self.assertEqual(result["skipped_no_provider"], 1)
            get_json.assert_not_called()

        self.run_with_db(assertions)

    def test_wikipedia_lookup_tries_short_title_variants(self):
        calls = []

        def fake_get_json(url, headers=None, timeout=8, retries=2):
            calls.append(url)
            if "titles=%E6%B5%8B%E8%AF%95%E8%A5%BF%E6%B9%96%E9%A3%8E%E6%99%AF%E5%8C%BA" in url:
                return {"query": {"pages": {"-1": {"missing": ""}}}}
            return {
                "query": {
                    "pages": {
                        "10": {
                            "title": "测试西湖",
                            "extract": "测试西湖是杭州代表性湖泊景区，拥有湖光山色和历史遗迹。",
                            "fullurl": "https://zh.wikipedia.org/wiki/test",
                            "thumbnail": {"source": "https://img.test/thumb.jpg"},
                            "original": {"source": "https://img.test/original.jpg"},
                        }
                    }
                }
            }

        scenic = {"id": 2, "name": "测试西湖风景区", "province": "浙江省", "city": "杭州市", "district": "西湖区"}
        with patch.object(external_service, "_http_get_json", fake_get_json):
            profile_candidate, image_candidates = external_service._wikipedia_candidates(scenic)

        self.assertGreaterEqual(len(calls), 2)
        self.assertEqual(profile_candidate["content"], "测试西湖是杭州代表性湖泊景区，拥有湖光山色和历史遗迹。")
        self.assertEqual(image_candidates[0]["image_url"], "https://img.test/original.jpg")

    def test_title_variants_include_known_public_aliases(self):
        self.assertIn("漓江", external_service._title_variants("桂林漓江风景区"))
        self.assertIn("千岛湖", external_service._title_variants("千岛湖风景区"))
        self.assertIn("雷峰塔", external_service._title_variants("雷峰塔景区"))

    def test_amap_candidates_extract_profile_and_photo_candidates(self):
        def fake_get_json(url, headers=None, timeout=8, retries=2):
            return {
                "status": "1",
                "pois": [
                    {
                        "id": "B0001",
                        "name": "测试西湖",
                        "address": "浙江省杭州市西湖区测试路1号",
                        "tel": "0571-12345678",
                        "opentime": "08:00-17:30",
                        "website": "https://westlake.example.test",
                        "location": "120.14,30.24",
                        "photos": [
                            {
                                "title": "测试西湖入口",
                                "url": "https://img.example.test/westlake-amap.jpg",
                            }
                        ],
                    }
                ],
            }

        scenic = {"id": 1, "name": "测试西湖", "province": "浙江省", "city": "杭州市", "district": "西湖区"}
        with patch.object(external_service, "_http_get_json", fake_get_json):
            profile_candidates, image_candidates = external_service._amap_candidates(scenic, "amap-key")

        candidate_types = {item["candidate_type"] for item in profile_candidates}
        self.assertIn("address", candidate_types)
        self.assertIn("opening_hours", candidate_types)
        self.assertIn("official_site", candidate_types)
        self.assertEqual(image_candidates[0]["image_url"], "https://img.example.test/westlake-amap.jpg")


if __name__ == "__main__":
    unittest.main()
