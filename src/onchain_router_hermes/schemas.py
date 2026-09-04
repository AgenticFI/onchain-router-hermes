"""Bounded Hermes tool schemas and local preflight validation."""

from __future__ import annotations

import base64
import binascii
import json
import math
import re
from typing import Any

IDEMPOTENCY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
MODEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
ASPECT = re.compile(r"^\d{1,2}:\d{1,2}$")
VOICE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
MAX_TOOL_BODY_BYTES = 1_114_112
MAX_TRANSCRIPTION_BASE64 = 1_048_576

EMPTY_SCHEMA = {"type": "object", "properties": {}, "additionalProperties": False}

COMMON = {
    "idempotency_key": {
        "type": "string",
        "pattern": IDEMPOTENCY.pattern,
        "description": "Stable caller key. Reuse only for the identical logical request.",
    },
    "model": {
        "type": "string",
        "pattern": MODEL.pattern,
        "description": "Exact model returned by the live Onchain Router catalog.",
    },
}

IMAGE_SCHEMA = {
    "type": "object",
    "properties": {
        **COMMON,
        "prompt": {"type": "string", "minLength": 1, "maxLength": 4000},
        "image_size": {"type": "string", "enum": ["0.5K", "1K", "2K", "4K"], "default": "1K"},
        "aspect_ratio": {"type": "string", "pattern": ASPECT.pattern, "default": "1:1"},
        "response_format": {"type": "string", "enum": ["url"], "default": "url"},
    },
    "required": ["idempotency_key", "model", "prompt"],
    "additionalProperties": False,
}

SPEECH_SCHEMA = {
    "type": "object",
    "properties": {
        **COMMON,
        "input": {"type": "string", "minLength": 1, "maxLength": 5000},
        "voice": {"type": "string", "pattern": VOICE.pattern},
        "response_format": {"type": "string", "enum": ["mp3"], "default": "mp3"},
        "speed": {"type": "number", "minimum": 0.7, "maximum": 1.2, "default": 1},
    },
    "required": ["idempotency_key", "model", "input"],
    "additionalProperties": False,
}

TRANSCRIPTION_SCHEMA = {
    "type": "object",
    "properties": {
        **COMMON,
        "audio_base64": {
            "type": "string",
            "minLength": 4,
            "maxLength": MAX_TRANSCRIPTION_BASE64,
            "description": "Canonical MP3 Base64 only; no file path or URL.",
        },
        "acknowledge_provider_retention": {
            "type": "boolean",
            "const": True,
            "description": "Human acknowledgement of provider-side audio/transcript retention.",
        },
        "language": {"type": "string", "pattern": r"^[a-z]{2,3}(?:-[A-Z]{2})?$"},
        "diarize": {"type": "boolean"},
        "num_speakers": {"type": "integer", "minimum": 1, "maximum": 32},
        "timestamps": {"type": "string", "enum": ["none", "word", "character"], "default": "none"},
        "tag_audio_events": {"type": "boolean"},
        "response_format": {"type": "string", "enum": ["json", "verbose_json"], "default": "json"},
    },
    "required": ["idempotency_key", "model", "audio_base64", "acknowledge_provider_retention"],
    "additionalProperties": False,
}


def _object(value: Any, allowed: set[str], required: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("tool input must be an object")
    if set(value) - allowed:
        raise ValueError("unsupported tool input field")
    if required - set(value):
        raise ValueError("required tool input field is missing")
    result = dict(value)
    if not isinstance(result.get("idempotency_key"), str) or not IDEMPOTENCY.fullmatch(result["idempotency_key"]):
        raise ValueError("idempotency_key is invalid")
    if not isinstance(result.get("model"), str) or not MODEL.fullmatch(result["model"]):
        raise ValueError("model is invalid")
    return result


def _text(value: Any, maximum: int, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value or len(value) > maximum:
        raise ValueError(f"{label} is empty, malformed, or too long")
    return value


def _bounded(value: dict[str, Any]) -> dict[str, Any]:
    if len(json.dumps(value, separators=(",", ":")).encode("utf-8")) > MAX_TOOL_BODY_BYTES:
        raise ValueError("tool request exceeds its byte limit")
    return value


def validate_image(value: Any) -> tuple[str, dict[str, Any]]:
    allowed = {"idempotency_key", "model", "prompt", "image_size", "aspect_ratio", "response_format"}
    result = _object(value, allowed, {"idempotency_key", "model", "prompt"})
    _text(result["prompt"], 4000, "prompt")
    if result.get("image_size", "1K") not in {"0.5K", "1K", "2K", "4K"}:
        raise ValueError("image_size is not supported")
    ratio = result.get("aspect_ratio", "1:1")
    if not isinstance(ratio, str) or not ASPECT.fullmatch(ratio):
        raise ValueError("aspect_ratio is invalid")
    if result.get("response_format", "url") != "url":
        raise ValueError("only hosted image URLs are supported by this tool")
    key = result.pop("idempotency_key")
    return key, _bounded(result)


def validate_speech(value: Any) -> tuple[str, dict[str, Any]]:
    allowed = {"idempotency_key", "model", "input", "voice", "response_format", "speed"}
    result = _object(value, allowed, {"idempotency_key", "model", "input"})
    _text(result["input"], 5000, "speech input")
    voice = result.get("voice")
    if voice is not None and (not isinstance(voice, str) or not VOICE.fullmatch(voice)):
        raise ValueError("voice is invalid")
    if result.get("response_format", "mp3") != "mp3":
        raise ValueError("only MP3 speech output is supported by this tool")
    speed = result.get("speed", 1)
    if (
        not isinstance(speed, (int, float))
        or isinstance(speed, bool)
        or not math.isfinite(speed)
        or not 0.7 <= speed <= 1.2
        or not float(speed * 1000).is_integer()
    ):
        raise ValueError("speech speed is invalid")
    key = result.pop("idempotency_key")
    return key, _bounded(result)


def validate_transcription(value: Any) -> tuple[str, dict[str, Any]]:
    allowed = {
        "idempotency_key", "model", "audio_base64", "acknowledge_provider_retention",
        "language", "diarize", "num_speakers", "timestamps", "tag_audio_events", "response_format",
    }
    result = _object(
        value,
        allowed,
        {"idempotency_key", "model", "audio_base64"},
    )
    if result.get("acknowledge_provider_retention") is not True:
        raise ValueError("provider-retention acknowledgement is required before audio upload")
    encoded = result.get("audio_base64")
    if not isinstance(encoded, str) or len(encoded) > MAX_TRANSCRIPTION_BASE64 or len(encoded) % 4:
        raise ValueError("audio must be bounded canonical MP3 Base64")
    try:
        decoded = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("audio must be bounded canonical MP3 Base64") from exc
    if base64.b64encode(decoded).decode("ascii") != encoded:
        raise ValueError("audio must be bounded canonical MP3 Base64")
    if not decoded or not (decoded.startswith(b"ID3") or (len(decoded) > 1 and decoded[0] == 0xFF and decoded[1] & 0xE0 == 0xE0)):
        raise ValueError("only MP3 audio is supported")
    if "num_speakers" in result and result.get("diarize") is not True:
        raise ValueError("num_speakers requires diarize=true")
    if "language" in result and (
        not isinstance(result["language"], str)
        or not re.fullmatch(r"^[a-z]{2,3}(?:-[A-Z]{2})?$", result["language"])
    ):
        raise ValueError("transcription language is invalid")
    for flag in ("diarize", "tag_audio_events"):
        if flag in result and not isinstance(result[flag], bool):
            raise ValueError(f"{flag} must be boolean")
    if "num_speakers" in result and (
        not isinstance(result["num_speakers"], int)
        or isinstance(result["num_speakers"], bool)
        or not 1 <= result["num_speakers"] <= 32
    ):
        raise ValueError("num_speakers is invalid")
    if result.get("timestamps", "none") not in {"none", "word", "character"}:
        raise ValueError("transcription timestamps are invalid")
    if result.get("response_format", "json") not in {"json", "verbose_json"}:
        raise ValueError("transcription response_format is invalid")
    result.pop("acknowledge_provider_retention")
    key = result.pop("idempotency_key")
    return key, _bounded(result)
