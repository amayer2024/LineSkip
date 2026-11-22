"""Analytics service — Flask entrypoint. Owns the events table; ingest + revenue reports.

POST /events is the seam target: the passes service calls it over HTTP on each purchase/refund.
"""
import os
import time

import config
import db
import service as analytics_service
from flask import Flask, g, jsonify, request
from flask_cors import CORS


def create_app():
    app = Flask(__name__)
    CORS(
        app,
        origins=os.environ.get("CORS_ORIGINS", "*").split(","),
        allow_headers=["Content-Type", "Authorization"],
    )

    db.init_db()  # apply migrations in order

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

    @app.post("/events")
    def ingest_event():
        data = request.get_json(silent=True) or {}
        conn = db.get_connection()
        try:
            event_id = analytics_service.record_event(
                conn,
                data.get("venue_id"),
                data.get("event_type", "purchase"),
                data.get("amount_cents", 0),
            )
            conn.commit()
        finally:
            conn.close()
        return jsonify(id=event_id), 201

    @app.get("/analytics/revenue")
    def revenue():
        conn = db.get_connection()
        try:
            total = analytics_service.total_revenue(conn)
        finally:
            conn.close()
        return jsonify(total_revenue_cents=total)

    @app.get("/analytics/revenue/net")
    def net_revenue():
        conn = db.get_connection()
        try:
            total = analytics_service.net_revenue(conn)
        finally:
            conn.close()
        return jsonify(net_revenue_cents=total)

    @app.get("/analytics/revenue/by-venue")
    def revenue_by_venue():
        conn = db.get_connection()
        try:
            rows = analytics_service.revenue_per_venue(conn)
        finally:
            conn.close()
        return jsonify(rows)

    @app.get("/analytics/venues/top")
    def top_venues():
        n = request.args.get("n", default=3, type=int)
        if n is None or n < 1:
            n = 3
        conn = db.get_connection()
        try:
            rows = analytics_service.top_venues(conn, n)
        finally:
            conn.close()
        return jsonify(rows)

    @app.get("/analytics/revenue/by-day")
    def revenue_by_day():
        conn = db.get_connection()
        try:
            rows = analytics_service.revenue_per_day(conn)
        finally:
            conn.close()
        return jsonify(rows)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.get_port())
