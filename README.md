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

## Tests & coverage
_(Coverage command and result added on Day 5 once the core logic is complete.)_
