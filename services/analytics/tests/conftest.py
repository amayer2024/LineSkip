"""Test fixtures. DB-backed tests need a reachable SQL Server via DATABASE_URL;
they skip otherwise (CI gains a SQL Server service container in a later step)."""
import os

import pytest

import db


@pytest.fixture
def conn():
    if not os.environ.get("DATABASE_URL") or not db.can_reach_db():
        pytest.skip("No reachable SQL Server (set DATABASE_URL)")
    connection = db.get_connection()
    db.run_migrations(connection)
    yield connection
    connection.close()
