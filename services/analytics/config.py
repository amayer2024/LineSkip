"""Runtime configuration, read entirely from environment variables."""
import os


def get_port():
    return int(os.environ.get("PORT", "8000"))
