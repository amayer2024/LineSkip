# AI Usage Log

## How I used AI on this project
I used AI (Claude Code) as a design-and-pair-programming partner, working one small segment at a
time. For each segment the AI first explained *what* it would build and *how it would work*; I read
that explanation, questioned or adjusted it, and approved it before any code was written. The
design decisions — the stack, the two feature domains, how they stay decoupled, the auth approach,
what to leave out — were mine, made as we went. After building, I ran and tested each segment
myself and only then committed it. Disclosure is grade-neutral; the point of this log is to show
that I understand and can explain every line I shipped.

One row per meaningful AI interaction. The last column is my own explanation, in my own words.

| Date/commit | Tool | Prompt | Disposition | What changed & why (if modified) | In my own words, how this works |
|---|---|---|---|---|---|
| 2026-10-05 · scaffold | Claude Code | Design a LineLeap-style passes app for this assignment, then scaffold a Flask + SQLite skeleton with a health check and environment-based configuration; explain each file before writing it | Accepted after step-by-step review | I reviewed and approved each file as it was explained; no changes were needed to the proposed scaffold | The app starts with `python app.py`. `create_app()` in `app.py` builds the Flask app and calls `db.init_db()` so the database is ready before any request. `config.py` reads `PORT` (default 8000) and `DATA_DIR` (default `./data`) from the environment, so I reconfigure the app by setting env vars, never by editing code. `db.get_connection()` opens the SQLite file at `<DATA_DIR>/lineskip.db` (creating the folder if needed), sets `row_factory` so I can read columns by name like `row["email"]`, and turns on foreign keys. `init_db()` reads `schema.sql` and runs it with `executescript`; because every table uses `CREATE TABLE IF NOT EXISTS`, running it on every startup is safe. The `/health` route just returns `{"status":"ok"}` so a deployer can check the app is alive. Binding `0.0.0.0` (not localhost) is what lets the container accept outside traffic. |
