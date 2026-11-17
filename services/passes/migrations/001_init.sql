-- Passes service schema (SQL Server). Applied once by the migration runner.
-- Ported from the Assignment 1 SQLite schema: AUTOINCREMENT -> IDENTITY, TEXT -> NVARCHAR.
-- The events table is gone: it belongs to the analytics service now (ADR-2 / ADR-6).
IF OBJECT_ID('dbo.users') IS NULL
CREATE TABLE dbo.users (
    id            INT IDENTITY(1,1) PRIMARY KEY,
    email         NVARCHAR(255) NOT NULL UNIQUE,
    password_hash NVARCHAR(255) NOT NULL,
    created_at    NVARCHAR(40)  NOT NULL
);
GO
IF OBJECT_ID('dbo.sessions') IS NULL
CREATE TABLE dbo.sessions (
    token      NVARCHAR(64) PRIMARY KEY,
    user_id    INT NOT NULL REFERENCES dbo.users(id),
    created_at NVARCHAR(40) NOT NULL,
    expires_at NVARCHAR(40) NOT NULL
);
GO
IF OBJECT_ID('dbo.venues') IS NULL
CREATE TABLE dbo.venues (
    id         INT IDENTITY(1,1) PRIMARY KEY,
    name       NVARCHAR(200) NOT NULL,
    city       NVARCHAR(100) NOT NULL,
    address    NVARCHAR(300) NOT NULL,
    created_at NVARCHAR(40)  NOT NULL
);
GO
IF OBJECT_ID('dbo.pass_products') IS NULL
CREATE TABLE dbo.pass_products (
    id             INT IDENTITY(1,1) PRIMARY KEY,
    venue_id       INT NOT NULL REFERENCES dbo.venues(id),
    type           NVARCHAR(20) NOT NULL CHECK (type IN ('line_skip', 'cover')),
    name           NVARCHAR(200) NOT NULL,
    price_cents    INT NOT NULL,
    quantity_total INT NOT NULL,
    quantity_sold  INT NOT NULL DEFAULT 0,
    valid_date     NVARCHAR(40) NOT NULL,
    created_at     NVARCHAR(40) NOT NULL
);
GO
IF OBJECT_ID('dbo.purchases') IS NULL
CREATE TABLE dbo.purchases (
    id               INT IDENTITY(1,1) PRIMARY KEY,
    user_id          INT NOT NULL REFERENCES dbo.users(id),
    pass_product_id  INT NOT NULL REFERENCES dbo.pass_products(id),
    venue_id         INT NOT NULL REFERENCES dbo.venues(id),
    price_cents_paid INT NOT NULL,
    status           NVARCHAR(20) NOT NULL CHECK (status IN ('active', 'redeemed', 'refunded')),
    redemption_code  NVARCHAR(32) NOT NULL UNIQUE,
    purchased_at     NVARCHAR(40) NOT NULL,
    redeemed_at      NVARCHAR(40) NULL
);
GO
