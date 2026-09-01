import base64

import pytest

from onchain_router_hermes.schemas import (
    MAX_TRANSCRIPTION_BASE64,
    validate_image,
    validate_speech,
    validate_transcription,
)

KEY = "request-20260901-001"


def test_image_and_speech_are_strict_and_bounded():
    key, image = validate_image(
        {"idempotency_key": KEY, "model": "image-model", "prompt": "blue circle"}
    )
    assert key == KEY
    assert image == {"model": "image-model", "prompt": "blue circle"}
    with pytest.raises(ValueError, match="unsupported"):
        validate_image({"idempotency_key": KEY, "model": "x", "prompt": "x", "url": "https://bad"})
    with pytest.raises(ValueError, match="MP3"):
        validate_speech(
            {"idempotency_key": KEY, "model": "speech", "input": "hello", "response_format": "wav"}
        )


def test_transcription_requires_retention_ack_and_canonical_mp3():
    audio = base64.b64encode(b"ID3" + b"\0" * 32).decode("ascii")
    with pytest.raises(ValueError, match="acknowledgement"):
        validate_transcription({"idempotency_key": KEY, "model": "stt", "audio_base64": audio})
    key, body = validate_transcription(
        {
            "idempotency_key": KEY,
            "model": "stt",
            "audio_base64": audio,
            "acknowledge_provider_retention": True,
        }
    )
    assert key == KEY
    assert "acknowledge_provider_retention" not in body
    with pytest.raises(ValueError, match="bounded"):
        validate_transcription(
            {
                "idempotency_key": KEY,
                "model": "stt",
                "audio_base64": "A" * (MAX_TRANSCRIPTION_BASE64 + 4),
                "acknowledge_provider_retention": True,
            }
        )
