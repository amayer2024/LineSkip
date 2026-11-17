"""The seam (passes side): record events on the analytics service over HTTP.

Replaces the Assignment 1 in-process call. Locates analytics through ANALYTICS_URL
(never a hardcoded host), times out, and degrades on failure: a purchase or refund still
succeeds even if analytics is down — the event is simply not recorded (see ADR-6).
"""
import os

import requests


def _base_url():
    return os.environ.get("ANALYTICS_URL", "http://analytics:8000")


def _timeout():
    return float(os.environ.get("ANALYTICS_TIMEOUT_S", "2"))


def record_event(venue_id, event_type, amount_cents):
    """POST one event to analytics. Never raises to the caller; logs and returns on failure."""
    try:
        requests.post(
            f"{_base_url()}/events",
            json={"venue_id": venue_id, "event_type": event_type, "amount_cents": amount_cents},
            timeout=_timeout(),
        )
    except requests.RequestException as exc:
        print(f"[seam] analytics unavailable, event not recorded: {exc}", flush=True)
