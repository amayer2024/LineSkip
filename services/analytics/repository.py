"""Analytics domain: the SQL layer for the events table (SQL Server).

Reads and writes ONLY the events table — never the passes tables. That isolation is
what lets it be its own service (ADR-2). Ported from SQLite: substr -> SUBSTRING,
LIMIT -> OFFSET/FETCH, and GROUP BY on the expression (SQL Server can't group by an alias).
"""


def insert_event(conn, venue_id, event_type, amount_cents, occurred_at):
    cur = conn.execute(
        """INSERT INTO events (venue_id, event_type, amount_cents, occurred_at)
           VALUES (?, ?, ?, ?)""",
        (venue_id, event_type, amount_cents, occurred_at),
    )
    return cur.lastrowid


# --- reporting reads (all over purchase events only) ----------------------

def sum_revenue(conn):
    """Total revenue across all purchase events. COALESCE turns the NULL sum of
    zero rows into 0 so the empty-data case returns a real number."""
    return conn.execute(
        "SELECT COALESCE(SUM(amount_cents), 0) AS total FROM events WHERE event_type = 'purchase'"
    ).fetchone()["total"]


def revenue_by_venue(conn):
    """One row per venue: (venue_id, total) summed over that venue's purchases."""
    return conn.execute(
        """SELECT venue_id, SUM(amount_cents) AS total
               FROM events
              WHERE event_type = 'purchase'
           GROUP BY venue_id
           ORDER BY venue_id"""
    ).fetchall()


def top_venues_by_revenue(conn, n):
    """Same per-venue grouping, highest revenue first, capped at n rows."""
    return conn.execute(
        """SELECT venue_id, SUM(amount_cents) AS total
               FROM events
              WHERE event_type = 'purchase'
           GROUP BY venue_id
           ORDER BY total DESC, venue_id
          OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY""",
        (n,),
    ).fetchall()


def revenue_by_day(conn):
    """Daily series: group on the YYYY-MM-DD slice of the ISO occurred_at string."""
    return conn.execute(
        """SELECT SUBSTRING(occurred_at, 1, 10) AS day, SUM(amount_cents) AS total
               FROM events
              WHERE event_type = 'purchase'
           GROUP BY SUBSTRING(occurred_at, 1, 10)
           ORDER BY day"""
    ).fetchall()
