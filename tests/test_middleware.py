from onchain_router_hermes.middleware import attach_paid_request_identity


def _call(api_request_id="turn-1:api:1", provider="onchain-router"):
    return attach_paid_request_identity(
        request={"model": "model-a", "messages": [{"role": "user", "content": "private"}]},
        session_id="session-1",
        turn_id="turn-1",
        api_request_id=api_request_id,
        api_call_count=1,
        model="model-a",
        provider=provider,
        base_url="http://127.0.0.1:8402/v1",
    )


def test_model_retries_receive_one_stable_financial_identity():
    first = _call()
    retry = _call()
    assert first is not None and retry is not None
    first_headers = first["request"]["extra_headers"]
    retry_headers = retry["request"]["extra_headers"]
    assert first_headers == retry_headers
    assert first_headers["Idempotency-Key"].startswith("hermes-")
    assert first_headers["Cache-Control"] == "no-store"
    assert "private" not in first_headers["Idempotency-Key"]


def test_separate_model_calls_receive_separate_financial_identities():
    first = _call("turn-1:api:1")
    second = _call("turn-1:api:2")
    assert first is not None and second is not None
    assert first["request"]["extra_headers"] != second["request"]["extra_headers"]


def test_other_providers_are_untouched():
    assert _call(provider="other") is None
