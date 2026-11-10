"""Core analytics logic for the standalone service."""
import service as analytics


def test_record_event_writes_a_row(conn):
    analytics.record_event(conn, venue_id=7, event_type="purchase", amount_cents=1500)
    row = conn.execute("SELECT * FROM events").fetchone()
    assert row["venue_id"] == 7
    assert row["event_type"] == "purchase"
    assert row["amount_cents"] == 1500


def test_reports_are_empty_with_no_events(conn):
    assert analytics.total_revenue(conn) == 0
    assert analytics.revenue_per_venue(conn) == []
    assert analytics.top_venues(conn) == []
    assert analytics.revenue_per_day(conn) == []


def test_total_revenue_sums_purchases(conn):
    analytics.record_event(conn, 1, "purchase", 1500)
    analytics.record_event(conn, 2, "purchase", 5000)
    assert analytics.total_revenue(conn) == 6500
