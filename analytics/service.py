"""Analytics domain: recording sales events and (Day 4) reporting on them.

Pure logic — no Flask. `record_event` is the single seam between the Passes domain and this one:
Passes calls it on each purchase. When the domains are split into separate services later, this
call becomes a network/queue message and nothing else about Passes has to change (see ADR-2).
"""
from datetime import datetime, timezone

from analytics import repository


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def record_event(conn, venue_id, event_type, amount_cents):
    """Record one sales event into the Analytics-owned events table.

    This is the only entry point the Passes domain uses to reach Analytics.
    """
    return repository.insert_event(conn, venue_id, event_type, amount_cents, _now_iso())
