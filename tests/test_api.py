import json

import httpx

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
