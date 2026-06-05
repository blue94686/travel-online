import importlib.util
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "clean_tpt_jingdian_sql.py"
SPEC = importlib.util.spec_from_file_location("clean_tpt_jingdian_sql", SCRIPT_PATH)
cleaner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cleaner)


def _row(row_id, title, category, level="", address="测试地址", areaid="110101", lon="116.1", lat="39.9"):
    values = [
        str(row_id),
        title,
        "",
        address,
        category,
        areaid,
        f"POI{row_id}",
        lon,
        lat,
        lon,
        lat,
        "北京市",
        "北京市",
        "东城区",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        level,
        "测试来源",
        "https://example.test/source",
        "2026-06-04",
        "2026",
        "北京市",
        "北京市",
        "东城区",
        address,
        lon,
        lat,
        "official_reference",
        "",
    ]
    return cleaner.row_from_values(values)


class CleanTptJingdianSqlTest(unittest.TestCase):
    def test_deduplicate_major_only_keeps_4a_5a_and_removes_minor_destinations(self):
        rows = [
            _row(1, "黄山风景区", "风景名胜;国家A级景区;5A景区", "5A"),
            _row(2, "普通小公园", "风景名胜;公园广场;公园", ""),
            _row(3, "龙庆峡风景区", "风景名胜;国家A级景区;4A景区", "4A"),
        ]

        kept, removed, reasons, _samples = cleaner.deduplicate(rows, major_only=True)

        self.assertEqual([row["id"] for row in kept], [1, 3])
        self.assertEqual(removed[2], "not_major_scenic_level")
        self.assertEqual(reasons["not_major_scenic_level"], 1)

    def test_deduplicate_major_only_removes_accessory_even_when_marked_4a(self):
        rows = [
            _row(1, "瑞云山风景区", "风景名胜;国家A级景区;4A景区", "4A"),
            _row(2, "瑞云山风景区服务中心", "风景名胜;国家A级景区;4A景区", "4A"),
            _row(3, "某景区旅游集散中心", "风景名胜;国家A级景区;5A景区", "5A"),
            _row(4, "长隆旅游度假区(南大路入口)", "风景名胜;国家A级景区;5A景区", "5A"),
        ]

        kept, removed, reasons, _samples = cleaner.deduplicate(rows, major_only=True)

        self.assertEqual([row["id"] for row in kept], [1])
        self.assertEqual(removed[2], "accessory_facility")
        self.assertEqual(removed[3], "accessory_facility")
        self.assertEqual(removed[4], "accessory_gate_or_entrance")
        self.assertEqual(reasons["accessory_facility"], 2)

    def test_deduplicate_major_only_merges_same_name_same_region(self):
        rows = [
            _row(1, "鳄鱼山景区", "风景名胜;国家A级景区;5A景区", "5A", address="涠洲岛火山国家地质公园", lon="109.09725", lat="21.013033"),
            _row(2, "鳄鱼山景区", "风景名胜;国家A级景区;4A景区", "4A", address="广西壮族自治区北海市海城区", lon="109.40243", lat="21.3094"),
            _row(3, "其他5A景区", "风景名胜;国家A级景区;5A景区", "5A"),
        ]

        kept, removed, reasons, _samples = cleaner.deduplicate(rows, major_only=True)

        self.assertEqual([row["id"] for row in kept], [1, 3])
        self.assertEqual(removed[2], "duplicate_same_title_region")
        self.assertEqual(reasons["duplicate_same_title_region"], 1)


if __name__ == "__main__":
    unittest.main()
