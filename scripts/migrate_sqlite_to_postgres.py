#!/usr/bin/env python3
import argparse
import os
import sqlite3
import sys
from pathlib import Path


def quote_ident(value: str) -> str:
    if not value.replace("_", "").isalnum() or value[0].isdigit():
        raise ValueError(f"Unsafe identifier: {value}")
    return f'"{value}"'


def sqlite_tables(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [row["name"] for row in rows if not row["name"].endswith(("_fts_data", "_fts_idx", "_fts_docsize", "_fts_config"))]


def sqlite_columns(conn, table):
    return [row["name"] for row in conn.execute(f"PRAGMA table_info({quote_ident(table)})").fetchall()]


def postgres_tables(conn):
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public' AND table_type='BASE TABLE'
            ORDER BY table_name
            """
        )
        return {row[0] for row in cursor.fetchall()}


def postgres_columns(conn, table):
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name=%s
            ORDER BY ordinal_position
            """,
            (table,),
        )
        return [row[0] for row in cursor.fetchall()]


def batched_rows(sqlite_conn, table, columns, batch_size):
    quoted_table = quote_ident(table)
    quoted_columns = ", ".join(quote_ident(column) for column in columns)
    cursor = sqlite_conn.execute(f"SELECT {quoted_columns} FROM {quoted_table}")
    while True:
        rows = cursor.fetchmany(batch_size)
        if not rows:
            break
        yield [[row[column] for column in columns] for row in rows]


def update_sequences(pg_conn, table):
    with pg_conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema='public'
              AND table_name=%s
              AND column_default LIKE 'nextval%%'
            """,
            (table,),
        )
        sequence_columns = [row[0] for row in cursor.fetchall()]
        for column in sequence_columns:
            cursor.execute("SELECT pg_get_serial_sequence(%s, %s)", (table, column))
            sequence = cursor.fetchone()[0]
            if not sequence:
                continue
            cursor.execute(
                f"""
                SELECT setval(
                  %s,
                  GREATEST(COALESCE((SELECT MAX({quote_ident(column)}) FROM {quote_ident(table)}), 0), 1),
                  true
                )
                """,
                (sequence,),
            )


def initialize_schema(database_url):
    os.environ["DATABASE_URL"] = database_url
    backend_dir = Path(__file__).resolve().parents[1] / "backend"
    sys.path.insert(0, str(backend_dir))
    from app.core.database import init_db

    init_db()


def migrate(sqlite_path, database_url, batch_size=2000):
    try:
        import psycopg
    except ImportError as exc:
        raise SystemExit("缺少 psycopg，请先在 backend 环境运行 pip install -r backend/requirements.txt") from exc

    if not sqlite_path.exists():
        raise SystemExit(f"SQLite 文件不存在: {sqlite_path}")

    initialize_schema(database_url)

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    pg_conn = psycopg.connect(database_url)
    try:
        source_tables = sqlite_tables(sqlite_conn)
        target_tables = postgres_tables(pg_conn)
        summary = []
        for table in source_tables:
            if table not in target_tables:
                summary.append((table, "skipped", "target_missing", 0))
                continue
            source_columns = sqlite_columns(sqlite_conn, table)
            target_columns = postgres_columns(pg_conn, table)
            columns = [column for column in source_columns if column in target_columns]
            if not columns:
                summary.append((table, "skipped", "no_common_columns", 0))
                continue
            placeholders = ", ".join(["%s"] * len(columns))
            insert_sql = (
                f"INSERT INTO {quote_ident(table)} "
                f"({', '.join(quote_ident(column) for column in columns)}) "
                f"VALUES ({placeholders}) ON CONFLICT DO NOTHING"
            )
            imported = 0
            with pg_conn.cursor() as cursor:
                for batch in batched_rows(sqlite_conn, table, columns, batch_size):
                    cursor.executemany(insert_sql, batch)
                    imported += len(batch)
            update_sequences(pg_conn, table)
            pg_conn.commit()
            summary.append((table, "copied", "", imported))
        return summary
    finally:
        sqlite_conn.close()
        pg_conn.close()


def main():
    parser = argparse.ArgumentParser(description="Migrate Scenic Online SQLite data into PostgreSQL.")
    parser.add_argument("--sqlite", default="backend/app/data/scenic_online.sqlite3", help="SQLite database path")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", ""), help="PostgreSQL DATABASE_URL")
    parser.add_argument("--batch-size", type=int, default=2000)
    args = parser.parse_args()
    if not args.database_url:
        raise SystemExit("请提供 --database-url 或设置 DATABASE_URL")
    summary = migrate(Path(args.sqlite), args.database_url, args.batch_size)
    for table, status, reason, rows in summary:
        suffix = f" ({reason})" if reason else ""
        print(f"{table}: {status}{suffix}, rows={rows}")


if __name__ == "__main__":
    main()
