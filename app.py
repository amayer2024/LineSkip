"""LineSkip — Flask entrypoint. Single process, started by `python app.py` (deployment contract §7)."""
from functools import wraps

from flask import Flask, g, jsonify, request

import config
import db
from auth import service as auth_service


def require_auth(view):
    """Flask glue: resolve the Bearer token to a user_id (stored on g) or return 401."""
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
    db.init_db()

    @app.get("/health")
    def health():
        return jsonify(status="ok")

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

    return app


app = create_app()


if __name__ == "__main__":
    # Bind 0.0.0.0 and read PORT from env so the shared deployment script works unmodified.
    app.run(host="0.0.0.0", port=config.get_port())
