-- Additive, data-preserving migration: record the sales channel each purchase
-- came through. Existing rows backfill to 'web' via the column default, which is
-- the evidence that the migration preserves data already in the table.
IF COL_LENGTH('dbo.purchases', 'source') IS NULL
    ALTER TABLE dbo.purchases
        ADD source NVARCHAR(20) NOT NULL
        CONSTRAINT DF_purchases_source DEFAULT 'web';
GO
