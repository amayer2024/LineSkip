# Migration evidence (Azure)

Demonstrates a versioned migration shipped through the CI/CD pipeline and preserving
data already in the database. Migration `003_add_purchase_source.sql` adds a
`source NVARCHAR(20) NOT NULL DEFAULT 'web'` column to `dbo.purchases`; existing rows
backfill to `web` via the default.

Queried directly against the live Azure SQL database `amayer-ieu2024-passes-db`.

## Before — migration 003 not yet deployed

Live app was at migrations 001 and 002; two purchases existed (id 1 bought via the UI,
id 2 via the API demo user `migdemo@lineskip.es`).

```
filename                    applied_at
--------------------------  --------------------------------
001_init.sql                2026-11-19T16:11:45.344271+00:00
002_add_venue_country.sql   2026-11-19T16:11:45.358222+00:00

purchases
---------
        2

id   user_id   venue_id   price_cents_paid   status
---  --------  ---------  -----------------  ------
  2         2          1               1500  active
  1         1          2               2000  active

source_col_exists
-----------------
             NULL          <- the column does not exist yet
```

## Deploy

Commit `71b8a37` added `services/passes/migrations/003_add_purchase_source.sql`; merged to
`main` (PR #9). The CD pipeline built the SHA-tagged image, rolled it out to the passes
Container App, and the service ran the migration on startup.

## After — migration 003 deployed by the pipeline

```
filename                       applied_at
-----------------------------  --------------------------------
001_init.sql                   2026-11-19T16:11:45.344271+00:00
002_add_venue_country.sql      2026-11-19T16:11:45.358222+00:00
003_add_purchase_source.sql    2026-11-20T14:38:00.084647+00:00   <- applied once, by the pipeline

id   user_id   venue_id   price_cents_paid   status   source
---  --------  ---------  -----------------  ------   ------
  1         1          2               2000  active   web      <- same rows, preserved
  2         2          1               1500  active   web      <- backfilled by the default

source_col_exists
-----------------
               40          <- COL_LENGTH of NVARCHAR(20); the column now exists
```

## What this shows

- The migration is **versioned and recorded**: `schema_migrations` gained exactly one row
  (`003_...`) with its apply timestamp; a second startup applies nothing (idempotent,
  forward-only — ADR-7).
- **Existing data is preserved**: the two purchases present before the migration are still
  present after, unchanged, and the new `source` column backfilled to `web` on those rows.
- It was applied **by the pipeline**, not by hand: merging to `main` built and deployed the
  image, and the passes service ran the migration on container startup.
