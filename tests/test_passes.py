"""Tests for the Passes domain's core logic (purchase + oversell guard)."""
import pytest

from passes import repository
from passes import service as passes


def _make_product(conn, quantity_total=100, price_cents=1500):
    """Seed one venue + one pass product directly, returning (venue_id, pass_product_id)."""
    vcur = conn.execute(
        "INSERT INTO venues (name, city, address, created_at) VALUES ('V', 'Madrid', 'A', 'now')"
    )
    venue_id = vcur.lastrowid
    pcur = conn.execute(
        """INSERT INTO pass_products
               (venue_id, type, name, price_cents, quantity_total, quantity_sold, valid_date, created_at)
           VALUES (?, 'line_skip', 'Skip', ?, ?, 0, '2026-10-10', 'now')""",
        (venue_id, price_cents, quantity_total),
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
