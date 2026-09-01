"""One-shot bounded calls to the authenticated local proxy."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import httpx

from .proxy import PROXY_ORIGIN, ensure_running
from .schemas import IDEMPOTENCY
from .token import read_proxy_token

MAX_FREE_RESPONSE_BYTES = 4 * 1024 * 1024
MAX_PAID_RESPONSE_BYTES = 32 * 1024 * 1024
SAFE_HEADERS = (
    "x-onchain-router-idempotency-key",
    "x-onchain-router-outcome",
    "x-onchain-router-retry",
    "x-onchain-router-cache",
    "x-onchain-router-charge-atomic",
    "x-onchain-router-source-receipt-id",
    "x-receipt-id",
    "x-payment-network",
    "x-payment-maximum-atomic",
    "x-payment-actual-atomic",
    "x-payment-transaction",
)


def _request_json(
    client: httpx.Client,
    method: str,
    url: str,
    maximum: int,
    **kwargs: Any,
) -> tuple[int, httpx.Headers, Any]:
    with client.stream(method, url, **kwargs) as response:
        declared = response.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > maximum:
            raise RuntimeError("buyer proxy response exceeds its byte limit")
        content = bytearray()
        for chunk in response.iter_bytes():
            content.extend(chunk)
            if len(content) > maximum:
                raise RuntimeError("buyer proxy response exceeds its byte limit")
        status = response.status_code
        headers = httpx.Headers(response.headers)
    try:
        value = json.loads(content)
    except (UnicodeDecodeError, ValueError) as exc:
        raise RuntimeError("buyer proxy response is not valid JSON") from exc
    return status, headers, value


def _safe_error(value: Any, status: int) -> dict[str, Any]:
    code = "buyer_proxy_error"
    if isinstance(value, dict) and isinstance(value.get("error"), dict):
        raw_code = value["error"].get("code")
        if isinstance(raw_code, str) and len(raw_code) <= 128 and raw_code.replace("_", "").isalnum():
            code = raw_code
    return {"code": code, "message": f"buyer proxy returned HTTP {status}"}


def _headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {name: headers[name] for name in SAFE_HEADERS if name in headers}


def get_free(path: str, *, transport: httpx.BaseTransport | None = None) -> dict[str, Any]:
    if path not in {"/v1/models", "/v1/pricing", "/v1/audio/voices"}:
        raise ValueError("unsupported free proxy path")
    status = ensure_running()
    if not status.reachable:
        return {"ok": False, "outcome": "proxy_unavailable", "message": status.error}
    try:
        token = read_proxy_token()
        with httpx.Client(timeout=10, follow_redirects=False, trust_env=False, transport=transport) as client:
            response_status, _response_headers, value = _request_json(
                client,
                "GET",
                f"{PROXY_ORIGIN}{path}",
                MAX_FREE_RESPONSE_BYTES,
                headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
            )
        if response_status != 200:
            return {"ok": False, "status": response_status, "error": _safe_error(value, response_status)}
        return {"ok": True, "result": value}
    except (OSError, RuntimeError, httpx.HTTPError):
        return {"ok": False, "outcome": "transport_unknown", "retry": "human_review"}


def post_paid(
    path: str,
    body: dict[str, Any],
    idempotency_key: str,
    *,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
    if path not in {"/v1/images/generations", "/v1/audio/speech", "/v1/audio/transcriptions"}:
        raise ValueError("unsupported paid proxy path")
    if not IDEMPOTENCY.fullmatch(idempotency_key):
        raise ValueError("idempotency_key is invalid")
    status = ensure_running()
    if not status.reachable:
        return {"ok": False, "outcome": "proxy_unavailable", "message": status.error, "retry": "never"}
    try:
        token = read_proxy_token()
        with httpx.Client(timeout=300, follow_redirects=False, trust_env=False, transport=transport) as client:
            response_status, response_headers, value = _request_json(
                client,
                "POST",
                f"{PROXY_ORIGIN}{path}",
                MAX_PAID_RESPONSE_BYTES,
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": idempotency_key,
                },
                json=body,
            )
        metadata = _headers(response_headers)
        if response_status < 200 or response_status >= 300:
            retry = metadata.get("x-onchain-router-retry", "human_review")
            return {
                "ok": False,
                "status": response_status,
                "error": _safe_error(value, response_status),
                "metadata": metadata,
                "retry": "human_review" if retry != "never" else "never",
            }
        return {"ok": True, "result": value, "metadata": metadata, "retry": "never"}
    except (OSError, RuntimeError, httpx.HTTPError):
        return {
            "ok": False,
            "outcome": "transport_unknown",
            "message": "local proxy outcome is unknown; inspect receipts and recover with the same key",
            "retry": "human_review",
        }
