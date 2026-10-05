"""Tests for the auth domain's core logic (register / login / verify_session)."""
from auth import service as auth


def test_register_returns_user_id_and_persists(conn):
    user_id = auth.register(conn, "Dancer@madrid.es", "supersecret")
    assert isinstance(user_id, int)
    row = conn.execute("SELECT email, password_hash FROM users WHERE id = ?", (user_id,)).fetchone()
    assert row["email"] == "dancer@madrid.es"  # normalized to lowercase
    assert row["password_hash"] != "supersecret"  # stored hashed, never plaintext


def test_login_with_correct_password_issues_token(conn):
    auth.register(conn, "user@madrid.es", "supersecret")
    token = auth.login(conn, "user@madrid.es", "supersecret")
    assert token
    assert auth.verify_session(conn, token) is not None


def test_verify_session_rejects_unknown_token(conn):
    assert auth.verify_session(conn, "not-a-real-token") is None
    assert auth.verify_session(conn, None) is None
