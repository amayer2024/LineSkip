# LineSkip

A Madrid take on [LineLeap](https://www.lineleap.com/): buy line-skip / cover passes for nightlife
venues and redeem them at the door. Built for DevOps Assignment 1 as a minimal monolithic app
(single process, single container, SQLite) that will be Dockerized and deployed in Assignment 2.

## Feature domains
- **Passes** — venues, pass products, purchasing (with a no-oversell inventory guard), one-time
  redemption codes, refunds.
- **Analytics** — records a sales event on each purchase into its own `events` table and reports
  revenue (totals, per-venue, top venues, per-day).

## Tech stack
Python + Flask, stdlib `sqlite3` (no ORM), `werkzeug.security` for password hashing. See `ADR.md`
for the reasoning behind each choice.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The server binds `0.0.0.0` on `PORT` (default `8000`) and writes its SQLite database to
`${DATA_DIR}/lineskip.db` (`DATA_DIR` defaults to `./data`). The schema is created automatically on
startup — no manual migration. Everything is configurable via environment variables:

| Variable   | Default   | Purpose                        |
|------------|-----------|--------------------------------|
| `PORT`     | `8000`    | HTTP port                      |
| `DATA_DIR` | `./data`  | Directory for the SQLite file  |

Health check: `curl http://localhost:8000/health` → `{"status":"ok"}`.

## Deployment contract (§7) evidence

Verified with the provided contract checker (`container/run.sh`), which builds the app with the
root `Dockerfile` and checks the §7 output contract:

```
=== SDD Assignment 1 contract check ===
==> Repository shape
  PASS  one Dockerfile, one manifest (requirements.txt)
==> Build from a clean context, no build args
  PASS  image built
  PASS  image size 232 MB
==> Start on PORT=8000 and reach it from the host
  PASS  HTTP 200 from http://localhost:8000/
==> SQLite file under DATA_DIR
  PASS  found in /data: lineskip.db
==> Data persists, and a second boot does not re-seed
  PASS  volume at /data persists
  WARN  Could not read row counts, skipping the re-seed check.
==> PORT override is honoured (not hardcoded)
  PASS  HTTP 200 from http://localhost:9123/
=== ALL CHECKS PASSED ===
```

(The one WARN is the checker skipping a row-count probe — the slim image has no `sqlite3` CLI for it
to exec; seed idempotency is covered directly by `test_seed_venues_is_idempotent`.)

## Web UI

With the server running, open <http://localhost:8000/> in a browser: browse venues, register/log
in, buy a pass, view your passes (with redemption codes) and refund them, and see the revenue
dashboard. The pages are a thin client over the JSON API — they store the login token in the
browser and send it as `Authorization: Bearer <token>`, so there is no separate web-only auth path.

## Tests & coverage

Run the suite with coverage on the core logic (the two domain services plus auth):

```bash
pytest --cov=auth --cov=passes --cov=analytics --cov-report=term-missing
```

Latest result — **34 tests pass, 100% line coverage** on the measured modules:

```
Name                      Stmts   Miss  Cover
---------------------------------------------
analytics/repository.py      11      0   100%
analytics/service.py         17      0   100%
auth/service.py              42      0   100%
passes/repository.py         38      0   100%
passes/service.py            42      0   100%
---------------------------------------------
TOTAL                       150      0   100%
```

Coverage targets the domain/auth modules rather than `app.py`, because the Flask routes are thin
glue and all business logic lives in the service and repository layers (see ADR-4).
