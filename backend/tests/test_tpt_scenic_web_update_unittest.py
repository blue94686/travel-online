import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "update_tpt_scenic_from_web.py"
spec = importlib.util.spec_from_file_location("update_tpt_scenic_from_web", SCRIPT_PATH)
web_update = importlib.util.module_from_spec(spec)
spec.loader.exec_module(web_update)


SAMPLE_SQL = """SET FOREIGN_KEY_CHECKS=0;
INSERT INTO `tpt_data_jingdian` VALUES ('1', '黄山风景区', '', '黄山区汤口镇', '风景名胜;国家级景点;风景名胜', '341003', 'B1', '118.170', '30.130', '118.170', '30.130', '安徽省', '黄山市', '黄山区', '风景名胜', 'nature,photo', '自然风光,摄影', '全国景点', '黄山风景区是安徽省黄山市黄山区的风景名胜。', '旧描述', '四季皆宜', '普通游客', '1天', '景区入口 - 核心游览点', '82', '2026-theme-v1', '2026-06-03T10:00:00');
INSERT INTO `tpt_data_jingdian` VALUES ('2', '普通公园', '', '人民路', '风景名胜;公园广场;公园', '110101', 'B2', '116.400', '39.900', '116.400', '39.900', '北京市', '北京市', '东城区', '公园', 'nature', '自然风光', '全国景点', '普通公园是北京市的公园。', '旧描述', '四季皆宜', '普通游客', '2小时', '公园入口 - 中心广场', '60', '2026-theme-v1', '2026-06-03T10:00:00');
"""


class TptScenicWebUpdateTest(unittest.TestCase):
    def test_kcloud_records_are_normalized_to_web_scenic(self):
        provinces = [{
            "id": "p1",
            "name": "安徽省",
            "scenicSpots": [{
                "name": "黄山风景区",
                "aLevel": "5A",
                "longitude": 118.170,
                "latitude": 30.130,
                "cityName": "黄山市",
                "districtName": "黄山区",
            }],
        }]

        records = web_update.scenic_from_kcloud(provinces)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].name, "黄山风景区")
        self.assertEqual(records[0].a_level, "5A")
        self.assertEqual(records[0].province, "安徽省")
        self.assertEqual(records[0].address, "安徽省黄山市黄山区")
        self.assertEqual(records[0].source_confidence, "high_auxiliary")

    def test_merge_updates_level_source_and_keeps_existing_theme_data(self):
        rows, errors = self._read_sample_rows()
        self.assertEqual(errors, [])
        record = web_update.WebScenic(
            name="黄山风景名胜区",
            a_level="5A",
            province="安徽省",
            city="黄山市",
            district="黄山区",
            address="安徽省黄山市黄山区汤口镇",
            longitude="118.170",
            latitude="30.130",
            source_name="测试来源",
            source_url="https://example.test/scenic",
            source_confidence="official_reference",
            a_level_year="2007",
        )

        result = web_update.merge_web_records(rows, [record], append_missing=False)
        row = result["rows"][0]

        self.assertEqual(result["match_counts"]["name_region"], 1)
        self.assertEqual(row["official_level"], "5A")
        self.assertEqual(row["level_source"], "测试来源")
        self.assertEqual(row["a_level_year"], "2007")
        self.assertIn("5A景区", row["tags"])
        self.assertIn("photo", row["theme_slugs"])
        self.assertIn("nature", row["theme_slugs"])
        self.assertGreaterEqual(int(row["quality_score"]), 96)

    def test_unmatched_web_record_can_be_appended_as_new_sql_row(self):
        rows, _ = self._read_sample_rows()
        record = web_update.WebScenic(
            name="新景区",
            a_level="4A",
            province="浙江省",
            city="丽水市",
            district="云和县",
            longitude="119.50",
            latitude="28.10",
            source_name="测试来源",
            source_url="https://example.test/4a",
            source_confidence="high_auxiliary",
        )

        result = web_update.merge_web_records(rows, [record], append_missing=True)
        appended = result["rows"][-1]

        self.assertEqual(result["match_counts"]["appended"], 1)
        self.assertEqual(appended["id"], 3)
        self.assertEqual(appended["official_level"], "4A")
        self.assertEqual(appended["province"], "浙江省")
        self.assertIn("国家A级景区", appended["tags"])

    def test_write_and_read_extended_schema_round_trips(self):
        rows, _ = self._read_sample_rows()
        record = web_update.WebScenic(name="黄山风景区", a_level="5A", province="安徽省", source_name="测试来源")
        updated = web_update.merge_web_records(rows, [record])["rows"]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tpt_data_jingdian.sql"
            web_update.write_sql(path, updated)
            reread, errors = web_update.read_rows(path)

        self.assertEqual(errors, [])
        self.assertEqual(len(reread), 2)
        self.assertEqual(reread[0]["official_level"], "5A")
        self.assertEqual(reread[0]["level_source"], "测试来源")

    def _read_sample_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.sql"
            path.write_text(SAMPLE_SQL, encoding="utf-8")
            return web_update.read_rows(path)


if __name__ == "__main__":
    unittest.main()
