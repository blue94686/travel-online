import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.services.tpt_jingdian_importer import import_tpt_jingdian_sql


MEDIA_SAMPLE_SQL = """SET FOREIGN_KEY_CHECKS=0;
INSERT INTO `tpt_data_jingdian` VALUES ('3', '黄山风景区', '', '黄山区汤口镇', '风景名胜;国家A级景区;5A景区', '341003', 'B3', '118.170', '30.130', '118.170', '30.130', '安徽省', '黄山市', '黄山区', '5A景区', 'nature,photo', '自然风光,摄影', '全国景点,5A景区,国家A级景区', '黄山风景区是安徽省黄山市黄山区的5A旅游景区。', '公开网页核验描述', '四季皆宜', '普通游客', '1天', '景区入口 - 核心游览点', '96', '2026-web-a-level-v1', '2026-06-03T10:00:00', '5A', '测试来源', 'https://example.test/5a', '2026-06-03', '2007', '安徽省', '黄山市', '黄山区', '安徽省黄山市黄山区', '118.170', '30.130', 'official_reference', '等级已核验', 'https://upload.wikimedia.org/example.jpg', '[\"https://upload.wikimedia.org/example.jpg\"]', 'Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Example.jpg', 'CC BY-SA 4.0', 'Example Author', 'approved_external_url', '2026-06-04T09:00:00', '维基百科', 'https://zh.wikipedia.org/wiki/黄山', '2026-06-04T09:00:00');
"""


class TptJingdianMediaColumnsTest(unittest.TestCase):
    def test_import_reads_media_and_profile_columns_from_sql(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tpt_data_jingdian.sql"
            path.write_text(MEDIA_SAMPLE_SQL, encoding="utf-8")
            conn = sqlite3.connect(":memory:")
            conn.row_factory = sqlite3.Row

            imported = import_tpt_jingdian_sql(conn, path, batch_size=1)
            item = conn.execute("SELECT * FROM tpt_jingdian WHERE source_id=3").fetchone()

        self.assertEqual(imported, 1)
        self.assertEqual(item["cover_image_url"], "https://upload.wikimedia.org/example.jpg")
        self.assertEqual(item["image_source"], "Wikimedia Commons")
        self.assertEqual(item["image_license"], "CC BY-SA 4.0")
        self.assertEqual(item["profile_source"], "维基百科")
        self.assertEqual(item["profile_source_url"], "https://zh.wikipedia.org/wiki/黄山")


if __name__ == "__main__":
    unittest.main()
