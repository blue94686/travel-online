import sqlite3
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from fastapi import HTTPException

from app.routers import user as user_router
from app.core.auth import hash_password, verify_password
from app.routers.user import EmailCodePayload, LoginPayload, RegisterPayload


class AuthCodeTest(unittest.TestCase):
    def make_db(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(
            """
            CREATE TABLE auth_codes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              email TEXT NOT NULL,
              code TEXT NOT NULL,
              purpose TEXT DEFAULT 'login',
              expires_at TEXT NOT NULL,
              created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              email TEXT UNIQUE NOT NULL,
              password_hash TEXT DEFAULT '',
              nickname TEXT,
              role TEXT DEFAULT 'user',
              status TEXT DEFAULT 'active'
            );
            """
        )
        return conn

    @contextmanager
    def patched_db(self, conn):
        @contextmanager
        def fake_get_db():
            yield conn
            conn.commit()

        with patch.object(user_router, "get_db", fake_get_db), patch.object(user_router, "write_audit"):
            yield

    def test_send_code_response_does_not_expose_code(self):
        conn = self.make_db()
        with self.patched_db(conn), patch.object(user_router.random, "randint", return_value=1):
            response = user_router.send_auth_code(EmailCodePayload(email="traveler@example.com"))

        self.assertEqual(response["message"], "验证码已发送")
        self.assertNotIn("111111", response["message"])

    def test_password_login_rejects_wrong_password(self):
        conn = self.make_db()
        conn.execute(
            "INSERT INTO users (email, password_hash, nickname, role, status) VALUES (?, ?, ?, ?, ?)",
            ("traveler@example.com", hash_password("Right123456"), "traveler", "user", "active"),
        )
        with self.patched_db(conn):
            with self.assertRaises(HTTPException) as raised:
                user_router.login_with_password(LoginPayload(email="traveler@example.com", password="Wrong123456"))

        self.assertEqual(raised.exception.status_code, 401)

    def test_password_login_returns_existing_user(self):
        conn = self.make_db()
        conn.execute(
            "INSERT INTO users (email, password_hash, nickname, role, status) VALUES (?, ?, ?, ?, ?)",
            ("traveler@example.com", hash_password("Traveler123"), "traveler", "user", "active"),
        )
        with self.patched_db(conn):
            response = user_router.login_with_password(LoginPayload(email="traveler@example.com", password="Traveler123"))

        self.assertTrue(response["success"])
        self.assertEqual(response["data"]["user"]["email"], "traveler@example.com")
        self.assertIn("token", response["data"])

    def test_register_with_code_creates_password_user(self):
        conn = self.make_db()
        conn.execute(
            "INSERT INTO auth_codes (email, code, expires_at) VALUES (?, ?, datetime('now', '+10 minutes'))",
            ("traveler@example.com", "123456"),
        )
        with self.patched_db(conn):
            response = user_router.register_with_code(
                RegisterPayload(email="traveler@example.com", password="Traveler123", code="123456")
            )

        self.assertTrue(response["success"])
        self.assertEqual(response["data"]["user"]["email"], "traveler@example.com")
        self.assertEqual(response["data"]["user"]["nickname"], "traveler")
        row = conn.execute("SELECT password_hash FROM users WHERE email='traveler@example.com'").fetchone()
        self.assertTrue(verify_password("Traveler123", row["password_hash"]))
        self.assertIsNone(conn.execute("SELECT 1 FROM auth_codes WHERE email='traveler@example.com'").fetchone())


if __name__ == "__main__":
    unittest.main()
