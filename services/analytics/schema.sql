-- Analytics service schema. This service owns only the events table (ADR-2).
CREATE TABLE IF NOT EXISTS events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    venue_id     INTEGER NOT NULL,
    event_type   TEXT NOT NULL,
    amount_cents INTEGER NOT NULL DEFAULT 0,
    occurred_at  TEXT NOT NULL
);
