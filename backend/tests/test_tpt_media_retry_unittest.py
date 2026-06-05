import unittest
import sqlite3
import json
from unittest.mock import patch

from app.services import tpt_profile_enrichment_service as service
from app.services.tpt_jingdian_importer import ensure_tpt_jingdian_schema


class FlakyDb:
    def __init__(self, error):
        self.error = error
        self.calls = 0
        self.rollbacks = 0

    def execute(self, sql, params=None):
        self.calls += 1
        if self.calls == 1:
            raise self.error
        return {"ok": True}

    def rollback(self):
        self.rollbacks += 1


class TptMediaRetryTest(unittest.TestCase):
    def test_retryable_db_write_recovers_from_deadlock_once(self):
        db = FlakyDb(RuntimeError("deadlock detected while updating tpt_jingdian"))

        with patch.object(service.time, "sleep"):
            result = service._execute_db_write_with_retry(db, "UPDATE tpt_jingdian SET image_status=?", ("error",))

        self.assertEqual(result, {"ok": True})
        self.assertEqual(db.calls, 2)
        self.assertEqual(db.rollbacks, 1)

    def test_non_retryable_db_write_is_not_retried(self):
        db = FlakyDb(RuntimeError("syntax error near UPDATE"))

        with self.assertRaises(RuntimeError):
            service._execute_db_write_with_retry(db, "UPDATE broken", ())

        self.assertEqual(db.calls, 1)
        self.assertEqual(db.rollbacks, 0)

    def test_forced_local_profile_does_not_overwrite_public_profile_source(self):
        scenic = {
            "name": "测试景区",
            "province": "浙江省",
            "city": "杭州市",
            "district": "西湖区",
            "official_level": "5A",
            "summary": "测试景区是公开来源整理的景区。",
            "description": "测试景区是公开来源整理的景区，拥有真实的历史文化介绍。",
            "profile_source": "维基百科",
            "profile_source_url": "https://zh.wikipedia.org/wiki/test",
        }

        patch = service._build_tpt_profile_patch(scenic, force=True)

        self.assertNotIn("profile_source", patch)
        self.assertNotIn("profile_source_url", patch)
        self.assertNotIn("profile_updated_at", patch)

    def test_public_profile_replaces_local_rule_text_even_when_shorter(self):
        scenic = {
            "name": "首都博物馆",
            "summary": "首都博物馆位于北京市西城区，属于4A目的地，核心特色偏向历史文化，适合人文探访、研学旅行、建筑摄影和城市漫步。",
            "description": "首都博物馆位于北京市西城区，地址为复兴门外大街16号。站内根据全国景点源表、行政区划、A 级标识、分类标签和坐标信息整理为历史文化类旅游目的地。",
            "profile_source": "local_rule_v2",
        }
        candidate = {
            "content": "首都博物馆位于北京市西城区复兴门外大街16号，是北京市大型综合性博物馆。",
            "source_name": "维基百科",
            "source_type": "wikipedia",
            "source_url": "https://zh.wikipedia.org/wiki/首都博物馆",
        }

        patch = service._profile_patch_from_candidate(scenic, candidate)

        self.assertEqual(patch["summary"], candidate["content"])
        self.assertEqual(patch["description"], candidate["content"])
        self.assertEqual(patch["profile_source"], "维基百科")

    def test_short_name_public_profile_requires_region_evidence(self):
        scenic = {
            "name": "灵山景区",
            "province": "江苏省",
            "city": "无锡市",
            "district": "滨湖区",
            "description": "灵山景区位于江苏省无锡市滨湖区。",
            "profile_source": "local_rule_v2",
        }
        wrong_candidate = {
            "content": "灵山是广西壮族自治区钦州市所辖的一个县，县城距南宁市120公里。",
            "source_url": "https://zh.wikivoyage.org/wiki/灵山",
            "source_name": "维基导游",
            "source_type": "wikivoyage",
            "raw_payload_json": {"title": "灵山"},
        }
        right_candidate = {
            "content": "灵山景区位于江苏省无锡市滨湖区马山镇，是无锡太湖沿岸的佛教文化旅游景区。",
            "source_url": "https://example.test/wuxi-lingshan",
            "source_name": "公开来源",
            "source_type": "wikipedia",
            "raw_payload_json": {"title": "灵山景区"},
        }

        self.assertEqual(service._profile_patch_from_candidate(scenic, wrong_candidate), {})
        self.assertIn("无锡太湖", service._profile_patch_from_candidate(scenic, right_candidate)["description"])

    def test_rate_limited_status_requires_all_public_image_sources_blocked(self):
        commons_only = [{"provider": "wikimedia_commons", "status": "rate_limited"}]
        all_sources = [
            {"provider": "wikipedia", "status": "rate_limited"},
            {"provider": "wikivoyage", "status": "rate_limited"},
            {"provider": "wikimedia_commons", "status": "rate_limited"},
            {"provider": "openverse", "status": "rate_limited"},
        ]

        self.assertFalse(service._all_public_image_sources_rate_limited(commons_only))
        self.assertTrue(service._all_public_image_sources_rate_limited(all_sources))

    def test_direct_commons_image_must_match_scenic_text_before_approval(self):
        scenic = {"name": "黄陂木兰文化生态旅游区", "province": "湖北省", "city": "武汉市"}
        wrong_image = {
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/7/72/ISS066-E-73685_-_View_of_Earth.jpg",
            "source_url": "https://commons.wikimedia.org/wiki/File:ISS066-E-73685_-_View_of_Earth.jpg",
            "title": "ISS view of Earth",
            "source_name": "Wikimedia Commons",
            "source_type": "wikimedia_commons",
            "license": "CC BY-SA 4.0",
            "attribution": "NASA",
        }
        matching_image = {
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/mulan.jpg",
            "source_url": "https://commons.wikimedia.org/wiki/File:%E9%BB%84%E9%99%82%E6%9C%A8%E5%85%B0%E6%96%87%E5%8C%96%E7%94%9F%E6%80%81%E6%97%85%E6%B8%B8%E5%8C%BA.jpg",
            "title": "黄陂木兰文化生态旅游区",
            "source_name": "Wikimedia Commons",
            "source_type": "wikimedia_commons",
            "license": "CC BY-SA 4.0",
            "attribution": "Tester",
        }

        self.assertEqual(service._image_patch_from_candidates(scenic, [wrong_image]), {})
        self.assertEqual(
            service._image_patch_from_candidates(scenic, [matching_image])["cover_image_url"],
            "https://upload.wikimedia.org/wikipedia/commons/mulan.jpg",
        )

    def test_wikipedia_cover_gallery_does_not_mix_openverse_third_party_urls(self):
        scenic = {"name": "首都博物馆", "province": "北京市", "city": "北京市"}
        wiki_image = {
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/3/36/Capital_Museum_in_Beijing.jpg",
            "source_url": "https://zh.wikipedia.org/wiki/首都博物馆",
            "source_name": "维基百科",
            "source_type": "wikipedia",
        }
        openverse_image = {
            "image_url": "https://live.staticflickr.com/3204/2768255404_196f76c448_b.jpg",
            "source_url": "https://www.flickr.com/photos/example",
            "source_name": "Openverse",
            "source_type": "openverse",
            "title": "首都博物馆",
        }

        patch = service._image_patch_from_candidates(scenic, [wiki_image, openverse_image])

        self.assertEqual(json.loads(patch["gallery"]), [wiki_image["image_url"]])

    def test_detail_enrichment_writes_public_profile_and_image_for_missing_source_row(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        ensure_tpt_jingdian_schema(conn)
        conn.execute(
            """
            INSERT INTO tpt_jingdian (
              source_id,name,province,city,district,official_level,summary,description,
              profile_source,cover_image_url,image_status,quality_score
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                522,
                "首都博物馆",
                "北京市",
                "北京市",
                "西城区",
                "4A",
                "首都博物馆本地规则简介",
                "首都博物馆本地规则详情",
                "local_rule_v2",
                "",
                "not_found",
                88,
            ),
        )
        scenic = dict(conn.execute("SELECT * FROM tpt_jingdian WHERE source_id=522").fetchone())
        profile = {
            "content": "首都博物馆位于北京市西城区复兴门外大街16号，是北京市大型综合性博物馆。",
            "source_url": "https://zh.wikipedia.org/wiki/首都博物馆",
            "source_name": "维基百科",
            "source_type": "wikipedia",
        }
        image = {
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/3/36/Capital_Museum_in_Beijing.jpg",
            "source_url": "https://zh.wikipedia.org/wiki/首都博物馆",
            "source_name": "维基百科",
            "source_type": "wikipedia",
            "license": "CC BY-SA 3.0",
            "attribution": "PENG Yanan",
        }

        with patch.object(service, "public_source_bundle_detailed", return_value=([profile], [image], [])):
            updated = service.enrich_tpt_detail_if_missing(conn, scenic)

        self.assertEqual(updated["cover_image_url"], image["image_url"])
        self.assertEqual(updated["profile_source"], "维基百科")
        self.assertIn("大型综合性博物馆", updated["description"])
        row = dict(conn.execute("SELECT * FROM tpt_jingdian WHERE source_id=522").fetchone())
        self.assertEqual(row["cover_image_url"], image["image_url"])
        self.assertEqual(row["image_status"], "approved_external_url")


if __name__ == "__main__":
    unittest.main()
