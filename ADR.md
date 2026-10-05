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
