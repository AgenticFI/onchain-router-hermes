"""Hermes tool handlers for existing bounded proxy endpoints."""

from __future__ import annotations

import json
from typing import Any, Callable

from . import api
from .schemas import validate_image, validate_speech, validate_transcription


def _json(action: Callable[[], dict[str, Any]]) -> str:
    try:
        return json.dumps(action(), separators=(",", ":"))
    except ValueError as exc:
        return json.dumps({"ok": False, "outcome": "invalid_input", "message": str(exc), "retry": "never"})


def models(_args: dict | None = None, **_: Any) -> str:
    return _json(lambda: api.get_free("/v1/models"))


def pricing(_args: dict | None = None, **_: Any) -> str:
    return _json(lambda: api.get_free("/v1/pricing"))


def voices(_args: dict | None = None, **_: Any) -> str:
    return _json(lambda: api.get_free("/v1/audio/voices"))


def image_generate(args: dict, **_: Any) -> str:
    def action():
        key, body = validate_image(args)
        return api.post_paid("/v1/images/generations", body, key)

    return _json(action)


def speech_generate(args: dict, **_: Any) -> str:
    def action():
        key, body = validate_speech(args)
        return api.post_paid("/v1/audio/speech", body, key)

    return _json(action)


def transcribe(args: dict, **_: Any) -> str:
    def action():
        key, body = validate_transcription(args)
        return api.post_paid("/v1/audio/transcriptions", body, key)

    return _json(action)
