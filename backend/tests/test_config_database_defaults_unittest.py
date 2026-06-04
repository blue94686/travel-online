import importlib
import os
import unittest
from unittest.mock import patch

import app.core.config as config


class ConfigDatabaseDefaultsTest(unittest.TestCase):
    def reload_config(self, env):
        with patch.dict(os.environ, env, clear=True):
            return importlib.reload(config)

    def tearDown(self):
        importlib.reload(config)

    def test_postgres_is_the_default_development_database(self):
        loaded = self.reload_config({})

        self.assertEqual(loaded.DATABASE_BACKEND, "postgresql")
        self.assertEqual(loaded.DATABASE_URL, "postgresql://scenic:scenic@localhost:5432/scenic_online")

    def test_sqlite_is_available_only_when_explicitly_requested(self):
        loaded = self.reload_config({"SCENIC_DATABASE_BACKEND": "sqlite"})

        self.assertEqual(loaded.DATABASE_BACKEND, "sqlite")
        self.assertEqual(loaded.DATABASE_URL, "")

    def test_custom_database_url_overrides_the_default(self):
        loaded = self.reload_config({"DATABASE_URL": "postgresql://user:pass@db:5432/app"})

        self.assertEqual(loaded.DATABASE_BACKEND, "postgresql")
        self.assertEqual(loaded.DATABASE_URL, "postgresql://user:pass@db:5432/app")

    def test_tpt_jingdian_sql_path_can_be_overridden_by_environment(self):
        loaded = self.reload_config({"TPT_JINGDIAN_SQL_PATH": "/app/backend/tpt_data_jingdian.sql"})

        self.assertEqual(str(loaded.TPT_JINGDIAN_SQL_PATH), "/app/backend/tpt_data_jingdian.sql")


if __name__ == "__main__":
    unittest.main()
