import sqlite3
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from app.core.database import SCHEMA, migrate_db
from app.services import scenic_enrichment_service


class ScenicProfileEnrichmentTest(unittest.TestCase):
    def make_db(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA)
        migrate_db(conn)
        conn.execute(
            """
            INSERT INTO scenic_spots (
              id, slug, name, province, city, district, level, rating, address,
              latitude, longitude, summary, description, tags, ticket_price,
              opening_hours, best_season, cover_image_url, gallery
            ) VALUES (1, 'test-west-lake', '测试西湖', '浙江省', '杭州市', '西湖区',
              '5A', 4.8, '浙江省杭州市西湖区', NULL, NULL, '', '', '["摄影"]',
              '', '', '', '', '[]')
            """
        )
        return conn

    def run_with_db(self, callback):
        conn = self.make_db()

        @contextmanager
        def fake_db():
            yield conn

        try:
            with patch.object(scenic_enrichment_service, "get_db", fake_db):
                return callback(conn)
        finally:
            conn.close()

    def test_search_creates_pending_candidates_with_source_metadata_without_keys(self):
        def assertions(conn):
            result = scenic_enrichment_service.run_profile_search(1)
            self.assertEqual(result["status"], "success")
            self.assertTrue(result["fallback"])
            self.assertGreaterEqual(result["candidate_count"], 8)

            rows = conn.execute("SELECT * FROM scenic_profile_candidates WHERE scenic_id=1").fetchall()
            self.assertGreaterEqual(len(rows), 8)
            self.assertTrue(all(row["status"] == "pending" for row in rows))
            self.assertTrue(all(row["source_url"] for row in rows))
            self.assertTrue(all(row["source_type"] for row in rows))
            self.assertTrue(all(row["confidence"] >= 0 for row in rows))
            self.assertTrue(any(row["source_type"] == "generated_draft" for row in rows))

            scenic = conn.execute("SELECT summary, description, official_website FROM scenic_spots WHERE id=1").fetchone()
            self.assertEqual(scenic["summary"], "")
            self.assertEqual(scenic["description"], "")
            self.assertEqual(scenic["official_website"], "")

        self.run_with_db(assertions)

    def test_merge_only_publishes_approved_candidates_and_recalculates_score(self):
        def assertions(conn):
            scenic_enrichment_service.run_profile_search(1)
            pending = conn.execute(
                "SELECT id FROM scenic_profile_candidates WHERE scenic_id=1 AND candidate_type='official_site' LIMIT 1"
            ).fetchone()
            rejected = conn.execute(
                "SELECT id FROM scenic_profile_candidates WHERE scenic_id=1 AND candidate_type='ticket' LIMIT 1"
            ).fetchone()

            scenic_enrichment_service.approve_profile_candidate(pending["id"])
            scenic_enrichment_service.reject_profile_candidate(rejected["id"])
            result = scenic_enrichment_service.merge_profile_candidates(1)

            self.assertEqual(result["merged_count"], 1)
            scenic = conn.execute("SELECT official_website, ticket_price, completeness_score FROM scenic_spots WHERE id=1").fetchone()
            self.assertIn("bing.com/search", scenic["official_website"])
            self.assertEqual(scenic["ticket_price"], "")
            self.assertGreater(scenic["completeness_score"], 0)

            merged = conn.execute("SELECT status FROM scenic_profile_candidates WHERE id=?", (pending["id"],)).fetchone()
            self.assertEqual(merged["status"], "merged")

        self.run_with_db(assertions)


if __name__ == "__main__":
    unittest.main()
