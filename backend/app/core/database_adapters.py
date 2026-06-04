import re
from contextlib import suppress

from app.core.config import DATABASE_URL


def is_postgres_enabled():
    return (DATABASE_URL or "").startswith(("postgresql://", "postgres://"))


class CompatRow(dict):
    def __init__(self, keys, values):
        super().__init__(zip(keys, values))
        self._keys = list(keys)
        self._values = list(values)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return super().__getitem__(key)


class CompatCursor:
    def __init__(self, rows=None, rowcount=-1):
        self._rows = rows or []
        self.rowcount = rowcount

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows


def _replace_qmarks(sql):
    result = []
    in_single = False
    in_double = False
    escaped = False
    for char in sql:
        if char == "\\" and in_single:
            escaped = not escaped
            result.append(char)
            continue
        if char == "'" and not in_double and not escaped:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        if char == "?" and not in_single and not in_double:
            result.append("%s")
        else:
            result.append(char)
        escaped = False
    return "".join(result)


def _escape_percent_in_string_literals(sql):
    result = []
    in_single = False
    in_double = False
    escaped = False
    for char in sql:
        if char == "\\" and in_single:
            escaped = not escaped
            result.append(char)
            continue
        if char == "'" and not in_double and not escaped:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        if char == "%" and in_single:
            result.append("%%")
        else:
            result.append(char)
        escaped = False
    return "".join(result)


def _split_script(script):
    statements = []
    current = []
    in_single = False
    in_double = False
    for char in script:
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        if char == ";" and not in_single and not in_double:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
        else:
            current.append(char)
    tail = "".join(current).strip()
    if tail:
        statements.append(tail)
    return statements


def _translate_insert_or_ignore(sql):
    match = re.match(r"(\s*)INSERT\s+OR\s+IGNORE\s+INTO\s+(.+)", sql, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return sql
    prefix, rest = match.groups()
    if re.search(r"\bON\s+CONFLICT\b", rest, flags=re.IGNORECASE):
        return f"{prefix}INSERT INTO {rest}"
    return f"{prefix}INSERT INTO {rest} ON CONFLICT DO NOTHING"


def _translate_insert_or_replace(sql):
    match = re.match(r"(\s*)INSERT\s+OR\s+REPLACE\s+INTO\s+(.+)", sql, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return sql
    prefix, rest = match.groups()
    if re.search(r"\bON\s+CONFLICT\b", rest, flags=re.IGNORECASE):
        return f"{prefix}INSERT INTO {rest}"
    return f"{prefix}INSERT INTO {rest} ON CONFLICT DO NOTHING"


def translate_postgres_sql(sql):
    text = sql.strip()
    if not text:
        return text
    text = text.replace("`", '"')
    text = re.sub(r"\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b", "SERIAL PRIMARY KEY", text, flags=re.IGNORECASE)
    text = re.sub(r"\bAUTOINCREMENT\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bDATETIME\b", "TIMESTAMP", text, flags=re.IGNORECASE)
    text = re.sub(r"\bTEXT\s+DEFAULT\s+CURRENT_TIMESTAMP\b", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP", text, flags=re.IGNORECASE)
    text = text.replace("DROP TABLE IF EXISTS temp.", "DROP TABLE IF EXISTS ")
    text = re.sub(r"(\b[\w.]+\b)\s+GLOB\s+'\[0-9\]\*([^']+)'", r"\1 ~ '^[0-9].*\2$'", text, flags=re.IGNORECASE)
    text = re.sub(r"(\b[\w.]+\b)\s+GLOB\s+'\*\[0-9\]\*([^']+)\*'", r"\1 ~ '[0-9].*\2'", text, flags=re.IGNORECASE)
    text = _translate_insert_or_ignore(text)
    text = _translate_insert_or_replace(text)
    return _escape_percent_in_string_literals(_replace_qmarks(text))


def _looks_like_sqlite_virtual_table(sql):
    return re.match(r"\s*CREATE\s+VIRTUAL\s+TABLE\b", sql, flags=re.IGNORECASE) is not None


def _extract_pragma_name(sql, pragma):
    match = re.search(rf"PRAGMA\s+{pragma}\((\"?[A-Za-z0-9_]+\"?)\)", sql, flags=re.IGNORECASE)
    if not match:
        return ""
    return match.group(1).strip('"')


def _quote_identifier(name):
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name or ""):
        raise ValueError("invalid identifier")
    return f'"{name}"'


class PostgresConnection:
    def __init__(self):
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("PostgreSQL 已启用，但缺少 psycopg。请运行 pip install -r requirements.txt") from exc
        self._conn = psycopg.connect(DATABASE_URL)

    def execute(self, sql, params=None):
        handled = self._handle_sqlite_meta(sql, params)
        if handled is not None:
            return handled
        translated = translate_postgres_sql(sql)
        if _looks_like_sqlite_virtual_table(translated):
            return CompatCursor([])
        with self._conn.cursor() as cursor:
            cursor.execute(translated, params or ())
            return self._cursor_to_compat(cursor)

    def executemany(self, sql, seq_of_params):
        translated = translate_postgres_sql(sql)
        if _looks_like_sqlite_virtual_table(translated):
            return CompatCursor([])
        with self._conn.cursor() as cursor:
            cursor.executemany(translated, seq_of_params)
            return CompatCursor(rowcount=cursor.rowcount)

    def executescript(self, script):
        for statement in _split_script(script):
            if _looks_like_sqlite_virtual_table(statement):
                continue
            self.execute(statement)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        with suppress(Exception):
            self._conn.rollback()

    def close(self):
        self._conn.close()

    def _cursor_to_compat(self, cursor):
        if cursor.description is None:
            return CompatCursor(rowcount=cursor.rowcount)
        keys = [column.name for column in cursor.description]
        rows = [CompatRow(keys, row) for row in cursor.fetchall()]
        return CompatCursor(rows, cursor.rowcount)

    def _handle_sqlite_meta(self, sql, params=None):
        normalized = " ".join(sql.strip().split())
        if normalized.upper().startswith("PRAGMA BUSY_TIMEOUT"):
            return CompatCursor([])
        if normalized.upper().startswith("PRAGMA JOURNAL_MODE"):
            return CompatCursor([CompatRow(["journal_mode"], ["postgresql"])])
        if normalized.upper().startswith("PRAGMA QUICK_CHECK"):
            return CompatCursor([CompatRow(["quick_check"], ["ok"])])
        table_name = _extract_pragma_name(sql, "table_info")
        if table_name:
            return self._table_info(table_name)
        table_name = _extract_pragma_name(sql, "index_list")
        if table_name:
            return self._index_list(table_name)
        table_name = _extract_pragma_name(sql, "foreign_key_list")
        if table_name:
            return CompatCursor([])
        if "sqlite_master" in normalized and "type='table'" in normalized:
            return self._sqlite_master_tables(normalized)
        if "sqlite_master" in normalized and "type='index'" in normalized:
            return self._sqlite_master_indexes()
        if normalized.lower() == "select last_insert_rowid() as id":
            return self.execute("SELECT LASTVAL() AS id")
        return None

    def _sqlite_master_tables(self, normalized):
        if "AND name=" in normalized:
            match = re.search(r"name='([^']+)'", normalized)
            name = match.group(1) if match else ""
            rows = self.execute(
                """
                SELECT table_name AS name
                FROM information_schema.tables
                WHERE table_schema='public' AND table_type='BASE TABLE' AND table_name=%s
                ORDER BY table_name
                """,
                (name,),
            ).fetchall()
            return CompatCursor(rows)
        return self.execute(
            """
            SELECT table_name AS name
            FROM information_schema.tables
            WHERE table_schema='public' AND table_type='BASE TABLE'
            ORDER BY table_name
            """
        )

    def _sqlite_master_indexes(self):
        return self.execute(
            """
            SELECT indexname AS name, tablename AS tbl_name
            FROM pg_indexes
            WHERE schemaname='public'
            ORDER BY indexname
            """
        )

    def _table_info(self, table_name):
        rows = self.execute(
            """
            SELECT
              ordinal_position - 1 AS cid,
              column_name AS name,
              data_type AS type,
              CASE WHEN is_nullable='NO' THEN 1 ELSE 0 END AS "notnull",
              column_default AS dflt_value,
              CASE WHEN column_name IN (
                SELECT a.attname
                FROM pg_index i
                JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                WHERE i.indrelid = %s::regclass AND i.indisprimary
              ) THEN 1 ELSE 0 END AS pk
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name=%s
            ORDER BY ordinal_position
            """,
            (table_name, table_name),
        ).fetchall()
        return CompatCursor(rows)

    def _index_list(self, table_name):
        rows = self.execute(
            """
            SELECT row_number() OVER (ORDER BY indexname) - 1 AS seq,
                   indexname AS name,
                   0 AS "unique",
                   'c' AS origin,
                   0 AS partial
            FROM pg_indexes
            WHERE schemaname='public' AND tablename=%s
            ORDER BY indexname
            """,
            (table_name,),
        ).fetchall()
        return CompatCursor(rows)
