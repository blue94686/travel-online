import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "enrich_scenic_content.py"
spec = importlib.util.spec_from_file_location("enrich_scenic_content", SCRIPT_PATH)
script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(script)


class EnrichScenicContentScriptTest(unittest.TestCase):
    def test_analyze_sql_source_reads_table_columns_and_insert_count(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sql_path = Path(tmpdir) / "sample.sql"
            sql_path.write_text(
                """
                CREATE TABLE `tpt_data_jingdian` (
                  `id` int(11) NOT NULL AUTO_INCREMENT,
                  `title` varchar(67) DEFAULT NULL,
                  `type` varchar(176) DEFAULT NULL,
                  PRIMARY KEY (`id`)
                );
                INSERT INTO `tpt_data_jingdian` VALUES ('1', '测试景区', '风景名胜');
                INSERT INTO `tpt_data_jingdian` VALUES ('2', '测试公园', '公园广场');
                """,
                encoding="utf-8",
            )

            result = script.analyze_sql_source(sql_path)

            self.assertEqual(result["table"], "tpt_data_jingdian")
            self.assertEqual(result["insert_rows"], 2)
            self.assertIn("title", result["columns"])

    def test_run_batch_calls_external_service_with_cli_options(self):
        with patch.object(script, "external_enrich_profile_batch") as batch:
            batch.return_value = {"requested": 2, "profile_candidates": 1, "image_candidates": 1}
            result = script.run_batch(limit=2, offset=4, province="河北省", city="保定市", include_public_sources=False, sleep_seconds=0)

        self.assertEqual(result["batch"]["requested"], 2)
        batch.assert_called_once_with(
            limit=2,
            offset=4,
            province="河北省",
            city="保定市",
            only_missing_media=True,
            include_public_sources=False,
            sleep_seconds=0,
        )


if __name__ == "__main__":
    unittest.main()
