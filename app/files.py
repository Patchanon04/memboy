"""Signed links for reports and receipt images.

File names are guessable (LINE message ids are sequential, report names are listed in chat), so a bare static mount would
let anyone on the internet enumerate receipts. Every link the bot hands out now carries an expiry + HMAC; the browser
chat UI (cookie session) may fetch without one. ponytail: keyed on LINE_CHANNEL_SECRET, no extra secret to manage."""
import hashlib
import hmac
import os
import time
from pathlib import Path

from app.line_io import base_url

KEY = (os.environ.get("FILE_SIGNING_KEY") or os.environ.get("LINE_CHANNEL_SECRET") or "dev-only").encode()
DIRS = {"files": Path("/data/reports"), "uploads": Path("/data/uploads")}
TTL_S = 7 * 24 * 3600  # a PDF link in LINE is opened days later; receipts images likewise


def _sig(kind: str, name: str, exp: int) -> str:
    return hmac.new(KEY, f"{kind}/{name}/{exp}".encode(), hashlib.sha256).hexdigest()[:32]


def url(kind: str, name: str, ttl: int = TTL_S) -> str:
    exp = int(time.time()) + ttl
    return f"{base_url()}/{kind}/{name}?e={exp}&s={_sig(kind, name, exp)}"


def valid(kind: str, name: str, e: str | None, s: str | None) -> bool:
    try:
        exp = int(e or 0)
    except ValueError:
        return False
    return exp > time.time() and hmac.compare_digest(s or "", _sig(kind, name, exp))
