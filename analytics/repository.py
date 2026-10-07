"""Analytics domain: the SQL layer for the events table.

This domain reads and writes ONLY the events table — never the Passes tables. That isolation is
what lets it become a separate service later (see ADR-2).
"""


def insert_event(conn, venue_id, event_type, amount_cents, occurred_at):
    cur = conn.execute(
        """INSERT INTO events (venue_id, event_type, amount_cents, occurred_at)
           VALUES (?, ?, ?, ?)""",
        (venue_id, event_type, amount_cents, occurred_at),
    )
    return cur.lastrowid
