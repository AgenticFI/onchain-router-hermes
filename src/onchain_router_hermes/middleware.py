"""Hermes request shaping for financially idempotent model calls."""

from __future__ import annotations

import hashlib
from typing import Any

from .proxy import PROXY_ORIGIN


def _identity(kwargs: dict[str, Any]) -> str:
    parts = (
        str(kwargs.get("session_id") or ""),
        str(kwargs.get("turn_id") or ""),
        str(kwargs.get("api_request_id") or ""),
        str(kwargs.get("api_call_count") or ""),
        str(kwargs.get("model") or ""),
    )
    if not parts[2]:
        raise ValueError("Hermes did not supply a stable API request identity")
    digest = hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()
    return f"hermes-{digest}"


def attach_paid_request_identity(**kwargs: Any) -> dict[str, Any] | None:
    """Attach one stable Buyer Runtime key to every retry of one Hermes call."""
    provider = str(kwargs.get("provider") or "").strip().lower()
    base_url = str(kwargs.get("base_url") or "").rstrip("/")
    if provider not in {"onchain-router", "agenticfi"} or base_url != f"{PROXY_ORIGIN}/v1":
        return None
    request = kwargs.get("request")
    if not isinstance(request, dict):
        raise ValueError("Hermes did not supply a provider request object")
    updated = dict(request)
    existing = updated.get("extra_headers")
    headers = dict(existing) if isinstance(existing, dict) else {}
    for name in list(headers):
        if str(name).lower() in {"idempotency-key", "x-idempotency-key", "cache-control"}:
            headers.pop(name)
    headers["Idempotency-Key"] = _identity(kwargs)
    headers["Cache-Control"] = "no-store"
    updated["extra_headers"] = headers
    return {
        "request": updated,
        "source": "onchain-router",
        "reason": "stable Buyer Runtime payment identity",
    }
