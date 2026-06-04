import sqlite3
import tempfile
from pathlib import Path


from app.services.tpt_jingdian_importer import (
    ensure_tpt_jingdian_loaded,
    import_tpt_jingdian_sql,
    iter_tpt_jingdian_rows,
    normalize_tpt_jingdian_row,
)


SAMPLE_SQL = """SET FOREIGN_KEY_CHECKS=0;
INSERT INTO `tpt_data_jingdian` VALUES ('1', '礼王府', '', '西黄城根南街9号', '风景名胜;风景名胜;风景名胜', '110102', 'B000A81F8Z', '116.377178', '39.919584', '116.370948', '39.918193');
INSERT INTO `tpt_data_jingdian` VALUES ('2', '北京动物园(北2门)', '', '五塔寺路22号', '风景名胜;公园广场;动物园', '110108', 'B000A81FAR', '116.333487', '39.944157', '116.327336', '39.942834');
"""

EXTENDED_SAMPLE_SQL = """SET FOREIGN_KEY_CHECKS=0;
INSERT INTO `tpt_data_jingdian` VALUES ('3', '黄山风景区', '', '黄山区汤口镇', '风景名胜;国家A级景区;5A景区', '341003', 'B3', '118.170', '30.130', '118.170', '30.130', '安徽省', '黄山市', '黄山区', '5A景区', 'nature,photo', '自然风光,摄影', '全国景点,5A景区,国家A级景区', '黄山风景区是安徽省黄山市黄山区的5A旅游景区。', '公开网页核验描述', '四季皆宜', '普通游客', '1天', '景区入口 - 核心游览点', '96', '2026-web-a-level-v1', '2026-06-03T10:00:00', '5A', '测试来源', 'https://example.test/5a', '2026-06-03', '2007', '安徽省', '黄山市', '黄山区', '安徽省黄山市黄山区', '118.170', '30.130', 'official_reference', '等级已核验');
"""


def test_iter_tpt_jingdian_rows_streams_insert_values():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "tpt_data_jingdian.sql"
        path.write_text(SAMPLE_SQL, encoding="utf-8")

        rows = list(iter_tpt_jingdian_rows(path))

    assert len(rows) == 2
    assert rows[0]["id"] == 1
    assert rows[0]["title"] == "礼王府"
    assert rows[0]["address"] == "西黄城根南街9号"
    assert rows[0]["longitude"] == 116.370948
    assert rows[0]["latitude"] == 39.918193


def test_normalize_tpt_jingdian_row_maps_to_project_fields():
    item = normalize_tpt_jingdian_row(
        {
            "id": 2,
            "title": "北京动物园(北2门)",
            "tel": "",
            "address": "五塔寺路22号",
            "type": "风景名胜;公园广场;动物园",
            "areaid": "110108",
            "poiid": "B000A81FAR",
            "gcjx": "116.333487",
            "gcjy": "39.944157",
            "longitude": 116.327336,
            "latitude": 39.942834,
        }
    )

    assert item["source_id"] == 2
    assert item["name"] == "北京动物园(北2门)"
    assert item["category"] == "动物园"
    assert item["province_code"] == "11"
    assert item["city_code"] == "1101"
    assert item["district_code"] == "110108"


def test_import_tpt_jingdian_sql_uses_batch_upsert():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "tpt_data_jingdian.sql"
        path.write_text(SAMPLE_SQL, encoding="utf-8")
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row

        imported = import_tpt_jingdian_sql(conn, path, batch_size=1)
        imported_again = import_tpt_jingdian_sql(conn, path, batch_size=1)
        count = conn.execute("SELECT COUNT(*) AS c FROM tpt_jingdian").fetchone()["c"]

    assert imported == 2
    assert imported_again == 2
    assert count == 2


def test_import_tpt_jingdian_sql_reads_web_level_columns():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "tpt_data_jingdian.sql"
        path.write_text(EXTENDED_SAMPLE_SQL, encoding="utf-8")
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row

        imported = import_tpt_jingdian_sql(conn, path, batch_size=1)
        item = conn.execute("SELECT * FROM tpt_jingdian WHERE source_id=3").fetchone()

    assert imported == 1
    assert item["official_level"] == "5A"
    assert item["level_source_url"] == "https://example.test/5a"
    assert item["web_address"] == "安徽省黄山市黄山区"
    assert "5A景区" in item["search_text"]


def test_ensure_tpt_jingdian_loaded_imports_empty_database_once():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "tpt_data_jingdian.sql"
        path.write_text(SAMPLE_SQL, encoding="utf-8")
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row

        first = ensure_tpt_jingdian_loaded(conn, path)
        second = ensure_tpt_jingdian_loaded(conn, path)
        count = conn.execute("SELECT COUNT(*) AS c FROM tpt_jingdian").fetchone()["c"]

    assert first["imported"] == 2
    assert first["skipped"] is False
    assert second["imported"] == 0
    assert second["skipped"] is True
    assert count == 2
