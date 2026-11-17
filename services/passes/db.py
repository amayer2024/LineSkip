"""SQL Server connection, migration runner, and startup bootstrap.

Config comes entirely from DATABASE_URL (mssql://user:password@host:1433/dbname).

A thin Connection wrapper keeps the domain code almost identical to Assignment 1:
it still calls conn.execute("... ? ...", params).fetchone(), and the wrapper translates
'?' placeholders to pymssql's '%s' and exposes .lastrowid via SCOPE_IDENTITY().

Connections retry with backoff because a serverless Azure SQL database may be paused and
take ~1 minute to resume (error 40613 / connection timeout) — the same code path runs locally.
"""
import glob
import os
import time
from datetime import datetime, timezone
from urllib.parse import unquote, urlparse

import pymssql


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


class _Result:
    def __init__(self, cur):
        self._cur = cur

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    @property
    def rowcount(self):
        return self._cur.rowcount

    @property
    def lastrowid(self):
        # Identity of the row just inserted on this connection's scope.
        self._cur.execute("SELECT CAST(SCOPE_IDENTITY() AS INT) AS id")
        row = self._cur.fetchone()
        return row["id"] if row else None


class Connection:
    """Adapts a pymssql connection to the sqlite-style API the domain code expects."""

    def __init__(self, raw):
        self._raw = raw
        self._cur = raw.cursor()

    def execute(self, sql, params=()):
        self._cur.execute(sql.replace("?", "%s"), tuple(params))
        return _Result(self._cur)

    def commit(self):
        self._raw.commit()

    def rollback(self):
        self._raw.rollback()

    def close(self):
        self._raw.close()


def _cfg():
    u = urlparse(os.environ["DATABASE_URL"])
    return {
        "server": u.hostname,
        "port": str(u.port or 1433),
        "user": unquote(u.username or ""),
        "password": unquote(u.password or ""),
        "database": (u.path or "/").lstrip("/"),
    }


def get_connection(retries=12, backoff=5):
    """Open a wrapped connection, retrying while a paused database resumes."""
    c = _cfg()
    last = None
    for _ in range(retries):
        try:
            raw = pymssql.connect(
                server=c["server"], port=c["port"], user=c["user"],
                password=c["password"], database=c["database"],
                as_dict=True, login_timeout=15, timeout=30,
            )
            return Connection(raw)
        except pymssql.Error as exc:
            last = exc
            time.sleep(backoff)
    raise last


def can_reach_db():
    """True if a trivial query succeeds — used by GET /health."""
    try:
        conn = get_connection(retries=1, backoff=0)
        try:
            conn.execute("SELECT 1 AS ok").fetchone()
            return True
        finally:
            conn.close()
    except Exception:
        return False


def _split_batches(sql):
    """Split a .sql file on lines that are exactly GO (the SQL Server batch separator)."""
    batches, cur = [], []
    for line in sql.splitlines():
        if line.strip().upper() == "GO":
            if cur:
                batches.append("\n".join(cur))
                cur = []
        else:
            cur.append(line)
    if cur:
        batches.append("\n".join(cur))
    return [b for b in batches if b.strip()]


def run_migrations(conn):
    """Apply every migrations/*.sql not yet recorded, in filename order, each exactly once."""
    conn.execute(
        "IF OBJECT_ID('dbo.schema_migrations') IS NULL "
        "CREATE TABLE dbo.schema_migrations "
        "(filename NVARCHAR(255) PRIMARY KEY, applied_at NVARCHAR(40) NOT NULL)"
    )
    conn.commit()
    applied = {r["filename"] for r in conn.execute("SELECT filename FROM dbo.schema_migrations").fetchall()}
    mig_dir = os.path.join(os.path.dirname(__file__), "migrations")
    for path in sorted(glob.glob(os.path.join(mig_dir, "*.sql"))):
        name = os.path.basename(path)
        if name in applied:
            continue
        with open(path, "r", encoding="utf-8") as f:
            script = f.read()
        for batch in _split_batches(script):
            conn.execute(batch)
        conn.execute(
            "INSERT INTO dbo.schema_migrations (filename, applied_at) VALUES (?, ?)",
            (name, _now_iso()),
        )
        conn.commit()
        print(f"[migration] applied {name}", flush=True)


def init_db():
    """Startup bootstrap: run migrations in order."""
    conn = get_connection()
    try:
        run_migrations(conn)
    finally:
        conn.close()
