-- Analytics service schema (SQL Server). This service owns only the events table (ADR-2).
-- No foreign key into the passes tables: analytics keeps its own copy of what it needs.
IF OBJECT_ID('dbo.events') IS NULL
CREATE TABLE dbo.events (
    id           INT IDENTITY(1,1) PRIMARY KEY,
    venue_id     INT NOT NULL,
    event_type   NVARCHAR(40) NOT NULL,
    amount_cents INT NOT NULL DEFAULT 0,
    occurred_at  NVARCHAR(40) NOT NULL
);
GO
