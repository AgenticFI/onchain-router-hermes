import json

import httpx
import pytest

from onchain_router_hermes import api
from onchain_router_hermes.proxy import ProxyStatus


def test_paid_call_forwards_one_stable_key_once_and_projects_safe_headers(monkeypatch):
    requests = []
    token = "s" * 43

    def handler(request: httpx.Request):
        requests.append(request)
        assert request.headers["idempotency-key"] == "image-key-001"
        assert request.headers["authorization"] == f"Bearer {token}"
        return httpx.Response(
            200,
            json={"data": [{"url": "https://example.invalid/image", "expires_at": 1}]},
            headers={"x-receipt-id": "receipt-1", "x-payment-actual-atomic": "123"},
        )

    monkeypatch.setattr(api, "ensure_running", lambda: ProxyStatus(True))
    monkeypatch.setattr(api, "read_proxy_token", lambda: token)
    result = api.post_paid(
        "/v1/images/generations",
        {"model": "image-model", "prompt": "circle"},
        "image-key-001",
        transport=httpx.MockTransport(handler),
    )
    assert len(requests) == 1
    assert result["ok"] is True
    assert result["metadata"] == {"x-receipt-id": "receipt-1", "x-payment-actual-atomic": "123"}
    assert token not in json.dumps(result)


def test_ambiguous_transport_is_never_retried(monkeypatch):
    calls = 0

    def handler(_request: httpx.Request):
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("lost response")

    monkeypatch.setattr(api, "ensure_running", lambda: ProxyStatus(True))
    monkeypatch.setattr(api, "read_proxy_token", lambda: "s" * 43)
    result = api.post_paid(
        "/v1/audio/speech",
        {"model": "speech", "input": "hello"},
        "speech-key-001",
        transport=httpx.MockTransport(handler),
    )
    assert calls == 1
    assert result == {
        "ok": False,
        "outcome": "transport_unknown",
        "message": "local proxy outcome is unknown; inspect receipts and recover with the same key",
        "retry": "human_review",
    }


def test_free_call_is_bounded_authenticated_and_allowlisted(monkeypatch):
    token = "a" * 43

    def handler(request: httpx.Request):
        assert request.headers["authorization"] == f"Bearer {token}"
        return httpx.Response(200, json={"data": []})

    monkeypatch.setattr(api, "ensure_running", lambda: ProxyStatus(True))
    monkeypatch.setattr(api, "read_proxy_token", lambda: token)
    assert api.get_free("/v1/models", transport=httpx.MockTransport(handler)) == {
        "ok": True, "result": {"data": []}
    }
    with pytest.raises(ValueError, match="unsupported"):
        api.get_free("/health/live", transport=httpx.MockTransport(handler))


def test_paid_error_sanitizes_body_and_unknown_headers(monkeypatch):
    secret = "never-return-this"

    def handler(_request: httpx.Request):
        return httpx.Response(
            402,
            json={"error": {"code": "declined", "message": secret}},
            headers={"x-onchain-router-retry": "never", "x-internal-debug": secret},
        )

    monkeypatch.setattr(api, "ensure_running", lambda: ProxyStatus(True))
    monkeypatch.setattr(api, "read_proxy_token", lambda: "a" * 43)
    result = api.post_paid("/v1/audio/speech", {}, "speech-key", transport=httpx.MockTransport(handler))
    assert result["error"] == {"code": "declined", "message": "buyer proxy returned HTTP 402"}
    assert result["retry"] == "never"
    assert secret not in json.dumps(result)


def test_paid_path_and_key_are_validated_before_transport(monkeypatch):
    monkeypatch.setattr(api, "ensure_running", lambda: (_ for _ in ()).throw(AssertionError("no probe")))
    with pytest.raises(ValueError, match="unsupported"):
        api.post_paid("/v1/chat/completions", {}, "key")
    with pytest.raises(ValueError, match="idempotency"):
        api.post_paid("/v1/audio/speech", {}, "bad key")


def test_declared_oversize_and_invalid_json_fail_as_unknown_transport(monkeypatch):
    monkeypatch.setattr(api, "ensure_running", lambda: ProxyStatus(True))
    monkeypatch.setattr(api, "read_proxy_token", lambda: "a" * 43)

    def oversized(_request: httpx.Request):
        return httpx.Response(200, content=b"{}", headers={"content-length": str(api.MAX_FREE_RESPONSE_BYTES + 1)})

    assert api.get_free("/v1/models", transport=httpx.MockTransport(oversized))["outcome"] == "transport_unknown"
    invalid = httpx.MockTransport(lambda _request: httpx.Response(200, content=b"not-json"))
    assert api.get_free("/v1/models", transport=invalid)["outcome"] == "transport_unknown"
