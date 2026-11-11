"""Analytics service — Flask entrypoint. Owns the events table; exposes ingest + reports.

POST /events is the seam target: in Assignment 2 the passes service calls it over HTTP
instead of recording events in-process.
"""
import config
import db
import service as analytics_service
from flask import Flask, jsonify, request


def create_app():
    app = Flask(__name__)
    db.init_db()

    @app.get("/health")
    def health():
        return jsonify(status="ok")

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
