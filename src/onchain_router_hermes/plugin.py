"""Ordinary Hermes plugin surfaces layered over the model provider."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import cli, commands, proxy, schemas, tools
from .middleware import attach_paid_request_identity
from .token import refresh_token_environment


def _ensure_before_llm(**kwargs: Any) -> None:
    provider = str(kwargs.get("provider") or kwargs.get("provider_id") or kwargs.get("runtime_provider") or "").lower()
    base_url = str(kwargs.get("base_url") or kwargs.get("api_base") or "").lower()
    if provider not in {"onchain-router", "agenticfi"} and "127.0.0.1:8402" not in base_url:
        return
    current = proxy.ensure_running()
    if not current.reachable:
        raise RuntimeError(current.error or "AgenticFI buyer proxy is unavailable")
    if not refresh_token_environment():
        raise RuntimeError("AgenticFI proxy bearer is unavailable")


def _register_tool(ctx: Any, name: str, schema: dict, handler: Any, description: str, emoji: str) -> None:
    ctx.register_tool(
        name=name,
        toolset="onchain-router",
        schema=schema,
        handler=handler,
        description=description,
        emoji=emoji,
    )


def register_host_plugin(ctx: Any) -> None:
    # This is the sole permitted startup secret read: a non-wallet owner-only bearer.
    refresh_token_environment()
    ctx.register_hook("pre_llm_call", _ensure_before_llm)
    ctx.register_middleware("llm_request", attach_paid_request_identity)
    _register_tool(ctx, "onchain_router_models", schemas.EMPTY_SCHEMA, tools.models, "List live policy-filtered AgenticFI models without spending.", "🧭")
    _register_tool(ctx, "onchain_router_pricing", schemas.EMPTY_SCHEMA, tools.pricing, "Inspect current model pricing without spending.", "🧾")
    _register_tool(ctx, "onchain_router_voices", schemas.EMPTY_SCHEMA, tools.voices, "List public speech voices and compatibility without spending.", "🔊")
    _register_tool(ctx, "onchain_router_image_generate", schemas.IMAGE_SCHEMA, tools.image_generate, "Generate one paid image through Buyer Runtime. Returns a hosted URL and expiry.", "🖼️")
    _register_tool(ctx, "onchain_router_speech_generate", schemas.SPEECH_SCHEMA, tools.speech_generate, "Generate paid MP3 speech through Buyer Runtime.", "🎙️")
    _register_tool(ctx, "onchain_router_transcribe", schemas.TRANSCRIPTION_SCHEMA, tools.transcribe, "Transcribe bounded MP3 Base64 after explicit provider-retention acknowledgement.", "📝")
    ctx.register_command(
        name="onchain-router",
        handler=commands.dispatch,
        description="AgenticFI Onchain Router status and usage help",
        args_hint="<status|doctor|models|pricing|voices|recovery|help>",
    )
    ctx.register_cli_command(
        name="onchain-router",
        help="Set up and diagnose the AgenticFI local Buyer Runtime adapter",
        setup_fn=cli.register_cli,
        handler_fn=cli.handle_cli,
        description="Install exact local clients, check readiness, and control only the managed proxy.",
    )
    skill = Path(__file__).parent / "skills" / "onchain-router" / "SKILL.md"
    ctx.register_skill(
        name="guide",
        path=skill,
        description="Safe AgenticFI provider, media, idempotency, recovery, and receipt usage",
    )
    ctx.on_unload(proxy.stop)
