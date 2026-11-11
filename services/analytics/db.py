"""SQLite connection helper and startup schema init for the analytics service."""
import os
import sqlite3

import config


def get_connection():
    path = config.get_db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn=None):
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        script = f.read()
    owns = conn is None
    conn = conn or get_connection()
    conn.executescript(script)
    conn.commit()
    if owns:
        conn.close()
