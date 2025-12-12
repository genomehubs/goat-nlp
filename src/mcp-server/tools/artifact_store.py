"""In-memory artifact store for MCP tool outputs.

This store keeps authoritative structured objects server-side and returns opaque
artifact tokens to tools. Tokens are HMAC-signed to prevent forgery. Entries
expire after a TTL (default 60 seconds).

Usage:
    from .artifact_store import store, retrieve
    token = store(obj)
    obj = retrieve(token)
"""
import hashlib
import hmac
import os
import time
import uuid
from contextlib import suppress
from threading import Lock
from typing import Any, Optional

_SECRET = os.environ.get("GOAT_ARTIFACT_SECRET", None)
if _SECRET is None:
    # Use a deterministic fallback in dev; prefer setting GOAT_ARTIFACT_SECRET in prod
    _SECRET = "dev-secret-change-me"
_SECRET_BYTES = _SECRET.encode("utf-8")

# Default TTL (seconds)
DEFAULT_TTL = int(os.environ.get("GOAT_ARTIFACT_TTL_SECONDS", "60"))

# In-memory store: uid -> {data, created, ttl}
_STORE: dict[str, dict[str, Any]] = {}
_LOCK = Lock()


def _sign(uid: str) -> str:
    return hmac.new(_SECRET_BYTES, uid.encode("utf-8"), hashlib.sha256).hexdigest()


def _make_token(uid: str) -> str:
    return f"{uid}:{_sign(uid)}"


def _verify_token(token: str) -> Optional[str]:
    try:
        uid, sig = token.split(":", 1)
    except ValueError:
        return None
    expected = _sign(uid)
    return uid if hmac.compare_digest(expected, sig) else None


def store(obj: Any, ttl: int | None = None) -> str:
    """Store an object and return an opaque artifact token.

    Args:
        obj: JSON-serializable object to store
        ttl: optional TTL in seconds (defaults to DEFAULT_TTL)
    Returns:
        token string for later retrieval
    """
    uid = str(uuid.uuid4())
    entry = {"data": obj, "created": time.time(), "ttl": ttl or DEFAULT_TTL}
    with _LOCK:
        _STORE[uid] = entry
    return _make_token(uid)


def retrieve(token: str, consume: bool = False) -> Optional[Any]:
    """Retrieve a stored object by token.

    Args:
        token: the token returned by `store`
        consume: if True, remove the entry after retrieval
    Returns:
        The stored object or None if not found/expired/invalid
    """
    uid = _verify_token(token)
    if not uid:
        return None
    with _LOCK:
        entry = _STORE.get(uid)
        if not entry:
            return None
        if time.time() - entry["created"] > entry["ttl"]:
            # expired
            with suppress(KeyError):
                del _STORE[uid]
            return None
        data = entry["data"]
        if consume:
            with suppress(KeyError):
                del _STORE[uid]
        return data


def cleanup() -> None:
    """Remove expired entries from the store."""
    now = time.time()
    with _LOCK:
        for uid in list(_STORE.keys()):
            if now - _STORE[uid]["created"] > _STORE[uid]["ttl"]:
                del _STORE[uid]


def stats() -> dict[str, Any]:
    """Return simple stats about the store."""
    with _LOCK:
        return {"count": len(_STORE)}
