"""Tests for the Analytics domain. Day 3: recording events (reporting arrives Day 4)."""
from analytics import service as analytics


def test_record_event_writes_a_row(conn):
    analytics.record_event(conn, venue_id=7, event_type="purchase", amount_cents=1500)

    row = conn.execute("SELECT * FROM events").fetchone()
    assert row["venue_id"] == 7
    assert row["event_type"] == "purchase"
    assert row["amount_cents"] == 1500
    assert row["occurred_at"]  # timestamp was stamped


def test_record_event_returns_event_id(conn):
    first = analytics.record_event(conn, 1, "purchase", 1000)
    second = analytics.record_event(conn, 1, "purchase", 2000)
    assert second != first
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 2
