"""LineSkip — Flask entrypoint. Single process, started by `python app.py` (deployment contract §7)."""
from flask import Flask, jsonify

import config
import db


def create_app():
    app = Flask(__name__)
    db.init_db()

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    return app


app = create_app()


if __name__ == "__main__":
    # Bind 0.0.0.0 and read PORT from env so the shared deployment script works unmodified.
    app.run(host="0.0.0.0", port=config.get_port())
