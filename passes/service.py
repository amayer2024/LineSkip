"""Passes domain: purchase business logic.

Pure logic — no Flask. Decisions live here; raw SQL lives in repository.py.
"""
import secrets

from passes import repository


class PassError(Exception):
    """Raised when a passes operation fails for a caller-visible reason."""


def _new_redemption_code():
    # 8 uppercase hex chars, e.g. "A1B2C3D4". The column is UNIQUE, so a collision would be
    # rejected by the DB; at this scale the odds are negligible.
    return secrets.token_hex(4).upper()


def purchase(conn, user_id, pass_product_id):
    """Buy one unit of a pass product. Returns the new purchase as a dict.

    Raises PassError if the product does not exist or is sold out.
    """
    product = repository.get_pass_product(conn, pass_product_id)
    if product is None:
        raise PassError("pass product not found")

    # Atomic oversell guard: only proceed if a unit was actually claimed.
    if not repository.try_claim_unit(conn, pass_product_id):
        raise PassError("sold out")

    code = _new_redemption_code()
    purchase_id = repository.insert_purchase(
        conn, user_id, pass_product_id, product["venue_id"], product["price_cents"], code
    )
    conn.commit()

    return {
        "id": purchase_id,
        "pass_product_id": pass_product_id,
        "venue_id": product["venue_id"],
        "price_cents_paid": product["price_cents"],
        "status": "active",
        "redemption_code": code,
    }
