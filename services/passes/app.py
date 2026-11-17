"""LineSkip passes service — Flask entrypoint. Auth + passes domains; JSON API only.

Analytics is now a separate service reached over HTTP (the seam, ADR-6); this service
no longer serves /analytics or owns the events table.
"""
import os
import time
from functools import wraps

from flask import Flask, g, jsonify, request
from flask_cors import CORS

import config
import db
from auth import service as auth_service
from passes import repository as passes_repo
from passes import service as passes_service


def require_auth(view):
    """Resolve the Bearer token to a user_id (stored on g) or return 401."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        token = _bearer_token()
        conn = db.get_connection()
        try:
            user_id = auth_service.verify_session(conn, token)
        finally:
            conn.close()
        if user_id is None:
            return jsonify(error="authentication required"), 401
        g.user_id = user_id
        return view(*args, **kwargs)

    return wrapper


def _bearer_token():
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[len("Bearer ") :]
    return None


def create_app():
    app = Flask(__name__)
    CORS(
        app,
        origins=os.environ.get("CORS_ORIGINS", "*").split(","),
        allow_headers=["Content-Type", "Authorization"],
    )

    db.init_db()  # apply migrations in order
    seed_conn = db.get_connection()
    try:
        passes_repo.seed_venues(seed_conn)  # idempotent
    finally:
        seed_conn.close()

    @app.before_request
    def _start_timer():
        g._t0 = time.time()

    @app.after_request
    def _log(resp):
        dur_ms = (time.time() - getattr(g, "_t0", time.time())) * 1000
        print(f"{request.method} {request.path} {resp.status_code} {dur_ms:.0f}ms", flush=True)
        return resp

    @app.get("/health")
    def health():
        ok = db.can_reach_db()
        body = {
            "status": "ok" if ok else "error",
            "db": "ok" if ok else "down",
            "version": os.environ.get("GIT_SHA", "dev"),
        }
        return jsonify(body), (200 if ok else 503)

    @app.get("/venues")
    def list_venues():
        conn = db.get_connection()
        try:
            venues = passes_repo.list_venues(conn)
        finally:
            conn.close()
        return jsonify([dict(v) for v in venues])

    @app.get("/venues/<int:venue_id>/passes")
    def list_venue_passes(venue_id):
        conn = db.get_connection()
        try:
            venue = passes_repo.get_venue(conn, venue_id)
            if venue is None:
                return jsonify(error="venue not found"), 404
            passes = passes_repo.list_pass_products(conn, venue_id)
        finally:
            conn.close()
        return jsonify([dict(p) for p in passes])

    @app.post("/auth/register")
    def register():
        data = request.get_json(silent=True) or {}
        conn = db.get_connection()
        try:
            user_id = auth_service.register(conn, data.get("email"), data.get("password"))
        except auth_service.AuthError as exc:
            return jsonify(error=str(exc)), 400
        finally:
            conn.close()
        return jsonify(id=user_id), 201

    @app.post("/auth/login")
    def login():
        data = request.get_json(silent=True) or {}
        conn = db.get_connection()
        try:
            token = auth_service.login(conn, data.get("email"), data.get("password"))
        except auth_service.AuthError as exc:
            return jsonify(error=str(exc)), 401
        finally:
            conn.close()
        return jsonify(token=token)

    @app.get("/auth/me")
    @require_auth
    def me():
        return jsonify(user_id=g.user_id)

    @app.post("/passes/purchase")
    @require_auth
    def purchase_pass():
        data = request.get_json(silent=True) or {}
        conn = db.get_connection()
        try:
            result = passes_service.purchase(conn, g.user_id, data.get("pass_product_id"))
        except passes_service.PassError as exc:
            return jsonify(error=str(exc)), 400
        finally:
            conn.close()
        return jsonify(result), 201

    @app.get("/passes/mine")
    @require_auth
    def my_passes():
        conn = db.get_connection()
        try:
            rows = passes_repo.list_purchases_for_user(conn, g.user_id)
        finally:
            conn.close()
        return jsonify([dict(r) for r in rows])

    @app.post("/passes/redeem")
    def redeem_pass():
        # Open endpoint: the redemption code itself is the credential (door staff scanning).
        data = request.get_json(silent=True) or {}
        conn = db.get_connection()
        try:
            result = passes_service.redeem(conn, data.get("code"))
        except passes_service.PassError as exc:
            return jsonify(error=str(exc)), 400
        finally:
            conn.close()
        return jsonify(result)

    @app.post("/passes/<int:purchase_id>/refund")
    @require_auth
    def refund_pass(purchase_id):
        conn = db.get_connection()
        try:
            result = passes_service.refund(conn, purchase_id, g.user_id)
        except passes_service.PassError as exc:
            return jsonify(error=str(exc)), 400
        finally:
            conn.close()
        return jsonify(result)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.get_port())
