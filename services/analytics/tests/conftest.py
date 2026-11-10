"""Fresh, schema-initialized SQLite per test, isolated via DATA_DIR."""
import pytest

import db


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    connection = db.get_connection()
    db.init_db(connection)
    yield connection
    connection.close()
