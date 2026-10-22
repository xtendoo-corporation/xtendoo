"""Pure helpers to build and parse ``xtdai1`` tokens (CONTRACT §2). No ORM here."""

import base64
import hashlib
import hmac
import json
import time

PREFIX = "xtdai1"
TTL = 600
LEEWAY = 30


def _b64e(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64d(text):
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(secret, payload_b64):
    mac = hmac.new(secret.encode(), f"{PREFIX}.{payload_b64}".encode(), hashlib.sha256)
    return _b64e(mac.digest())


def build_token(secret, payload):
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload_b64 = _b64e(raw)
    return f"{PREFIX}.{payload_b64}.{_sign(secret, payload_b64)}"


def parse_token(secret, token, now=None):
    """Return ``(payload, reason)``; ``payload`` is None when invalid.

    ``reason`` is a short machine code, never contains the token.
    """
    if not isinstance(token, str) or len(token) > 4096:
        return None, "malformed"
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != PREFIX:
        return None, "malformed"
    _prefix, payload_b64, signature = parts
    expected = _sign(secret, payload_b64)
    if not hmac.compare_digest(expected.encode(), signature.encode("ascii", "ignore")):
        return None, "bad_signature"
    try:
        payload = json.loads(_b64d(payload_b64))
    except (ValueError, UnicodeDecodeError):
        return None, "malformed"
    if not isinstance(payload, dict) or payload.get("v") != 1:
        return None, "malformed"
    ok = (
        isinstance(payload.get("db"), str)
        and all(
            isinstance(payload.get(k), int) and not isinstance(payload.get(k), bool)
            for k in ("uid", "conv", "run", "iat", "exp")
        )
        and isinstance(payload.get("cids"), list)
        and payload["cids"]
        and all(isinstance(c, int) and not isinstance(c, bool) for c in payload["cids"])
        and isinstance(payload.get("jti"), str)
        and isinstance(payload.get("lang"), str)
        and isinstance(payload.get("tz"), str)
    )
    if not ok:
        return None, "malformed"
    now = time.time() if now is None else now
    if payload["exp"] + LEEWAY <= now:
        return None, "expired"
    return payload, ""
