import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PostgresRuntimeQueriesTest(unittest.TestCase):
    def test_region_provinces_orders_by_aggregated_sort_order(self):
        source = (ROOT / "app/routers/public.py").read_text()

        self.assertIn("MIN(sort_order)", source)
        self.assertIn("ORDER BY province_sort_order, province", source)
        self.assertIn("ORDER BY city_sort_order, city", source)
        self.assertIn("ORDER BY district_sort_order, district", source)

    def test_nearby_generation_uses_postgres_safe_insert(self):
        source = (ROOT / "app/services/nearby_recommendation_service.py").read_text()

        self.assertNotIn("INSERT OR REPLACE", source.upper())

    def test_admin_database_status_is_backend_aware(self):
        source = (ROOT / "app/routers/admin_system.py").read_text()

        self.assertIn("DATABASE_BACKEND", source)
        self.assertIn("PostgreSQL", source)
        self.assertNotIn("healthy = DB_PATH.exists()", source)

    def test_tpt_region_backfill_groups_by_expressions_for_postgres(self):
        source = (ROOT / "app/core/database.py").read_text()

        self.assertIn("GROUP BY substr(areaid,1,2), substr(areaid,1,4), substr(areaid,1,6)", source)
        self.assertNotIn("GROUP BY province_code, city_code, district_code", source)


if __name__ == "__main__":
    unittest.main()
