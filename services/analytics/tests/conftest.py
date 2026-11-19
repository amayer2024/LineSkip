"""Test fixtures. DB-backed tests need a reachable SQL Server via DATABASE_URL
(provided by a service container in CI); they skip otherwise.

The CI database is shared across tests, so each test starts from empty data:
_reset() clears the events table while leaving schema_migrations intact.
"""
import os

import pytest

import db


def _reset(connection):
    connection.execute("DELETE FROM events")
    connection.commit()


@pytest.fixture
def conn():
    if not os.environ.get("DATABASE_URL") or not db.can_reach_db():
        pytest.skip("No reachable SQL Server (set DATABASE_URL)")
    connection = db.get_connection()
    db.run_migrations(connection)
    _reset(connection)
    yield connection
    connection.close()
