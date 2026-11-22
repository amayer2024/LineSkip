# Architecture Decision Records

## 1. Backend language and framework
Date: 2026-10-05
Status: Decided
Context: The assignment is graded on explaining my own code cold at a closed-book oral check that
multiplies the whole grade, and it must run as a single process with SQLite storage.
Decision: Python + Flask with the stdlib `sqlite3` module (no ORM) and `werkzeug.security` for
password hashing, which ships with Flask.
Alternatives considered: FastAPI — rejected because its Pydantic models, `Depends()` dependency
injection, and `async` add framework machinery I would have to explain under exam conditions for no
benefit at this scale. Django — rejected as far too heavy for two small domains (poor-judgment
signal per §1b).
Consequences: Every request handler is plain traceable Python, which is ideal for the comprehension
check. The cost is writing request validation and SQL by hand instead of getting it for free.

## 2. Scoping the two feature domains to be independently modularizable
Date: 2026-10-06
Status: Decided
Context: The assignment requires two backend domains coupled as little as possible, each able to
become its own microservice later. Passes (selling/redeeming passes) and Analytics (revenue
reporting) clearly need to share sales data without becoming entangled.
Decision: Analytics owns its own `events` table and reports only from it; the Passes domain reaches
Analytics through a single function, `record_event()`, and nothing else — invoked at two lifecycle
points (`purchase()` records a `purchase` event and `refund()` records a `refund` event). There is
no foreign key between `events` and the Passes tables, and neither domain reads the other's tables.
Alternatives considered: Let Analytics query the `purchases` table directly with SQL joins —
rejected because it would bind Analytics to the Passes schema, so the two could never be split. A
message broker / event bus — rejected as out of scope (§1c forbids brokers; this is one process),
with the in-process `record_event()` call standing in for the future network boundary.
Consequences: To extract Analytics into its own service later, I turn the `record_event()` calls
into HTTP/queue messages and point its reports at the events it already owns — the seam is that one
function, the single integration surface between the domains, regardless of how many lifecycle
events call it. The cost now is a one-way in-process dependency (Passes imports Analytics only to
emit events).

## 3. SQLite data model for the Passes domain
Date: 2026-10-06
Status: Decided
Context: The Passes domain needs to sell limited-inventory passes and later feed revenue numbers to
the Analytics domain, so the schema has to handle money and stock correctly while keeping the two
domains loosely coupled.
Decision: Store all money as integer `*_cents` columns; model inventory as two columns on
`pass_products` (`quantity_total` fixed, `quantity_sold` incremented on purchase); give `purchases`
a text `status` enum (`active`/`redeemed`/`refunded`), a unique `redemption_code`, and a
denormalized `venue_id`. The Analytics `events` table (added later) will hold no foreign key into
these tables.
Alternatives considered: Storing prices as REAL/float — rejected because floating-point rounding
corrupts money math. A separate `inventory` table or per-pass rows — rejected as overkill for a
simple sold-vs-total count. A foreign key from `events` into `purchases` — rejected because it would
tie Analytics to the Passes schema and break the independent-domain goal (see ADR-2).
Consequences: Money math is exact and the oversell check is a trivial `quantity_sold >=
quantity_total` comparison. Denormalizing `venue_id` costs a little duplication but lets purchases
be reported on (and events recorded) without joining back through `pass_products`.

## 4. Testing approach and what coverage measures
Date: 2026-10-09
Status: Decided
Context: The grade is dominated by a closed-book oral check where I must explain my own code, and
the assignment asks for ≥70% test coverage on the core logic with a stated, reproducible figure.
The code is split into pure service modules (business rules), repository modules (SQL), and thin
Flask routes (HTTP glue).
Decision: Test the service and repository layers directly against a per-test temporary SQLite
database (the `conn` fixture in `tests/conftest.py`), and measure coverage on `auth`, `passes`, and
`analytics` only — not `app.py`. Each test drives one branch of the logic (e.g. sold-out, double
redeem, refund-of-another-user, empty-report, seed idempotency). The documented command is
`pytest --cov=auth --cov=passes --cov=analytics --cov-report=term-missing`.
Alternatives considered: HTTP-level tests through the Flask test client — rejected because they are
slower, mostly re-prove what the service tests already cover, and would pull framework glue into the
coverage number, making it less meaningful. No coverage gate at all — rejected because the
assignment wants a concrete, reproducible figure.
Consequences: The tests exercise exactly the code I have to explain at the oral check, and the
coverage number reflects real logic rather than routing boilerplate. Current result: 34 tests, 100%
line coverage on the measured modules. The cost is that the thin routes are verified by hand (live
`curl` / browser checks during development) rather than by automated HTTP tests.

## 5. Deliberately not building real payment processing
Date: 2026-10-11
Status: Decided
Context: Buying a pass is a paid transaction, so a product I could actually ship would eventually
charge a card; I had to decide whether to integrate a payment gateway now or defer it.
Decision: `purchase()` records the sale as a transaction (the price is copied into
`purchases.price_cents_paid` and a redemption code is issued) but does not charge real money; a
payment gateway is explicitly out of scope for this assignment.
Alternatives considered: Integrating a real gateway such as Stripe or PayPal — rejected because it
requires an external runtime dependency plus secret/API-key management, which is in tension with
§7.6 ("no required external runtime dependency beyond a public API your use case genuinely needs")
and the single-container contract, and it drags in PCI-compliance scope that teaches nothing about
the DevOps modularization goal of this assignment. A fake in-app "wallet" balance — rejected as
busywork that simulates payment without being real, adding a table and rules I would have to explain
for no learning value.
Consequences: The money path stays a clean integer-cents bookkeeping record that both domains
already rely on (Passes stores it, Analytics reports on it), and the purchase flow is fully testable
with no network calls or secrets. The cost is that "payment" is modelled, not executed; wiring in a
real gateway — and its secrets, through the same environment-variable config approach in
`config.py` — is deferred to when the app is actually deployed.

## 6. Splitting the monolith into two services along the ADR-2 seam
Date: 2026-11-17
Status: Decided
Context: Assignment 2 requires the monolith to become two independently deployed services, one per
feature domain, each with its own container and its own database, split along the seam named in
ADR-2.
Decision: Passes and Analytics are now separate Flask services. The in-process `record_event()`
call became an HTTP POST from Passes to Analytics' `POST /events`, located through the
`ANALYTICS_URL` environment variable (never a hardcoded host). Analytics owns the `events` table in
its own database; Passes no longer contains it. Recording a sale is the cross-seam flow and it runs
server-side, inside Passes' `purchase()`/`refund()`.
Alternatives considered: Put the cross-seam call in the UI (client-side), rejected because recording
a sale belongs with the write that causes it and at least one flow must cross the seam server-side.
Keep Analytics in-process, rejected because it violates the database-per-service rule.
Consequences: ADR-2 held exactly — the only coupling was that single `record_event` call, so the
split changed one line into an HTTP request. The cost is a network hop that must tolerate failure
(see the timeout and degrade-on-failure in ADR-6's seam client) and the loss of a foreign key across
the seam (ADR-7).

## 7. One SQL Server database per service, with versioned migrations
Date: 2026-11-17
Status: Decided
Context: Assignment 1 created the SQLite schema on first boot. Assignment 2 moves to SQL Server with
one database per service and requires versioned migrations that preserve existing data once a
database holds rows.
Decision: Each service owns its tables in its own SQL Server database (`passes`, `analytics`), each
reached by its own login (`passes_user`, `analytics_user`) that `db/init.sql` scopes to that one
database — so no service can read the other's data. The schema is defined by numbered files
(`migrations/001_init.sql`, ...) applied in filename order on startup and recorded in a
`schema_migrations` table, so each migration runs exactly once and a second boot applies nothing.
SQL was ported from SQLite to T-SQL (`AUTOINCREMENT`->`IDENTITY`, `TEXT`->`NVARCHAR`, `LIMIT`->
`OFFSET/FETCH`, `substr`->`SUBSTRING`). Forward-only.
Alternatives considered: Keep schema-on-boot (A1), rejected because it cannot evolve a table that
already holds data. Use an ORM / Alembic, rejected to keep the SQL raw and explainable, continuing
the no-ORM choice of ADR-1.
Consequences: Integrity lost at the seam — the old foreign key from `events` into the Passes tables
is gone; `events` keeps a plain `venue_id` and referential integrity across the seam is deliberately
not enforced (Analytics records whatever `venue_id` Passes sends). Recovery plan for a bad
migration: migrations are forward-only and never edited once applied, so a mistake is corrected by a
new migration; because each service runs at most one replica, startup migrations never race; if a
migration corrupts data on Azure, restore the database from Azure SQL's automated point-in-time
backup and deploy the corrective migration.

## 8. Deploying to Azure: serverless Container Apps, static website, serverless SQL
Date: 2026-11-19
Status: Decided
Context: Assignment 2 §7 requires the two services deployed to Azure within the Azure for Students
free credit, scaling to zero when idle, with the UI served as a static site and one database per
service. It must cost almost nothing while idle and never need a credit card.
Decision: Each service runs as an Azure Container App (Consumption plan, minimum 0 / maximum 1
replica) in a shared environment `amayer-ieu2024-env`; the static UI is an Azure Storage static
website (the `$web` container); the data lives in one Azure SQL logical server with two General
Purpose serverless databases on the free offer (`--use-free-limit true`, fixed 60-minute auto-pause,
32 GB). Every resource name derives from the prefix `amayer-ieu2024`, and everything is in one
region (France Central) picked from the subscription's allowed-regions policy and used for all
resources. Runtime config is environment variables: the connection string is a Container Apps
secret, and the allowed CORS origin is the static website URL read from `CORS_ORIGINS`.
Alternatives considered: App Service or AKS — rejected because App Service bills for an always-on
plan and AKS is far too heavy, both breaking §7's scale-to-zero intent and the free credit. A
container-run or managed Postgres — rejected because the app already speaks SQL Server (ADR-7) and
Azure SQL serverless on the free offer fits the credit with no new dialect. Copying a classmate's
region — rejected because the allowed-regions policy differs per subscription (France Central isn't
on every list).
Consequences: An idle system costs essentially nothing — the apps scale to zero and the databases
auto-pause after 60 minutes. The price is cold starts: the first request after idle wakes the
container and resumes the database (~1 minute), during which connections fail (error 40613, or a
pymssql connection timeout) and Azure may answer the first request with 503 "App port is not ready".
This is handled by the connect-with-retry/backoff in `db.py` (ADR-7) and tolerated by the UI. The
free offer also fixes the auto-pause delay and size, so those flags must not be passed, and it isn't
available in every region.

## 9. CI/CD pipeline: OIDC deploy, SHA-tagged images, and what CI gates
Date: 2026-11-19
Status: Decided
Context: Assignment 2 §5/§8 require CI that builds and pushes a SHA-tagged image per service, and a
CD pipeline that deploys from `main` — authenticating to Azure without storing a cloud credential in
the repository.
Decision: GitHub Actions, split in two. `ci.yml` runs on branches and pull requests and as a
reusable workflow (`workflow_call`): it lints (ruff), validates the specs (both OpenAPI documents
and `system.yaml` against the provided `system.schema.json`), runs each service's tests against a
real SQL Server service container behind a ≥70% coverage gate, then builds each image and pushes
`ghcr.io/<owner>/lineskip-<service>:<sha>` — pushing only on `main`, with `provenance: false` so
Azure can pull the image. `cd.yml` runs on push to `main`: it calls `ci.yml`, then a deploy job that
authenticates to Azure by OIDC federation (a user-assigned managed identity with a federated
credential — no stored secret), points each Container App at the SHA-tagged image, injects each
`DATABASE_URL` from a GitHub secret, writes `ui/config.js` with the live service URLs and uploads
`ui/` to `$web`, and fails the run unless `/health` returns 200 on both services after retries.
CI's push trigger excludes `main` so the pipeline never runs twice.
Alternatives considered: Store an Azure service-principal secret for `azure/login` — rejected because
IE accounts can't create service principals and OIDC federation needs no stored secret at all.
Deploy straight from CI — rejected because a separate CD workflow keeps deployment `main`-only and
scoped to the `id-token: write` permission. A `latest` image tag — rejected because a per-commit SHA
tag makes every running revision traceable to a commit and trivially rollback-able.
Consequences: Every merge to `main` is a reproducible, commit-traceable deploy, and the pipeline's
identity holds Contributor on the resource group only (least privilege for a student subscription).
The footguns, all met during setup: the OIDC subject must be registered in both the repository-name
and the numeric-ID form (GitHub presented the numeric form, and `azure/login` failed until it was
added); new GHCR packages are private, so the first deploy couldn't pull the images until they were
made public; and coverage is measured on the business-logic modules, not the Flask glue (continuing
ADR-4), so the 70% figure stays meaningful rather than inflated by routing boilerplate.

## 10. Deliberately leaving the service-to-service seam unauthenticated
Date: 2026-11-19
Status: Decided
Context: Once the domains are separate services, the Analytics service needs external ingress because
the browser dashboard reads its `GET /analytics/*` endpoints directly. Its `POST /events` — the
write that the Passes service makes across the seam on each purchase/refund — shares that same public
ingress. I had to decide whether to authenticate the seam.
Decision: For this assignment Analytics accepts `POST /events` with no caller authentication; the
seam is trusted by network reachability alone. There is no shared secret, token, or managed-identity
check on the cross-service call.
Alternatives considered: Put Analytics on internal-only ingress — rejected because the same service
also serves the public dashboard reads the browser needs, so it has to stay externally reachable. A
shared secret or bearer token on `POST /events` — deferred, not rejected on merit: it is the correct
next step, but it adds a secret to manage and explain for no new insight into the modularization
goal this assignment is graded on. mTLS or managed-identity auth between the two apps — out of scope
for the timeline and the free credit.
Consequences: Anyone who discovers the Analytics URL can POST a fabricated sales event and skew the
revenue reports; there is no integrity guarantee on what the seam carries (compounding the
deliberate loss of the cross-seam foreign key in ADR-7). The blast radius is contained: Analytics
owns only its `events` table and cannot reach the Passes data or auth, so the worst case is wrong
analytics, not compromised sales or accounts. The fix when this matters is isolated to one service
and the single seam client — split Analytics into a public read API and an internal ingest that
requires a shared secret, or restrict `POST /events` to the Container Apps environment's internal
network.

## 11. Enforcing pass validity at purchase (A1 feedback)
Date: 2026-11-22
Status: Decided
Context: Assignment 1 feedback noted that `valid_date` is stored on `pass_products` but never
enforced — the seeded passes dated 2026-10-10 could still be bought after that date. A stored-but-
ignored constraint is a latent bug and an easy comprehension-check target.
Decision: `purchase()` now rejects a product whose `valid_date` is before today
(`PassError("pass has expired")`), a single ISO-date string comparison. Seeding uses a date two
months out so freshly seeded data is buyable, and migration `004_bump_pass_valid_dates.sql` updates
any already-seeded past-dated rows to a future date so existing live data stays purchasable.
Alternatives considered: leave it informational and only record the choice in an ADR — rejected,
because the feedback is right that an unenforced constraint is a real gap. Enforce without migrating
existing rows — rejected, because it would make every already-seeded pass on the live Azure database
unbuyable, including the migration-demo data.
Consequences: expired passes can no longer be sold; the rule is trivial to explain and test (a new
test buys an expired pass and asserts rejection, and the test helpers now seed future dates). The
cost is that validity is a date-only check with no per-event timezone cutoff, which is enough here.

## 12. Reporting net revenue, not just gross (A1 feedback)
Date: 2026-11-22
Status: Decided
Context: Assignment 1 feedback noted the Analytics domain stays thin — refund events are recorded
through the seam but no report uses them, so every revenue figure includes refunded passes and there
is no net view.
Decision: add a net-revenue report that subtracts refund events from purchase events
(`SUM(CASE WHEN event_type='purchase' THEN amount_cents WHEN event_type='refund' THEN -amount_cents
END)`), exposed at `GET /analytics/revenue/net`. The existing total / by-venue / top / by-day reports
stay gross (purchases only) and are now explicitly the gross view.
Alternatives considered: change the existing `total_revenue` to be net — rejected, because it would
silently change the meaning of an endpoint and its tests; gross and net are both legitimate and a
caller may want either. Delete refund events — rejected, because they are exactly the data the net
view needs.
Consequences: the refund events the seam already records are finally used. Net revenue reads only the
`events` table, so Analytics stays independent of the Passes schema (ADR-2). A test records two
purchases and a refund and asserts gross 3500 vs net 1500.
