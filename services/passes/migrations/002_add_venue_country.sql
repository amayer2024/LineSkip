-- 002: add a country column to venues (data-preserving, A2 §4).
-- A NOT NULL column with a DEFAULT backfills every existing row with 'Spain' at ALTER
-- time and covers future inserts, so running this against a populated venues table loses
-- no data. It runs exactly once (recorded in schema_migrations); a second boot skips it.
IF COL_LENGTH('dbo.venues', 'country') IS NULL
    ALTER TABLE dbo.venues
        ADD country NVARCHAR(100) NOT NULL CONSTRAINT DF_venues_country DEFAULT 'Spain';
GO
