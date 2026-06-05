import unittest

from app.services import scenic_sql_import_service as service


class FakeCursor:
    def fetchone(self):
        return {"id": 42}


class FakePostgresDb:
    def __init__(self):
        self.calls = []

    def execute(self, sql, params=()):
        self.calls.append((sql, params))
        return FakeCursor()


class ScenicSqlImportPostgresTest(unittest.TestCase):
    def test_create_import_task_reads_returning_id_when_lastrowid_is_unavailable(self):
        db = FakePostgresDb()

        task_id = service._create_import_task(db, "/tmp/tpt_data_jingdian.sql", 3978, 0, 1000, "")

        self.assertEqual(task_id, 42)
        self.assertIn("RETURNING id", db.calls[0][0])

    def test_finish_import_task_avoids_timestamp_text_case_expression(self):
        db = FakePostgresDb()

        service._finish_import_task(db, 42, "finished", 3978, 0, 0, 3978)

        sql_text = "\n".join(sql for sql, _ in db.calls)
        self.assertNotIn("CASE WHEN", sql_text)
        self.assertIn("finished_at=CURRENT_TIMESTAMP", sql_text)


if __name__ == "__main__":
    unittest.main()
