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
