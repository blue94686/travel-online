import unittest

from app.core.database_adapters import translate_postgres_sql


class PostgresSqlTranslationTest(unittest.TestCase):
    def test_escapes_percent_inside_string_literals_for_psycopg(self):
        translated = translate_postgres_sql(
            "SELECT 1 FROM scenic_spots WHERE source_url LIKE 'local-sql:tpt_data_jingdian:%'"
        )

        self.assertIn("LIKE 'local-sql:tpt_data_jingdian:%%'", translated)

    def test_keeps_postgres_placeholders_outside_string_literals(self):
        translated = translate_postgres_sql(
            "SELECT * FROM scenic_spots WHERE name LIKE ? AND source_url LIKE 'local-sql:%'"
        )

        self.assertIn("name LIKE %s", translated)
        self.assertIn("source_url LIKE 'local-sql:%%'", translated)

    def test_rejects_sqlite_insert_or_replace_from_postgres_queries(self):
        translated = translate_postgres_sql(
            """
            INSERT OR REPLACE INTO nearby_recommendations
            (scenic_id,recommended_scenic_id,reason,distance_text,score,source)
            VALUES (?,?,?,?,?,?)
            """
        )

        self.assertNotIn("INSERT OR REPLACE", translated.upper())


if __name__ == "__main__":
    unittest.main()
