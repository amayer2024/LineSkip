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
