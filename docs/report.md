# LineSkip — Assignment 2 Report

**Student:** Amit Jason Mayer Bar-On (`amayer.ieu2024`)
**Repository:** https://github.com/amayer2024/LineSkip
**Live UI:** https://amayerieu2024ui.z28.web.core.windows.net/

LineSkip is a Madrid line-skip / cover-pass app for nightlife venues. Assignment 1 built it as a
single-process Flask + SQLite monolith. Assignment 2 splits it into two independently deployed
services, each owning its own SQL Server database, running locally with Docker Compose and in the
cloud on Azure — with a static browser UI, versioned migrations, and a CI/CD pipeline that tests,
builds and deploys on every merge to `main`. Every design decision is recorded in `ADR.md`
(entries 1–10); this report summarises the system and shows the evidence.

---

## 1. Architecture

```
                         browser
                            |
              https://amayerieu2024ui.z28.web.core.windows.net
                            |  (static UI on Azure Storage $web)
             +--------------+---------------+
             |                              |
             v                              v
     passes service                 analytics service        <- Azure Container Apps
   (auth, venues, passes)      (events, revenue reports)         (serverless, min 0 / max 1)
             |                              ^
             |   POST /events (the seam)    |
             +------------------------------+
             |                              |
             v                              v
      passes database               analytics database        <- Azure SQL, one serverless
   users, sessions, venues,              events                   database per service
   pass_products, purchases
```

Two Flask services, each with its own database and its own SQL login, coupled along a single seam:
on each purchase or refund the **passes** service makes one HTTP `POST /events` to **analytics**.
The static UI runs entirely in the browser and talks to both services directly. Nothing shares a
database; neither service can read the other's data.

The whole system is described formally in `system.yaml` (validated in CI against the provided
`system.schema.json`), and each service's HTTP contract in `services/<svc>/openapi.yaml`.

---

## 2. The service split and the seam (ADR-2, ADR-6)

The split follows a seam identified back in Assignment 1 (ADR-2): analytics owns an `events` table
and reports only from it, and passes reaches analytics through exactly one call. In A1 that call was
an in-process function; in A2 it became an HTTP request, which is the only change the split required.

- **Location by configuration, never hardcoded.** Passes finds analytics through the `ANALYTICS_URL`
  environment variable (the compose service name locally, the Container App URL on Azure).
- **Graceful degradation.** `analytics_client.record_event` posts `{venue_id, event_type,
  amount_cents}` with a timeout (`ANALYTICS_TIMEOUT_S`), wrapped in try/except. If analytics is down
  the purchase still succeeds, the event is dropped and logged (`[seam] analytics unavailable`), and
  passes `/health` stays 200. Verified locally by stopping the analytics container mid-purchase.
- **No shared integrity.** There is no foreign key across the seam; analytics records whatever
  `venue_id` passes sends. This is the deliberate cost of independence (ADR-7, ADR-10).

---

## 3. Database per service and versioned migrations (ADR-7)

Each service owns its tables in its own SQL Server database, reached by its own login
(`passes_user`, `analytics_user`) scoped to only that database — so no service can read the other's
data. The schema is defined by numbered files (`migrations/NNN_*.sql`) applied in order on startup
and recorded in a `schema_migrations` table, so each migration runs exactly once and is forward-only.
SQL was ported from SQLite to T-SQL (`IDENTITY`, `NVARCHAR`, `OFFSET/FETCH`, `SUBSTRING`).

### Migration evidence (live Azure database)

Migration `003_add_purchase_source.sql` adds a `source NVARCHAR(20) NOT NULL DEFAULT 'web'` column to
`purchases`. It was shipped through the pipeline (merge to `main` → deploy → applied on container
startup) and queried directly against the live Azure database before and after:

| | Before | After (003 deployed by the pipeline) |
|---|---|---|
| `schema_migrations` | 001, 002 | 001, 002, **003** (applied 2026-11-20 14:38) |
| purchases | 2 rows | **same 2 rows**, unchanged |
| `source` column | absent (`NULL`) | present, **backfilled to `web`** |

The two purchases that existed before the migration survived it and were backfilled by the column
default; `schema_migrations` gained exactly one row. Full query output is in
`docs/migration-evidence.md`. This is the required proof that a versioned migration preserves data
already in the database.

---

## 4. CI/CD pipeline (ADR-9)

Two GitHub Actions workflows, split so deployment only ever happens from `main`.

**CI (`ci.yml`)** runs on every branch and pull request (and is called by CD on `main`):

1. **lint** — `ruff --select E9,F` (syntax errors, undefined names, unused imports).
2. **specs** — validates both OpenAPI documents and `system.yaml` against `system.schema.json`.
3. **test** — each service runs against a **real SQL Server service container** (a wait script
   creates the per-service database) with a **≥70% coverage gate** on the business-logic modules.
   Current result: passes 99% line coverage, analytics 100%.
4. **images** — builds each service image and pushes `ghcr.io/amayer2024/lineskip-<svc>:<sha>` to
   GHCR, tagged by commit SHA, on `main` only (`provenance: false` so Azure can pull it).

**CD (`cd.yml`)** runs on push to `main`: it calls CI, then a deploy job that

- signs in to Azure by **OIDC federation** — a user-assigned managed identity with a federated
  credential, so **no cloud secret is stored** in the repo;
- rolls out the `:<sha>` image to each Container App and injects each `DATABASE_URL` from a GitHub
  secret (the DB password never touches the repo or a local shell);
- writes `ui/config.js` with the live service URLs and uploads `ui/` to the Storage `$web` container;
- **health-checks** both services (`/health` must return 200), retrying through the serverless cold
  start before declaring success.

Every merge to `main` is therefore a reproducible, commit-traceable deploy. Two real failures were
hit and fixed during bring-up, both documented: GitHub presents the OIDC subject in a numeric-ID
form that had to be registered alongside the repo-name form; and setting a Container Apps secret and
immediately referencing it is a race (`ContainerAppSecretRefNotFound`), fixed by retrying the image
update in `scripts/cd/deploy_service.sh`.

---

## 5. Azure deployment (ADR-8)

Everything runs in one resource group (`rg-amayer-ieu2024`, region France Central) within the Azure
for Students free credit, named from the prefix `amayer-ieu2024`:

- **UI** — Storage static website (`amayerieu2024ui`, the `$web` container).
- **Services** — two Azure Container Apps (Consumption plan, **min 0 / max 1 replica**) in the
  `amayer-ieu2024-env` environment; external ingress on port 8000; CORS enforced in the service code
  (Flask-CORS reading `CORS_ORIGINS`), never on the ingress.
- **Data** — one SQL logical server (`amayer-ieu2024-sql`) with two **serverless** General Purpose
  databases on the free offer (auto-pause after 60 min), one per service, each with its own contained
  login.
- **Pipeline identity** — a user-assigned managed identity (`amayer-ieu2024-github`) with Contributor
  on the resource group only, trusted from GitHub by a federated credential.

Because the apps scale to zero and the databases auto-pause, an idle system costs essentially
nothing. The trade-off is cold starts: the first request after idle wakes the container and resumes
the database (~1 min), during which Azure may answer 503 "App port is not ready"; `db.py` connects
with retry/backoff to absorb it. The one-time setup commands are documented in the README (steps 2–7,
passwords redacted).

**Live endpoints**

- UI: https://amayerieu2024ui.z28.web.core.windows.net/
- passes: https://amayer-ieu2024-passes.wittypebble-17e2d05a.francecentral.azurecontainerapps.io/health
- analytics: https://amayer-ieu2024-analytics.wittypebble-17e2d05a.francecentral.azurecontainerapps.io/health

---

## 6. Testing and coverage (ADR-4)

Coverage is measured on the modules that hold the logic — `service`, `repository`, and `auth` — not
the thin Flask routes, so the figure reflects real behaviour rather than routing glue. Each test
drives one branch of the domain logic (sold-out guard, double-redeem rejection, refund ownership,
empty-report, seed idempotency, expired-token purge). In CI these run against a real SQL Server, so
the SQL is exercised exactly as it runs in production. Current result: 28 passes-service tests at 99% line coverage
(including a concurrency test that proves the oversell guard is atomic under simultaneous
purchases), analytics at 100%, gated at ≥70%.

---

## 7. What was deliberately not built (ADR-5, ADR-10)

- **No real payment processing** (ADR-5): `purchase()` records the sale as integer-cents bookkeeping
  and issues a redemption code, but charges no card — a gateway would add external secrets and PCI
  scope irrelevant to the modularization goal.
- **No authentication on the seam** (ADR-10): analytics must stay publicly reachable because the
  browser dashboard reads its endpoints directly, so `POST /events` shares that public ingress with no
  caller auth. The blast radius is contained — analytics owns only its `events` table and cannot reach
  passes data or auth — and the fix (a public read API plus an internal authenticated ingest) is
  isolated to one service and the one seam client.

---

## 8. Where to look

| Artefact | Location |
|---|---|
| Architecture decisions | `ADR.md` (1–10) |
| System description | `system.yaml` (+ `system.schema.json`) |
| Service API contracts | `services/passes/openapi.yaml`, `services/analytics/openapi.yaml` |
| CI / CD | `.github/workflows/ci.yml`, `.github/workflows/cd.yml` |
| Migration evidence | `docs/migration-evidence.md` |
| AI usage | `AI_USAGE.md` |
| Setup + run instructions | `README.md` |
