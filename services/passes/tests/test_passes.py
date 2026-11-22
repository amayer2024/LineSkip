"""Tests for the Passes domain's core logic (purchase, oversell guard, redeem, refund).

The analytics seam is now an HTTP call to a separate service, so these tests cover only
the passes-owned behaviour; the cross-seam flow is covered by the integration test.
"""
import threading
from datetime import date, timedelta

import pytest

import db
from passes import service as passes

# Seeded/test passes must be valid in the future: purchase() now rejects expired passes.
FUTURE = (date.today() + timedelta(days=60)).isoformat()


def _make_product(conn, quantity_total=100, price_cents=1500, valid_date=FUTURE):
    """Seed one venue + one pass product directly, returning (venue_id, pass_product_id)."""
    vcur = conn.execute(
        "INSERT INTO venues (name, city, address, created_at) VALUES ('V', 'Madrid', 'A', 'now')"
    )
    venue_id = vcur.lastrowid
    pcur = conn.execute(
        """INSERT INTO pass_products
               (venue_id, type, name, price_cents, quantity_total, quantity_sold, valid_date, created_at)
           VALUES (?, 'line_skip', 'Skip', ?, ?, 0, ?, 'now')""",
        (venue_id, price_cents, quantity_total, valid_date),
    )
    conn.commit()
    return venue_id, pcur.lastrowid


def _user(conn):
    cur = conn.execute(
        "INSERT INTO users (email, password_hash, created_at) VALUES ('u@m.es', 'x', 'now')"
    )
    conn.commit()
    return cur.lastrowid


def test_purchase_succeeds_and_increments_stock(conn):
    venue_id, product_id = _make_product(conn, quantity_total=100, price_cents=1500)
    user_id = _user(conn)

    result = passes.purchase(conn, user_id, product_id)

    assert result["status"] == "active"
    assert result["price_cents_paid"] == 1500
    assert result["venue_id"] == venue_id
    assert result["redemption_code"]
    sold = conn.execute(
        "SELECT quantity_sold FROM pass_products WHERE id = ?", (product_id,)
    ).fetchone()["quantity_sold"]
    assert sold == 1


def test_purchase_rejects_when_sold_out(conn):
    _, product_id = _make_product(conn, quantity_total=1)
    user_id = _user(conn)

    passes.purchase(conn, user_id, product_id)  # claims the only unit
    with pytest.raises(passes.PassError):
        passes.purchase(conn, user_id, product_id)  # sold out

    sold = conn.execute(
        "SELECT quantity_sold FROM pass_products WHERE id = ?", (product_id,)
    ).fetchone()["quantity_sold"]
    assert sold == 1  # never exceeds quantity_total


def test_purchase_unknown_product_raises(conn):
    user_id = _user(conn)
    with pytest.raises(passes.PassError):
        passes.purchase(conn, user_id, 9999)


def test_each_purchase_gets_a_unique_code(conn):
    _, product_id = _make_product(conn, quantity_total=10)
    user_id = _user(conn)
    codes = {passes.purchase(conn, user_id, product_id)["redemption_code"] for _ in range(5)}
    assert len(codes) == 5


# --- redeem ---------------------------------------------------------------

def test_redeem_marks_pass_redeemed(conn):
    _, product_id = _make_product(conn)
    user_id = _user(conn)
    bought = passes.purchase(conn, user_id, product_id)

    result = passes.redeem(conn, bought["redemption_code"])

    assert result["status"] == "redeemed"
    assert result["redeemed_at"] is not None


def test_redeem_twice_is_rejected(conn):
    _, product_id = _make_product(conn)
    user_id = _user(conn)
    bought = passes.purchase(conn, user_id, product_id)

    passes.redeem(conn, bought["redemption_code"])
    with pytest.raises(passes.PassError):
        passes.redeem(conn, bought["redemption_code"])  # one-time use


def test_redeem_unknown_code_raises(conn):
    with pytest.raises(passes.PassError):
        passes.redeem(conn, "NOPE0000")


# --- refund ---------------------------------------------------------------

def test_refund_marks_refunded_and_releases_stock(conn):
    _, product_id = _make_product(conn, quantity_total=5)
    user_id = _user(conn)
    bought = passes.purchase(conn, user_id, product_id)
    assert conn.execute(
        "SELECT quantity_sold FROM pass_products WHERE id = ?", (product_id,)
    ).fetchone()["quantity_sold"] == 1

    result = passes.refund(conn, bought["id"], user_id)

    assert result["status"] == "refunded"
    assert conn.execute(
        "SELECT quantity_sold FROM pass_products WHERE id = ?", (product_id,)
    ).fetchone()["quantity_sold"] == 0  # unit returned to stock


def test_refund_rejects_other_users_purchase(conn):
    _, product_id = _make_product(conn)
    owner = _user(conn)
    bought = passes.purchase(conn, owner, product_id)
    other = conn.execute(
        "INSERT INTO users (email, password_hash, created_at) VALUES ('x@m.es','x','now')"
    ).lastrowid
    conn.commit()
    with pytest.raises(passes.PassError):
        passes.refund(conn, bought["id"], other)


def test_refund_unknown_purchase_raises(conn):
    user_id = _user(conn)
    with pytest.raises(passes.PassError):
        passes.refund(conn, 9999, user_id)


def test_refund_rejects_already_redeemed_pass(conn):
    _, product_id = _make_product(conn)
    user_id = _user(conn)
    bought = passes.purchase(conn, user_id, product_id)
    passes.redeem(conn, bought["redemption_code"])
    with pytest.raises(passes.PassError):
        passes.refund(conn, bought["id"], user_id)


# --- valid_date enforcement -----------------------------------------------

def test_purchase_rejects_expired_pass(conn):
    _, product_id = _make_product(conn, valid_date="2020-01-01")
    user_id = _user(conn)
    with pytest.raises(passes.PassError):
        passes.purchase(conn, user_id, product_id)


# --- oversell guard under concurrency (the property the design highlights) --

def test_oversell_guard_is_atomic_under_concurrent_purchases(conn):
    """Many buyers race for a single unit; the atomic claim must let exactly one win."""
    _, product_id = _make_product(conn, quantity_total=1)
    user_id = _user(conn)

    outcomes = []
    lock = threading.Lock()

    def buy():
        c = db.get_connection()  # each thread needs its own connection
        try:
            passes.purchase(c, user_id, product_id)
            with lock:
                outcomes.append("ok")
        except passes.PassError:
            with lock:
                outcomes.append("sold_out")
        finally:
            c.close()

    threads = [threading.Thread(target=buy) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert outcomes.count("ok") == 1        # exactly one buyer claimed the last unit
    assert outcomes.count("sold_out") == 9  # everyone else was correctly rejected
    sold = conn.execute(
        "SELECT quantity_sold FROM pass_products WHERE id = ?", (product_id,)
    ).fetchone()["quantity_sold"]
    assert sold == 1                        # never oversold past quantity_total
